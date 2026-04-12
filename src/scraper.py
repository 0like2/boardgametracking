"""
보드라이프 중고장터 스크래퍼
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 카테고리 키워드 매핑
CATEGORY_KEYWORDS = {
    "판매": ["판매", "팝니다", "sale"],
    "구매": ["구매", "삽니다", "buy", "구합니다"],
    "교환": ["교환", "exchange"],
    "나눔": ["나눔", "free", "무료"],
    "완료": ["완료", "done", "종료"],
}


@dataclass
class Post:
    post_id: str    # bbs_num
    title: str
    category: str   # 판매/구매/교환/나눔/완료
    author: str
    url: str
    price: str = ""  # 가격 정보 (예: "45,000원", "택배비 별도")


class BoardLifeScraper:
    """보드라이프 중고장터 스크래퍼"""

    BASE_DOMAIN = "https://boardlife.co.kr"
    DETAIL_PATH = "/bbs_detail.php"

    def __init__(self, base_url: str, user_agent: str) -> None:
        """세션 초기화

        Args:
            base_url: 중고장터 목록 URL
            user_agent: HTTP 요청에 사용할 User-Agent 문자열
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.BASE_DOMAIN,
        })

    # ------------------------------------------------------------------
    # 내부 헬퍼 메서드
    # ------------------------------------------------------------------

    def _extract_bbs_num(self, href: str) -> str | None:
        """URL에서 bbs_num 파라미터를 추출한다."""
        if not href:
            return None
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        nums = params.get("bbs_num")
        if nums:
            return nums[0]
        return None

    def _build_detail_url(self, bbs_num: str, tb: str = "board_used") -> str:
        """게시물 상세 URL을 조합한다."""
        return f"{self.BASE_DOMAIN}{self.DETAIL_PATH}?tb={tb}&bbs_num={bbs_num}"

    def _extract_category_from_title(self, title: str) -> tuple[str, str]:
        """제목에서 [카테고리] 태그를 분리한다.

        Returns:
            (category, clean_title) 튜플.
            카테고리를 찾지 못하면 category는 빈 문자열.
        """
        # [판매], [구매], [교환], [나눔], [완료] 등의 패턴을 제목 앞에서 추출
        bracket_pattern = re.compile(r"^\s*[\[\(【「]([^\]\)】」]+)[\]\)】」]\s*")
        match = bracket_pattern.match(title)
        if match:
            raw_tag = match.group(1).strip()
            clean_title = title[match.end():].strip()
            category = self._normalize_category(raw_tag)
            return category, clean_title

        # 괄호 없이 카테고리 키워드로 시작하는 경우 처리
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if title.lstrip().lower().startswith(kw.lower()):
                    return cat, title.strip()

        return "", title.strip()

    def _normalize_category(self, raw: str) -> str:
        """원시 카테고리 문자열을 표준 카테고리로 정규화한다."""
        raw_lower = raw.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in raw_lower:
                    return cat
        # 매핑 실패 시 원본 반환
        return raw

    def _parse_posts_from_soup(self, soup: BeautifulSoup) -> list[Post]:
        """BeautifulSoup 객체에서 게시물 목록을 파싱한다.

        보드라이프의 정확한 HTML 구조를 알 수 없으므로
        여러 패턴을 순서대로 시도한다.
        """
        posts: list[Post] = []

        # bbs_num 파라미터를 포함한 모든 <a> 태그를 수집 (가장 확실한 방법)
        all_links = soup.find_all("a", href=re.compile(r"bbs_num=\d+"))
        if not all_links:
            logger.warning("bbs_num 파라미터를 포함한 링크를 찾지 못했습니다.")
            return posts

        seen_ids: set[str] = set()

        for link in all_links:
            href = link.get("href", "")
            bbs_num = self._extract_bbs_num(href)
            if not bbs_num or bbs_num in seen_ids:
                continue

            # 제목 텍스트 추출
            raw_title = link.get_text(separator=" ", strip=True)
            if not raw_title:
                continue

            # 너무 짧거나 의미 없는 텍스트 제거 (페이지 네비게이션 링크 등)
            if len(raw_title) < 2:
                continue

            # 제목에서 카테고리 분리
            category, clean_title = self._extract_category_from_title(raw_title)

            # 카테고리를 행(row) 또는 상위 요소에서 별도로 찾아보기
            if not category:
                category = self._find_category_in_context(link)

            # "완료", "구매" 카테고리 게시물 제외
            if category in ("완료", "구매"):
                logger.debug("%s 게시물 제외: %s (id=%s)", category, clean_title, bbs_num)
                continue

            # 작성자 추출 (상위 행 또는 인접 요소에서 탐색)
            author = self._find_author_in_context(link)

            # URL 조합 (tb 파라미터를 href에서 가져오거나 기본값 사용)
            tb = parse_qs(urlparse(href).query).get("tb", ["board_used"])[0]
            detail_url = self._build_detail_url(bbs_num, tb)

            # 가격 추출: 제목에서 먼저 시도, 실패 시 컨텍스트에서 탐색
            price = self._extract_price_from_title(raw_title)
            if not price:
                price = self._extract_price_from_context(link)

            posts.append(Post(
                post_id=bbs_num,
                title=clean_title,
                category=category,
                author=author,
                url=detail_url,
                price=price,
            ))
            seen_ids.add(bbs_num)

        return posts

    def _extract_price_from_title(self, title: str) -> str:
        """제목에서 가격 패턴을 추출한다.

        Returns:
            가격 문자열 (예: "45,000원", "3만원", "무료").
            찾지 못하면 빈 문자열.
        """
        pattern = re.compile(r'(\d[\d,]*\s*원|\d+만\s*원?|무료|나눔)')
        match = pattern.search(title)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_price_from_context(self, link_tag) -> str:
        """링크 태그의 상위/인접 요소에서 가격 정보를 탐색한다."""
        parent = link_tag.parent
        for _ in range(5):
            if parent is None:
                break
            price_hints = parent.find_all(
                class_=re.compile(r"price|cost|금액", re.I)
            )
            for hint in price_hints:
                text = hint.get_text(strip=True)
                if text:
                    return text
            parent = parent.parent
        return ""

    def _find_category_in_context(self, link_tag) -> str:
        """링크 태그의 상위/인접 요소에서 카테고리 정보를 탐색한다."""
        # 상위 tr/li/div 요소 내에서 카테고리 전용 셀 또는 span을 탐색
        parent = link_tag.parent
        for _ in range(5):  # 최대 5단계 상위까지 탐색
            if parent is None:
                break
            # 카테고리를 나타내는 class 힌트 탐색
            cat_hints = parent.find_all(
                class_=re.compile(r"cate|category|type|tag", re.I)
            )
            for hint in cat_hints:
                text = hint.get_text(strip=True)
                normalized = self._normalize_category(text)
                if normalized in CATEGORY_KEYWORDS:
                    return normalized

            # td/li 순서 기반: 첫 번째 또는 두 번째 셀이 카테고리인 경우
            if parent.name in ("tr", "li"):
                cells = parent.find_all(["td", "span", "div"], recursive=False)
                for cell in cells[:3]:
                    text = cell.get_text(strip=True)
                    for cat, keywords in CATEGORY_KEYWORDS.items():
                        for kw in keywords:
                            if kw in text:
                                return cat
            parent = parent.parent

        return ""

    def _find_author_in_context(self, link_tag) -> str:
        """링크 태그의 상위/인접 요소에서 작성자를 탐색한다."""
        parent = link_tag.parent
        for _ in range(5):
            if parent is None:
                break
            # 작성자를 나타내는 class 힌트 탐색
            author_hints = parent.find_all(
                class_=re.compile(r"author|writer|nick|user|name", re.I)
            )
            for hint in author_hints:
                text = hint.get_text(strip=True)
                if text:
                    return text

            # td 순서 기반: 뒤쪽 셀이 작성자인 경우가 많음
            if parent.name in ("tr", "li"):
                cells = parent.find_all("td", recursive=False)
                # 보통 작성자는 제목 다음 셀 또는 마지막 셀 근처
                for cell in reversed(cells):
                    text = cell.get_text(strip=True)
                    # 날짜 패턴이 아닌 짧은 텍스트를 작성자로 간주
                    if text and not re.search(r"\d{4}[-./]\d{2}", text) and len(text) <= 20:
                        return text

            parent = parent.parent

        return ""

    # ------------------------------------------------------------------
    # 공개 메서드
    # ------------------------------------------------------------------

    def fetch_posts(self) -> list[Post]:
        """중고장터 1페이지 게시물 목록을 스크래핑한다.

        Returns:
            완료 카테고리를 제외한 Post 객체 리스트.
            에러 발생 시 빈 리스트를 반환한다.
        """
        try:
            logger.info("게시물 목록 요청 중: %s", self.base_url)
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
        except requests.exceptions.Timeout:
            logger.error("요청 시간 초과: %s", self.base_url)
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error("네트워크 연결 오류: %s", e)
            return []
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP 오류 (%s): %s", response.status_code, e)
            return []
        except requests.exceptions.RequestException as e:
            logger.error("요청 오류: %s", e)
            return []

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            posts = self._parse_posts_from_soup(soup)
            logger.info("총 %d개 게시물 수집 완료 (완료 제외)", len(posts))
            return posts
        except Exception as e:
            logger.error("HTML 파싱 오류: %s", e, exc_info=True)
            return []
