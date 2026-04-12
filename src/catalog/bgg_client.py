"""BGG XML API2 HTTP client with 5-tier backoff and rate limiting."""

from __future__ import annotations

import sys
import time
from typing import Any

import requests
from lxml import etree

from src.catalog.errors import BggApiError, GameSkipError

_BGG_API_URL = "https://boardgamegeek.com/xmlapi2/thing"

# Backoff schedules (seconds between retries)
_BACKOFF_202 = [5, 10, 20, 40, 60]       # max 5 retries, cap 155 s
_BACKOFF_5XX = [1, 4, 16]                 # max 3 retries
_MAX_429_RETRIES = 3
_REQUEST_TIMEOUT = 15  # seconds


class BggClient:
    """HTTP client for the BGG XML API2.

    One instance should be shared across all requests in a session so that the
    underlying TCP connection pool and the 1.5-second rate-limit are respected.
    """

    def __init__(
        self,
        user_agent: str = "BoardGameClubCatalog/1.0",
        request_interval_sec: float = 1.5,
        batch_size: int = 20,
    ) -> None:
        self._interval = request_interval_sec
        self._batch_size = batch_size
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_xml(self, bgg_ids: list[int]) -> bytes:
        """Fetch raw XML bytes for a list of BGG IDs (max batch_size at once).

        Handles 202, 429, 5xx, timeout, connection error, malformed XML, and
        HTTP-200-with-<errors> per the plan §5 backoff table.

        Returns raw XML bytes on success.
        Raises GameSkipError for non-recoverable single-game failures.
        Raises BggApiError for invalid-ID responses.
        """
        if len(bgg_ids) > self._batch_size:
            raise ValueError(
                f"fetch_xml accepts at most {self._batch_size} IDs per call."
            )

        ids_str = ",".join(str(i) for i in bgg_ids)
        url = f"{_BGG_API_URL}?id={ids_str}&stats=1"

        return self._fetch_with_backoff(url, bgg_ids)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)

    def _do_get(self, url: str) -> requests.Response:
        self._throttle()
        resp = self._session.get(url, timeout=_REQUEST_TIMEOUT)
        self._last_request_time = time.monotonic()
        return resp

    def _fetch_with_backoff(self, url: str, bgg_ids: list[int]) -> bytes:
        """Core fetch loop implementing all 5 tiers of backoff."""
        ids_label = ",".join(str(i) for i in bgg_ids)

        # --- Tier 3: 5xx ---
        retries_5xx = 0

        # --- Tier 4/5: timeout / connection error ---
        retries_transient = 0

        # --- Tier 2: 429 ---
        retries_429 = 0

        # --- Tier 6: malformed XML ---
        retries_malformed = 0

        while True:
            try:
                resp = self._do_get(url)
            except requests.exceptions.Timeout:
                retries_transient += 1
                if retries_transient > 1:
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"Timeout fetching IDs [{ids_label}] after retry.",
                    )
                print(
                    f"[BggClient] Timeout for [{ids_label}]; retrying once…",
                    file=sys.stderr,
                )
                continue
            except requests.exceptions.ConnectionError:
                retries_transient += 1
                if retries_transient > 1:
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"Connection error fetching IDs [{ids_label}] after retry.",
                    )
                print(
                    f"[BggClient] Connection error for [{ids_label}]; retrying once…",
                    file=sys.stderr,
                )
                time.sleep(2)
                continue

            # --- HTTP 202: BGG still processing ---
            if resp.status_code == 202:
                attempt = len(_BACKOFF_202) - len(_BACKOFF_202)  # track via list index
                # Use a local counter instead
                if not hasattr(self, "_202_count"):
                    self._202_count: dict[str, int] = {}
                count = self._202_count.get(ids_label, 0)
                if count >= len(_BACKOFF_202):
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"BGG returned 202 too many times for [{ids_label}].",
                    )
                wait = _BACKOFF_202[count]
                self._202_count[ids_label] = count + 1
                print(
                    f"[BggClient] 202 for [{ids_label}]; waiting {wait}s (attempt {count+1}/{len(_BACKOFF_202)})…",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue

            # --- HTTP 429: rate limited ---
            if resp.status_code == 429:
                retries_429 += 1
                if retries_429 > _MAX_429_RETRIES:
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"Too many 429 responses for [{ids_label}].",
                    )
                retry_after = int(resp.headers.get("Retry-After", "60"))
                print(
                    f"[BggClient] 429 for [{ids_label}]; waiting {retry_after}s…",
                    file=sys.stderr,
                )
                time.sleep(retry_after)
                continue

            # --- HTTP 5xx ---
            if resp.status_code >= 500:
                if retries_5xx >= len(_BACKOFF_5XX):
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"HTTP {resp.status_code} for [{ids_label}] after all retries.",
                    )
                wait = _BACKOFF_5XX[retries_5xx]
                retries_5xx += 1
                print(
                    f"[BggClient] HTTP {resp.status_code} for [{ids_label}]; waiting {wait}s…",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue

            # --- Non-200 we don't handle ---
            if resp.status_code != 200:
                raise GameSkipError(
                    bgg_ids[0] if len(bgg_ids) == 1 else 0,
                    f"Unexpected HTTP {resp.status_code} for [{ids_label}].",
                )

            raw = resp.content

            # --- HTTP 200 + <errors> payload (invalid BGG ID) ---
            try:
                root = etree.fromstring(raw)
            except etree.XMLSyntaxError:
                retries_malformed += 1
                if retries_malformed > 1:
                    raise GameSkipError(
                        bgg_ids[0] if len(bgg_ids) == 1 else 0,
                        f"Malformed XML for [{ids_label}] after retry.",
                    )
                print(
                    f"[BggClient] Malformed XML for [{ids_label}]; invalidating and retrying…",
                    file=sys.stderr,
                )
                continue

            if root.tag == "errors":
                id_str = ids_label
                msg = "; ".join(
                    e.findtext("message") or "unknown"
                    for e in root.findall("error")
                )
                print(
                    f"ERROR: BGG returned <errors> for IDs [{id_str}]: {msg}",
                    file=sys.stderr,
                )
                raise BggApiError(
                    bgg_ids[0] if len(bgg_ids) == 1 else 0,
                    msg,
                )

            # Clean up 202 counter on success
            if hasattr(self, "_202_count") and ids_label in self._202_count:
                del self._202_count[ids_label]

            return raw

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "BggClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
