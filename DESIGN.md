# Design

## Source of truth
Active · 2026-09-09 · 기존 컬렉션과 신규 `/azit`, `/azit/admin`.
근거: `web/src/app/{layout.tsx,page.tsx,globals.css}`, `RequestForm.tsx`, `AuthButton.tsx`, `web/supabase/schema.sql`, 사용자 아지트 안내와 시간 확인 답변. 기존 디자인 문서와 공간 사진은 없음.

## Brand
친근한 보드게임 모임. 기존 어두운 카드와 파란 액션을 유지한다. 실제 공간 사진·수용 인원·후기를 만들어내지 않는다.

## Product goals
시간표 확인 → 신청 → 접수중 → 관리자 확인 → 확정. 동시간대 중복 접수를 DB에서 차단하고 변경을 다른 방문자에게 전달한다. 결제·월 이용권 판매·자동 자격 검증은 이번 범위에 없다.

## Personas and jobs
참가자는 월 이용권 보유자와 가능한 시간을 찾고 예약한다. 운영자는 동행자의 이용권, 심야 참여와 주차를 확인하고 확정·취소한다.

## Information architecture
기존 목록과 상단 내비게이션에서 아지트로 연결. `/azit`: 소개·가격 → 날짜/시간표와 신청서 → 위치·이용 안내. `/azit/admin`: 접근 확인 → 접수/확정/지난 내역 → 확인 항목과 상태 변경.

## Design principles
접수와 확정은 구별한다. 예약 시간은 모두 한국 시간이다. 월·화 18–22시, 토 09–19시, 일 09–12시는 이용 불가, 그 외 신청 가능. 00:10–09:00 이용은 운영자 동행 확인이 필요하다. 데이터 조회 실패를 빈 시간표로 표현하지 않는다.

## Visual language
`globals.css`의 bg/panel/panel-2/line/ink/accent/weight/rating 토큰과 Noto Sans KR 재사용. 모서리 12–24px, 간격 4/8/12/16/24px. 접수중은 주황, 확정은 파랑, 고정 이용 불가는 회색. lucide 아이콘. 상태는 항상 텍스트 병기.

## Components
기존 Link, AuthButton과 스타일을 재사용. AzitBooking은 달력·선택일 시간표·신청서·접수 결과를 담당. AzitAdmin은 비공개 내역과 승인 작업을 담당. 시간 규칙은 `lib/azit.ts`에 모은다.

## Accessibility
키보드와 터치 접근, 레이블 있는 입력, 선택 상태 aria-pressed, 오류 role=alert, 상태 aria-live. 색상만으로 구별하지 않는다. 표준 date/time/select 컨트롤. 눈에 보이는 포커스와 reduced-motion 준수.

## Responsive behavior
모바일은 한 열, 큰 화면은 시간표 왼쪽·예약서 오른쪽. 헤더는 좁은 화면에서 줄바꿈한다. 달력은 7열을 유지하며 가로 넘침을 만들지 않는다.

## Interaction states
최초 불러오기, 접수 없는 날짜, 조회 실패와 재시도, 선택 불가 시간, 전송 중, 접수 성공, 다른 예약과 충돌을 구분. 실시간 신호와 주기 조회로 최신 상태를 갱신한다. 조회 실패 시 제출을 막고 마지막 자료가 오래되었음을 알린다.

## Content voice
짧고 친근한 한국어. ‘예약 접수중’은 승인 전 상태임을 명시. 비용은 이용권 안내/예상 금액으로 표시하며 결제 완료로 표현하지 않는다. 연락처와 메모는 관리자만 확인한다.

## Implementation constraints
Next.js 16 / React 19 / Tailwind 4 / 기존 Supabase, 추가 의존성 없음. 두 번째 컬렉션의 목록 전용 동작을 유지. DB는 원본 신청 테이블을 보존하는 추가 마이그레이션. 예약 저장을 성공의 기준으로 삼고 기존 Discord 웹후크로 접수 알림을 보낸다. 공용 응답은 시간·상태만, 관리자 권한은 검증된 로그인 사용자의 UUID가 비공개 `space_admins` 허용 목록에 있을 때만 부여한다. 규칙 테스트·타입 검사·lint·빌드·API 검사로 검증한다.

## Open questions
- [ ] 운영자: 배포 시 예약 DB 마이그레이션 적용 후 Supabase Auth 사용자 UUID를 `space_admins`에 수동 등록해야 한다. 운영 데이터 변경과 배포는 별도 작업.
- [ ] 운영자: 공간 사진·최대 수용 인원·결제 방법은 미제공. 화면에 임의로 기입하지 않는다.
