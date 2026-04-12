"""English → Korean translator for BGG category and mechanic names.

Translation happens only inside CardViewModel.from_game_data(); GameData
always stores English canonical strings.
"""

from __future__ import annotations


def _contains_hangul(s: str) -> bool:
    """True if the string has any Korean syllable (U+AC00..U+D7A3)."""
    return any("\uac00" <= ch <= "\ud7a3" for ch in s)


# ~50 common BGG category / mechanic terms
_DEFAULT_DICTIONARY: dict[str, str] = {
    # Categories
    "Abstract Strategy": "추상 전략",
    "Adventure": "어드벤처",
    "Age of Reason": "이성의 시대",
    "Ancient": "고대",
    "Animals": "동물",
    "Aviation / Flight": "항공",
    "Bluffing": "블러핑",
    "Card Game": "카드게임",
    "City Building": "도시 건설",
    "Civil War": "내전",
    "Civilization": "문명",
    "Collectible Components": "수집형",
    "Comic Book / Strip": "만화",
    "Deduction": "추리",
    "Dice": "주사위",
    "Economic": "경제",
    "Educational": "교육",
    "Environmental": "환경",
    "Exploration": "탐험",
    "Fantasy": "판타지",
    "Fighting": "전투",
    "Horror": "공포",
    "Humor": "유머",
    "Industry / Manufacturing": "산업",
    "Mafia": "마피아",
    "Math": "수학",
    "Mature / Adult": "성인",
    "Medieval": "중세",
    "Memory": "기억력",
    "Miniatures": "미니어처",
    "Movies / TV / Radio theme": "미디어",
    "Murder/Mystery": "미스터리",
    "Music": "음악",
    "Mythology": "신화",
    "Napoleonic": "나폴레옹",
    "Negotiation": "협상",
    "Novel-based": "소설 원작",
    "Number": "숫자",
    "Pirates": "해적",
    "Political": "정치",
    "Post-Napoleonic": "근대",
    "Prehistoric": "선사시대",
    "Print & Play": "프린트앤플레이",
    "Puzzle": "퍼즐",
    "Racing": "레이싱",
    "Real-time": "실시간",
    "Renaissance": "르네상스",
    "Science Fiction": "SF",
    "Space Exploration": "우주 탐험",
    "Spies/Secret Agents": "스파이",
    "Sports": "스포츠",
    "Strategy": "전략",
    "Territory Building": "영토 건설",
    "Trains": "기차",
    "Transportation": "교통",
    "Travel": "여행",
    "Trivia": "퀴즈",
    "Video Game Theme": "비디오게임",
    "Wargame": "워게임",
    "Word Game": "단어게임",
    "World War I": "1차 세계대전",
    "World War II": "2차 세계대전",
    # Mechanics
    "Action Points": "행동 포인트",
    "Action Queue": "행동 대기열",
    "Area Control": "지역 장악",
    "Area Movement": "지역 이동",
    "Auction/Bidding": "경매/입찰",
    "Bag Building": "백 빌딩",
    "Campaign / Battle Card Driven": "캠페인",
    "Card Drafting": "카드 드래프팅",
    "Cooperative Game": "협력 게임",
    "Deck Building": "덱 빌딩",
    "Deck Construction": "덱 구성",
    "Dice Rolling": "주사위 굴리기",
    "Engine Building": "엔진 빌딩",
    "Hand Management": "핸드 매니지먼트",
    "Hex-and-Counter": "헥스 카운터",
    "Hidden Roles": "비밀 역할",
    "Income": "수입",
    "Network and Route Building": "네트워크 구축",
    "Once-Per-Game Abilities": "일회성 능력",
    "Open Drafting": "오픈 드래프팅",
    "Pattern Building": "패턴 빌딩",
    "Pick-up and Deliver": "픽업 앤 딜리버",
    "Point to Point Movement": "점 대 점 이동",
    "Push Your Luck": "푸시 유어 럭",
    "Resource Management": "자원 관리",
    "Role Playing": "롤플레잉",
    "Route/Network Building": "루트 구축",
    "Semi-Cooperative Game": "반협력 게임",
    "Set Collection": "세트 수집",
    "Simultaneous Action Selection": "동시 행동 선택",
    "Solo / Solitaire Game": "솔로 게임",
    "Storytelling": "스토리텔링",
    "Team-Based Game": "팀 게임",
    "Tile Placement": "타일 배치",
    "Trading": "트레이딩",
    "Turn Order: Claim Action": "행동 순서 선택",
    "Variable Player Powers": "플레이어 특수 능력",
    "Variable Set-up": "가변 설정",
    "Voting": "투표",
    "Worker Placement": "일꾼 배치",
}


class Translator:
    """Translates English BGG terms to Korean.

    Unknown terms are passed through as-is and recorded for later reporting.
    """

    def __init__(self, dictionary: dict[str, str] | None = None) -> None:
        self._dict: dict[str, str] = (
            dict(_DEFAULT_DICTIONARY) if dictionary is None else dict(dictionary)
        )
        self._misses: set[str] = set()

    def translate(self, english: str) -> str:
        """Return Korean translation or the original string as fallback.

        Strings that already contain Hangul characters are returned as-is and
        not tracked as misses — they came from a Korean-native source
        (e.g. Boardlife's 테마/진행방식 labels).
        """
        if _contains_hangul(english):
            return english
        result = self._dict.get(english)
        if result is None:
            self._misses.add(english)
            return english
        return result

    def missing_terms(self) -> set[str]:
        """Return all English terms that had no Korean translation."""
        return set(self._misses)

    def report_missing(self) -> None:
        """Print missing terms to stderr."""
        import sys

        if self._misses:
            print("Missing translations:", file=sys.stderr)
            for term in sorted(self._misses):
                print(f"  {term}", file=sys.stderr)
