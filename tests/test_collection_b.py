"""The 2026-06 Boardlife layout reader, checked against a cached page.

cache/boardlife/bl_533.html (자이푸르) is the fixture: two players, best 2,
난이도 1.46, 평점 7.3. If Boardlife rebuilds the page again these break first.
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from export_collection_b import counts, credits, info_value, rank_of, rating_of, span, vote_value

FIXTURE = Path(__file__).parent.parent / "cache/boardlife/bl_533.html"


@pytest.fixture(scope="module")
def soup():
    if not FIXTURE.exists():
        pytest.skip("boardlife cache not present")
    return BeautifulSoup(FIXTURE.read_bytes(), "html.parser")


def test_reads_publisher_row(soup):
    assert span(info_value(soup, "인원")) == (2, 2)
    assert span(info_value(soup, "시간")) == (30, 30)
    assert info_value(soup, "연령").startswith("12")


def test_reads_community_votes(soup):
    assert vote_value(soup, "난이도") == "1.46"
    assert vote_value(soup, "카테고리") == "가족"
    best, _, rec = vote_value(soup, "베스트 / 추천").partition("/")
    assert counts(best) == [2] and counts(rec) == [2]


def test_reads_rating_and_rank(soup):
    assert rating_of(soup) == 7.3
    assert rank_of(soup) == 401


def test_reads_designers(soup):
    assert credits(soup, "디자이너") == ["Sébastien Pauchon"]


def test_span_handles_ranges_and_blanks():
    assert span("2-4명") == (2, 4)
    assert span("30~60분") == (30, 60)
    assert span("") == (None, None)
    assert counts("3~4인") == [3, 4]
    assert counts("-") == []
