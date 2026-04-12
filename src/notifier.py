"""
알림 모듈
보드라이프 중고거래 매칭 게시물을 Discord 웹훅 및 이메일(SMTP)로 알림 전송
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord Webhook을 이용한 알림 전송 클래스"""

    def __init__(self, webhook_url: str) -> None:
        """
        Discord 웹훅 초기화

        Args:
            webhook_url: Discord 채널 Webhook URL
        """
        self.webhook_url = webhook_url

    def send_alert(
        self,
        title: str,
        category: str,
        author: str,
        url: str,
        matched_keywords: list[str],
        price: str = "",
    ) -> bool:
        """
        매칭된 게시물 알림을 Discord Embed 형식으로 전송

        Args:
            title: 게시물 제목
            category: 게시물 카테고리
            author: 게시물 작성자
            url: 게시물 URL
            matched_keywords: 매칭된 키워드 목록
            price: 게시물 가격 (선택사항)

        Returns:
            전송 성공 여부 (True/False)
        """
        # 매칭 키워드를 쉼표로 연결
        keywords_str = ", ".join(matched_keywords) if matched_keywords else "없음"

        # Embed 필드 구성 (기본 필드)
        fields = [
            {"name": "📌 제목", "value": title, "inline": False},
            {"name": "🏷 카테고리", "value": category, "inline": True},
        ]

        # 가격 정보가 있을 때만 필드 추가
        if price:
            fields.append({"name": "💰 가격", "value": price, "inline": True})

        fields.extend([
            {"name": "✍️ 작성자", "value": author, "inline": True},
            {"name": "🔑 매칭 키워드", "value": keywords_str, "inline": False},
            {"name": "🔗 링크", "value": url, "inline": False},
        ])

        # Discord Embed 페이로드 구성
        payload = {
            "embeds": [
                {
                    "title": "🎲 보드게임 중고 알림!",
                    "color": 0x5865F2,  # Discord 파란색
                    "fields": fields,
                    "url": url,
                }
            ]
        }

        logger.info("Discord 알림 전송 시작 - 제목: %s, 키워드: %s", title, keywords_str)

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)

            # Discord Webhook 성공 응답은 204 No Content
            if response.status_code in (200, 204):
                logger.info("Discord 알림 전송 성공 - 제목: %s", title)
                return True
            else:
                logger.error(
                    "Discord 알림 전송 실패 - HTTP 상태 코드: %d, 응답: %s",
                    response.status_code,
                    response.text,
                )
                return False

        except requests.exceptions.ConnectionError as e:
            logger.error("Discord 네트워크 연결 오류: %s", e)
            return False
        except requests.exceptions.Timeout:
            logger.error("Discord 요청 타임아웃 - 웹훅 서버 응답 없음")
            return False
        except requests.exceptions.RequestException as e:
            logger.error("Discord 요청 오류: %s", e)
            return False

    def send_message(self, message: str) -> bool:
        """
        일반 텍스트 메시지 전송

        Args:
            message: 전송할 메시지 내용

        Returns:
            전송 성공 여부 (True/False)
        """
        payload = {"content": message}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)

            if response.status_code in (200, 204):
                logger.info("Discord 메시지 전송 성공")
                return True
            else:
                logger.error(
                    "Discord 메시지 전송 실패 - HTTP 상태 코드: %d, 응답: %s",
                    response.status_code,
                    response.text,
                )
                return False

        except requests.exceptions.ConnectionError as e:
            logger.error("Discord 네트워크 연결 오류: %s", e)
            return False
        except requests.exceptions.Timeout:
            logger.error("Discord 요청 타임아웃")
            return False
        except requests.exceptions.RequestException as e:
            logger.error("Discord 요청 오류: %s", e)
            return False

    def test_connection(self) -> bool:
        """
        Discord 웹훅 연결 테스트 (테스트 메시지 전송으로 확인)

        Returns:
            연결 성공 여부 (True/False)
        """
        logger.info("Discord 웹훅 연결 테스트 시작")
        result = self.send_message("✅ 보드게임 알림 서비스 연결 테스트 성공!")

        if result:
            logger.info("Discord 웹훅 연결 테스트 성공")
        else:
            logger.error("Discord 웹훅 연결 테스트 실패")

        return result


class EmailNotifier:
    """SMTP를 이용한 이메일 알림 전송 클래스 (표준 라이브러리만 사용)"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        receiver_email: str,
    ) -> None:
        """
        이메일 알림 초기화

        Args:
            smtp_host: SMTP 서버 호스트 (예: smtp.gmail.com)
            smtp_port: SMTP 서버 포트 (예: 587 for TLS, 465 for SSL)
            sender_email: 발신자 이메일 주소
            sender_password: 발신자 이메일 비밀번호 (앱 비밀번호 권장)
            receiver_email: 수신자 이메일 주소
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """
        SMTP 연결 생성 (TLS 지원)

        Returns:
            인증된 SMTP 연결 객체
        """
        # SMTP 서버에 연결
        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
        # TLS 암호화 시작 (포트 587 등에서 사용)
        server.starttls()
        # 이메일 계정 인증
        server.login(self.sender_email, self.sender_password)
        return server

    def send_alert(
        self,
        title: str,
        category: str,
        author: str,
        url: str,
        matched_keywords: list[str],
        price: str = "",
    ) -> bool:
        """
        매칭된 게시물 알림을 HTML 형식 이메일로 전송

        Args:
            title: 게시물 제목
            category: 게시물 카테고리
            author: 게시물 작성자
            url: 게시물 URL
            matched_keywords: 매칭된 키워드 목록
            price: 게시물 가격 (선택사항)

        Returns:
            전송 성공 여부 (True/False)
        """
        # 매칭 키워드를 쉼표로 연결
        keywords_str = ", ".join(matched_keywords) if matched_keywords else "없음"

        # 가격 행 (있을 때만 HTML 테이블에 포함)
        price_row = (
            f"<tr><td style='padding:8px;background:#f9f9f9;font-weight:bold;'>💰 가격</td>"
            f"<td style='padding:8px;'>{price}</td></tr>"
            if price
            else ""
        )

        # HTML 이메일 본문 구성 (게시물 정보 표 형식)
        html_body = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#5865F2;">🎲 보드게임 중고 알림!</h2>
            <table style="width:100%;border-collapse:collapse;border:1px solid #ddd;">
                <tr>
                    <td style="padding:8px;background:#f9f9f9;font-weight:bold;">📌 제목</td>
                    <td style="padding:8px;">{title}</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f9f9f9;font-weight:bold;">🏷 카테고리</td>
                    <td style="padding:8px;">{category}</td>
                </tr>
                {price_row}
                <tr>
                    <td style="padding:8px;background:#f9f9f9;font-weight:bold;">✍️ 작성자</td>
                    <td style="padding:8px;">{author}</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f9f9f9;font-weight:bold;">🔑 매칭 키워드</td>
                    <td style="padding:8px;">{keywords_str}</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f9f9f9;font-weight:bold;">🔗 링크</td>
                    <td style="padding:8px;"><a href="{url}" style="color:#5865F2;">게시물 보기</a></td>
                </tr>
            </table>
        </body>
        </html>
        """

        # 이메일 메시지 객체 생성 (HTML + 텍스트 대체)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[보드게임 알림] {title}"
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        # 텍스트 대체본 (HTML을 지원하지 않는 클라이언트용)
        plain_text = (
            f"보드게임 중고 알림!\n\n"
            f"제목: {title}\n"
            f"카테고리: {category}\n"
            f"{'가격: ' + price + chr(10) if price else ''}"
            f"작성자: {author}\n"
            f"매칭 키워드: {keywords_str}\n"
            f"링크: {url}"
        )

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        logger.info("이메일 알림 전송 시작 - 제목: %s, 수신자: %s", title, self.receiver_email)

        try:
            with self._create_smtp_connection() as server:
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())

            logger.info("이메일 알림 전송 성공 - 수신자: %s", self.receiver_email)
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error("이메일 인증 실패 - 계정 또는 비밀번호를 확인하세요: %s", e)
            return False
        except smtplib.SMTPConnectError as e:
            logger.error("SMTP 서버 연결 실패 - 호스트/포트를 확인하세요: %s", e)
            return False
        except smtplib.SMTPException as e:
            logger.error("이메일 전송 오류: %s", e)
            return False
        except OSError as e:
            logger.error("네트워크 오류 (이메일): %s", e)
            return False

    def send_message(self, message: str) -> bool:
        """
        일반 텍스트 이메일 전송

        Args:
            message: 전송할 메시지 내용

        Returns:
            전송 성공 여부 (True/False)
        """
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = "[보드게임 알림] 메시지"
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        logger.info("이메일 메시지 전송 시작 - 수신자: %s", self.receiver_email)

        try:
            with self._create_smtp_connection() as server:
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())

            logger.info("이메일 메시지 전송 성공")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error("이메일 인증 실패: %s", e)
            return False
        except smtplib.SMTPConnectError as e:
            logger.error("SMTP 서버 연결 실패: %s", e)
            return False
        except smtplib.SMTPException as e:
            logger.error("이메일 전송 오류: %s", e)
            return False
        except OSError as e:
            logger.error("네트워크 오류 (이메일): %s", e)
            return False

    def test_connection(self) -> bool:
        """
        SMTP 서버 연결 테스트 (실제 연결 및 인증만 확인, 메일 미발송)

        Returns:
            연결 성공 여부 (True/False)
        """
        logger.info("SMTP 연결 테스트 시작 - 호스트: %s:%d", self.smtp_host, self.smtp_port)

        try:
            with self._create_smtp_connection():
                # 연결 및 인증 성공 확인 후 즉시 종료
                pass

            logger.info("SMTP 연결 테스트 성공")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP 인증 실패 - 계정 또는 비밀번호를 확인하세요: %s", e)
            return False
        except smtplib.SMTPConnectError as e:
            logger.error("SMTP 서버 연결 실패 - 호스트/포트를 확인하세요: %s", e)
            return False
        except smtplib.SMTPException as e:
            logger.error("SMTP 연결 테스트 오류: %s", e)
            return False
        except OSError as e:
            logger.error("네트워크 오류 (SMTP 테스트): %s", e)
            return False


class MultiNotifier:
    """여러 알림 채널을 묶어 동시 발송하는 복합 알림 클래스"""

    def __init__(self, notifiers: list) -> None:
        """
        복합 알림 초기화

        Args:
            notifiers: DiscordNotifier, EmailNotifier 등 알림 객체 리스트
        """
        self.notifiers = notifiers

    def send_alert(
        self,
        title: str,
        category: str,
        author: str,
        url: str,
        matched_keywords: list[str],
        price: str = "",
    ) -> bool:
        """
        모든 알림 채널에 매칭 게시물 알림 전송

        Args:
            title: 게시물 제목
            category: 게시물 카테고리
            author: 게시물 작성자
            url: 게시물 URL
            matched_keywords: 매칭된 키워드 목록
            price: 게시물 가격 (선택사항)

        Returns:
            하나 이상의 채널에서 전송 성공 시 True, 모두 실패 시 False
        """
        results = []

        for notifier in self.notifiers:
            notifier_name = type(notifier).__name__
            logger.info("%s 알림 전송 시도 중...", notifier_name)

            success = notifier.send_alert(
                title=title,
                category=category,
                author=author,
                url=url,
                matched_keywords=matched_keywords,
                price=price,
            )
            results.append(success)

            if success:
                logger.info("%s 알림 전송 성공", notifier_name)
            else:
                logger.warning("%s 알림 전송 실패", notifier_name)

        # 하나라도 성공하면 True 반환
        any_success = any(results)
        if any_success:
            success_count = sum(results)
            logger.info(
                "복합 알림 전송 완료 - %d/%d 채널 성공",
                success_count,
                len(self.notifiers),
            )
        else:
            logger.error("복합 알림 전송 실패 - 모든 채널에서 전송 실패")

        return any_success

    def send_message(self, message: str) -> bool:
        """
        모든 알림 채널에 일반 메시지 전송

        Args:
            message: 전송할 메시지 내용

        Returns:
            하나 이상의 채널에서 전송 성공 시 True, 모두 실패 시 False
        """
        results = []

        for notifier in self.notifiers:
            notifier_name = type(notifier).__name__
            success = notifier.send_message(message)
            results.append(success)

            if not success:
                logger.warning("%s 메시지 전송 실패", notifier_name)

        any_success = any(results)
        if not any_success:
            logger.error("복합 메시지 전송 실패 - 모든 채널에서 전송 실패")

        return any_success

    def test_connection(self) -> bool:
        """
        모든 알림 채널의 연결 테스트

        Returns:
            하나 이상의 채널에서 연결 성공 시 True, 모두 실패 시 False
        """
        results = []

        for notifier in self.notifiers:
            notifier_name = type(notifier).__name__
            logger.info("%s 연결 테스트 시작...", notifier_name)

            success = notifier.test_connection()
            results.append(success)

            if success:
                logger.info("%s 연결 테스트 성공", notifier_name)
            else:
                logger.warning("%s 연결 테스트 실패", notifier_name)

        any_success = any(results)
        success_count = sum(results)
        logger.info(
            "복합 연결 테스트 완료 - %d/%d 채널 성공",
            success_count,
            len(self.notifiers),
        )

        return any_success
