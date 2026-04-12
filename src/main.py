"""
보드라이프 중고거래 알림 서비스 - 메인 실행 모듈

CLI 명령어:
    python -m src.main run              # 모니터링 시작 (스케줄러)
    python -m src.main add "버건디의 성"  # 키워드 추가
    python -m src.main remove "브라스"    # 키워드 제거
    python -m src.main list              # 등록된 키워드 목록 보기
    python -m src.main test              # 텔레그램 봇 연결 테스트
    python -m src.main check             # 한번만 체크 (디버깅용)
"""

import argparse
import logging
import time

import schedule
import yaml

from src.database import Database
from src.matcher import KeywordMatcher
from src.notifier import DiscordNotifier, EmailNotifier, MultiNotifier
from src.scraper import BoardLifeScraper

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------

def load_config(path: str = "config.yaml") -> dict:
    """config.yaml 파일을 로드하여 딕셔너리로 반환합니다.

    Args:
        path: 설정 파일 경로 (기본값: config.yaml)

    Returns:
        설정 딕셔너리
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 핵심 로직: 새 게시물 체크
# ---------------------------------------------------------------------------

def _create_notifier(config: dict) -> MultiNotifier:
    """설정에 따라 활성화된 알림 채널로 MultiNotifier를 구성합니다."""
    notifiers = []

    # Discord 설정
    discord_config = config.get("discord", {})
    if discord_config.get("enabled", False):
        notifiers.append(DiscordNotifier(
            webhook_url=discord_config["webhook_url"]
        ))

    # Email 설정
    email_config = config.get("email", {})
    if email_config.get("enabled", False):
        notifiers.append(EmailNotifier(
            smtp_host=email_config["smtp_host"],
            smtp_port=email_config["smtp_port"],
            sender_email=email_config["sender_email"],
            sender_password=email_config["sender_password"],
            receiver_email=email_config["receiver_email"],
        ))

    if not notifiers:
        logger.warning("활성화된 알림 채널이 없습니다. config.yaml을 확인하세요.")

    return MultiNotifier(notifiers)


def check_new_posts(
    scraper: BoardLifeScraper,
    db: Database,
    matcher: KeywordMatcher,
    notifier: MultiNotifier,
) -> None:
    """중고장터 게시물을 수집하고 매칭 시 알림을 전송합니다.

    1. 스크래퍼로 최신 게시물 목록 수집
    2. 이미 확인한 게시물은 건너뜀
    3. 새 게시물에서 키워드 매칭 탐색
    4. 매칭된 게시물은 알림 전송
    5. 모든 새 게시물을 DB에 저장
    6. DB 키워드를 다시 로드하여 matcher 갱신

    Args:
        scraper:  BoardLifeScraper 인스턴스
        db:       Database 인스턴스
        matcher:  KeywordMatcher 인스턴스
        notifier: MultiNotifier 인스턴스
    """
    logger.info("새 게시물 체크 시작")
    posts = scraper.fetch_posts()

    if not posts:
        logger.info("수집된 게시물이 없습니다.")
        return

    new_count = 0
    matched_count = 0

    for post in posts:
        # 이미 확인한 게시물이면 건너뜀
        if db.is_post_seen(post.post_id):
            continue

        new_count += 1

        # 키워드 매칭
        matched = matcher.find_matches(post.title)
        if matched:
            matched_count += 1
            logger.info(
                "매칭 발견 - 제목: %s | 키워드: %s | 가격: %s",
                post.title,
                ", ".join(matched),
                post.price or "없음",
            )
            notifier.send_alert(
                title=post.title,
                category=post.category,
                author=post.author,
                url=post.url,
                matched_keywords=matched,
                price=post.price,
            )

        # 새 게시물 DB 저장 (매칭 여부와 무관하게 저장)
        db.save_post(
            post_id=post.post_id,
            title=post.title,
            category=post.category,
            author=post.author,
            url=post.url,
            price=post.price,
        )

    logger.info(
        "체크 완료 - 신규: %d개, 매칭: %d개 (전체 수집: %d개)",
        new_count,
        matched_count,
        len(posts),
    )

    # DB에서 키워드를 다시 로드하여 matcher 업데이트 (실시간 키워드 변경 반영)
    updated_keywords = db.get_keywords()
    matcher.update_keywords(updated_keywords)
    logger.debug("키워드 목록 갱신 완료 - %d개", len(updated_keywords))


# ---------------------------------------------------------------------------
# CLI 명령어 핸들러
# ---------------------------------------------------------------------------

def cmd_run(config: dict) -> None:
    """모니터링을 시작합니다. schedule 라이브러리로 주기적으로 실행합니다.

    - config.yaml의 keywords를 DB에 시드로 추가
    - 설정된 간격(interval_minutes)마다 check_new_posts() 실행
    - 하루 1회 30일 이상 된 게시물 정리

    Args:
        config: config.yaml에서 로드한 설정 딕셔너리
    """
    import os
    db_dir = os.path.dirname(config["database"]["path"])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # 모듈 초기화
    db = Database(config["database"]["path"])
    scraper = BoardLifeScraper(
        base_url=config["scraping"]["url"],
        user_agent=config["scraping"]["user_agent"],
    )
    notifier = _create_notifier(config)

    # config.yaml의 keywords를 DB에 시드로 추가 (이미 있으면 무시됨)
    seed_keywords: list[str] = config.get("keywords", [])
    for kw in seed_keywords:
        db.add_keyword(kw)
    if seed_keywords:
        logger.info("시드 키워드 %d개 DB에 추가 완료", len(seed_keywords))

    # DB에서 키워드 로드 → KeywordMatcher 초기화
    keywords = db.get_keywords()
    matcher = KeywordMatcher(keywords)
    logger.info("키워드 %d개 로드 완료: %s", len(keywords), keywords)

    # 시작 알림 전송
    notifier.send_message("🟢 보드라이프 모니터링 시작")
    logger.info("시작 알림 전송 완료")

    # 체크 주기 설정
    interval_minutes: int = config["scraping"].get("interval_minutes", 5)

    # 즉시 한 번 실행 후 스케줄 등록
    check_new_posts(scraper, db, matcher, notifier)

    schedule.every(interval_minutes).minutes.do(
        check_new_posts, scraper, db, matcher, notifier
    )
    logger.info("%d분 간격으로 모니터링 중...", interval_minutes)

    # 하루 1회 오래된 게시물 정리 (자정 기준)
    schedule.every().day.at("00:00").do(db.cleanup_old_posts, days=30)
    logger.info("30일 이상 된 게시물 자동 정리 스케줄 등록 완료")

    print(f"모니터링 시작 (체크 간격: {interval_minutes}분). 종료하려면 Ctrl+C를 누르세요.")

    # 스케줄 루프
    while True:
        schedule.run_pending()
        time.sleep(1)


def cmd_add(config: dict, keyword: str) -> None:
    """키워드를 DB에 추가합니다.

    Args:
        config:  설정 딕셔너리
        keyword: 추가할 키워드
    """
    db = Database(config["database"]["path"])
    db.add_keyword(keyword)
    print(f"키워드 추가 완료: '{keyword}'")
    logger.info("키워드 추가: %s", keyword)


def cmd_remove(config: dict, keyword: str) -> None:
    """키워드를 DB에서 비활성화합니다.

    Args:
        config:  설정 딕셔너리
        keyword: 제거할 키워드
    """
    db = Database(config["database"]["path"])
    db.remove_keyword(keyword)
    print(f"키워드 제거 완료: '{keyword}'")
    logger.info("키워드 제거: %s", keyword)


def cmd_list(config: dict) -> None:
    """현재 등록된 활성 키워드 목록을 출력합니다.

    Args:
        config: 설정 딕셔너리
    """
    db = Database(config["database"]["path"])
    keywords = db.get_keywords()

    if not keywords:
        print("등록된 키워드가 없습니다.")
        return

    print(f"등록된 키워드 목록 ({len(keywords)}개):")
    for i, kw in enumerate(keywords, start=1):
        print(f"  {i}. {kw}")


def cmd_test(config: dict) -> None:
    """알림 채널 연결 상태를 테스트합니다.

    Args:
        config: 설정 딕셔너리
    """
    notifier = _create_notifier(config)
    print("알림 연결 테스트 중...")
    success = notifier.test_connection()
    if success:
        print("알림 연결 성공!")
    else:
        print("알림 연결 실패. 로그를 확인하세요.")


def cmd_check(config: dict) -> None:
    """게시물을 한 번만 체크합니다 (디버깅용).

    Args:
        config: 설정 딕셔너리
    """
    db = Database(config["database"]["path"])
    scraper = BoardLifeScraper(
        base_url=config["scraping"]["url"],
        user_agent=config["scraping"]["user_agent"],
    )
    notifier = _create_notifier(config)

    keywords = db.get_keywords()
    matcher = KeywordMatcher(keywords)

    print(f"게시물 체크 시작 (활성 키워드: {len(keywords)}개)")
    check_new_posts(scraper, db, matcher, notifier)
    print("게시물 체크 완료.")


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI 진입점. argparse로 명령어를 파싱하고 해당 핸들러를 호출합니다."""
    parser = argparse.ArgumentParser(
        description="보드라이프 중고거래 알림 서비스",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "사용 예시:\n"
            '  python -m src.main run\n'
            '  python -m src.main add "버건디의 성"\n'
            '  python -m src.main remove "브라스"\n'
            '  python -m src.main list\n'
            '  python -m src.main test\n'
            '  python -m src.main check\n'
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="명령어")
    subparsers.required = True

    # run: 모니터링 시작
    subparsers.add_parser("run", help="모니터링 시작 (스케줄러)")

    # add: 키워드 추가
    add_parser = subparsers.add_parser("add", help="키워드 추가")
    add_parser.add_argument("keyword", help="추가할 키워드")

    # remove: 키워드 제거
    remove_parser = subparsers.add_parser("remove", help="키워드 제거")
    remove_parser.add_argument("keyword", help="제거할 키워드")

    # list: 키워드 목록
    subparsers.add_parser("list", help="등록된 키워드 목록 보기")

    # test: 텔레그램 봇 연결 테스트
    subparsers.add_parser("test", help="텔레그램 봇 연결 테스트")

    # check: 한번만 체크
    subparsers.add_parser("check", help="한번만 체크 (디버깅용)")

    args = parser.parse_args()

    # 설정 로드
    try:
        config = load_config("config.yaml")
    except FileNotFoundError:
        print("오류: config.yaml 파일을 찾을 수 없습니다.")
        print("config.yaml.example을 참고하여 config.yaml을 생성하세요.")
        return
    except yaml.YAMLError as e:
        print(f"오류: config.yaml 파싱 실패 - {e}")
        return

    # 명령어 라우팅
    if args.command == "run":
        cmd_run(config)
    elif args.command == "add":
        cmd_add(config, args.keyword)
    elif args.command == "remove":
        cmd_remove(config, args.keyword)
    elif args.command == "list":
        cmd_list(config)
    elif args.command == "test":
        cmd_test(config)
    elif args.command == "check":
        cmd_check(config)
