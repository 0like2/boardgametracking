"""
보드라이프 중고거래 알림 서비스 - SQLite 데이터베이스 모듈

게시물 추적 및 관심 키워드 관리를 위한 로컬 SQLite 데이터베이스를 제공합니다.
"""

import sqlite3
from datetime import datetime, timedelta


class Database:
    """SQLite 기반 데이터베이스 관리 클래스."""

    def __init__(self, db_path: str):
        """
        데이터베이스 초기화 및 테이블 생성.

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다."""
        conn = sqlite3.connect(self.db_path)
        # Row를 딕셔너리처럼 접근 가능하게 설정
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        """posts, keywords 테이블을 생성합니다 (없을 경우에만)."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id          INTEGER PRIMARY KEY,
                    post_id     TEXT UNIQUE NOT NULL,
                    title       TEXT,
                    category    TEXT,
                    author      TEXT,
                    url         TEXT,
                    price       TEXT DEFAULT '',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id          INTEGER PRIMARY KEY,
                    keyword     TEXT UNIQUE NOT NULL,
                    active      BOOLEAN DEFAULT 1,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # ------------------------------------------------------------------
    # 게시물 관련 메서드
    # ------------------------------------------------------------------

    def is_post_seen(self, post_id: str) -> bool:
        """
        해당 게시물을 이미 확인했는지 여부를 반환합니다.

        Args:
            post_id: 보드라이프 게시물 번호 (bbs_num)

        Returns:
            이미 저장된 게시물이면 True, 아니면 False
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM posts WHERE post_id = ?", (post_id,)
            ).fetchone()
            return row is not None

    def save_post(
        self,
        post_id: str,
        title: str,
        category: str,
        author: str,
        url: str,
        price: str = "",
    ):
        """
        새 게시물 정보를 데이터베이스에 저장합니다.
        이미 존재하는 post_id는 무시합니다 (INSERT OR IGNORE).

        Args:
            post_id:  보드라이프 게시물 번호 (bbs_num)
            title:    게시물 제목
            category: 카테고리 (판매/구매/교환/나눔/완료)
            author:   작성자
            url:      게시물 URL
            price:    게시물 가격 (기본값 빈 문자열)
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO posts (post_id, title, category, author, url, price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (post_id, title, category, author, url, price),
            )
            conn.commit()

    def cleanup_old_posts(self, days: int = 30):
        """
        지정된 기간(일)보다 오래된 게시물 레코드를 삭제합니다.

        Args:
            days: 보존 기간 (기본값 30일). 이보다 오래된 레코드를 삭제합니다.
        """
        # days 경계를 포함하여 삭제하기 위해 1초를 더합니다.
        cutoff = datetime.utcnow() - timedelta(days=days) + timedelta(seconds=1)
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM posts WHERE created_at < ?",
                (cutoff.strftime("%Y-%m-%d %H:%M:%S"),),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # 키워드 관련 메서드
    # ------------------------------------------------------------------

    def add_keyword(self, keyword: str):
        """
        관심 키워드를 추가합니다.
        이미 존재하는 키워드는 활성 상태로 변경합니다.

        Args:
            keyword: 추가할 키워드
        """
        with self._get_connection() as conn:
            # 이미 존재하면 active = 1 로 갱신, 없으면 새로 삽입
            conn.execute(
                """
                INSERT INTO keywords (keyword, active)
                VALUES (?, 1)
                ON CONFLICT(keyword) DO UPDATE SET active = 1
                """,
                (keyword,),
            )
            conn.commit()

    def remove_keyword(self, keyword: str):
        """
        관심 키워드를 비활성화(소프트 삭제)합니다.

        Args:
            keyword: 비활성화할 키워드
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE keywords SET active = 0 WHERE keyword = ?",
                (keyword,),
            )
            conn.commit()

    def get_keywords(self) -> list[str]:
        """
        현재 활성화된 키워드 목록을 반환합니다.

        Returns:
            활성 키워드 문자열 리스트
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT keyword FROM keywords WHERE active = 1 ORDER BY id"
            ).fetchall()
            return [row["keyword"] for row in rows]
