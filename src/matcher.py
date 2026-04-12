"""
보드라이프 중고거래 알림 서비스 - 키워드 매칭 모듈

게시물 제목에서 사용자가 관심있는 키워드를 찾아내는 기능을 제공합니다.
"""


class KeywordMatcher:
    """게시물 제목에서 관심 키워드를 매칭하는 클래스

    대소문자를 무시하고, 공백을 제거한 후 부분 문자열 매칭을 수행합니다.
    """

    def __init__(self, keywords: list[str]):
        """키워드 목록을 초기화합니다.

        Args:
            keywords: 매칭할 키워드 목록
        """
        self.keywords = keywords

    def _normalize_text(self, text: str) -> str:
        """텍스트를 정규화합니다.

        대소문자를 소문자로 변환하고 공백을 제거합니다.
        한국어 특성을 고려하여 처리됩니다.

        Args:
            text: 정규화할 텍스트

        Returns:
            정규화된 텍스트 (소문자, 공백 제거)
        """
        # 대소문자 무시: 소문자로 변환
        text = text.lower()
        # 공백 무시: 모든 공백 제거
        text = text.replace(" ", "")
        return text

    def find_matches(self, title: str) -> list[str]:
        """게시물 제목에서 매칭되는 키워드를 찾습니다.

        정규화된 제목에 정규화된 키워드가 부분 문자열로 포함되어 있으면
        매칭된 것으로 간주합니다.

        Args:
            title: 게시물 제목

        Returns:
            매칭된 키워드 목록 (원본 키워드)
        """
        normalized_title = self._normalize_text(title)
        matched_keywords = []

        for keyword in self.keywords:
            normalized_keyword = self._normalize_text(keyword)
            # 부분 문자열 매칭: 정규화된 제목에 정규화된 키워드가 포함되어 있는지 확인
            if normalized_keyword in normalized_title:
                matched_keywords.append(keyword)

        return matched_keywords

    def update_keywords(self, keywords: list[str]) -> None:
        """키워드 목록을 업데이트합니다.

        Args:
            keywords: 새로운 키워드 목록
        """
        self.keywords = keywords
