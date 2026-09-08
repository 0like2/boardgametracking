# 보드게임 컬렉션

소장 보드게임 122종 목록 · 자료실 · 대여 예약 / 모임 요청 · 플레이 카드 수집.

Next.js 16 + Tailwind 4 + Supabase. PWA로 홈화면에 설치할 수 있습니다.

## 실행

```bash
npm install
npm run dev        # http://localhost:3000
```

## 배포 전 설정

`.env.example`을 `.env.local`로 복사하고 채웁니다. 신청 내역은 Supabase에 저장하고
새 신청 알림은 Discord 웹후크로 보냅니다. 저장에 실패하면 성공으로 응답하지 않으며,
Discord 장애가 저장된 예약을 취소하지는 않습니다.

| 변수 | 용도 |
| --- | --- |
| `DISCORD_WEBHOOK_URL` | 신청이 오면 디스코드 채널에 임베드로 전송 |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | 로그인과 실시간 예약 갱신 |
| `SUPABASE_SERVICE_ROLE_KEY` | 비공개 신청 저장·조회와 관리자 확인 |

아지트 기능을 배포한다면 `supabase/schema.sql`을 SQL Editor에 붙여넣어 실행하세요.
RLS는 켜두고 정책을 만들지 않습니다 — 서버(service role)만 접근하므로 연락처가
공개로 새지 않습니다.

Vercel에 올릴 때는 같은 변수를 프로젝트 환경 변수에 넣으면 됩니다.

## 보드게임 아지트 예약

아지트 예약은 Supabase가 필수입니다. 먼저 `supabase/schema.sql`, 다음으로
`supabase/azit.sql`을 SQL Editor에서 실행합니다. 예약표에는 시간과 상태만 공개되며
이름·연락처는 service role을 쓰는 서버와 허용된 관리자만 조회합니다. 신청이 저장되면
기존 `DISCORD_WEBHOOK_URL`로 알림을 보내고, 승인은 웹사이트의 `/azit/admin`에서 합니다.
아지트 디스코드 알림에는 예약 번호·시간·인원·확인할 조건과 관리 링크만 들어갑니다.
이름·연락처·메모는 디스코드에 보내지 않습니다. 알림이 실패해도 예약은 유지하며,
신청자에게 운영자에게 직접 알려달라는 안내를 표시합니다.

관리자는 Supabase Dashboard의 Authentication → Users에서 본인 UUID를 확인한 뒤 SQL
Editor에서 직접 등록합니다. 이메일·프로필 권한·첫 로그인 사용자를 자동으로 관리자로
지정하지 않습니다.

```sql
insert into public.space_admins (user_id)
values ('Supabase Auth 사용자 UUID')
on conflict (user_id) do nothing;
```

예약은 한국시간 10분 단위, 최대 24시간, 90일 이내로 접수합니다. 자정을 넘길 때는 종료
날짜를 따로 선택해야 합니다. 월 이용권 사용자가 최소 1명 필요하며 관리자가 실제 소유자를 확인한
뒤 승인합니다. 결제 기능은 없고 주차·심야 동행 요청도 승인 전에 관리자가 확인합니다.

`azit.sql`은 겹치는 접수중/확정 예약을 DB 제약으로 막고 `azit-availability` 주제에
`booking_changed` 이벤트를 방송합니다. 방송 실패는 예약 저장을 취소하지 않으므로 화면은
실시간 구독과 주기적 재조회 모두를 사용해야 합니다. DB 제약 확인용 `tests/azit-db.sql`은
비운영 DB에서 실행하며 마지막에 항상 롤백합니다.

예약 규칙과 API 검사는 Node.js 24에서 실행합니다. API 검사는 저장소·로그인을 대체해
개인정보 공개 범위, 권한, 접수 실패·충돌을 확인하며 실제 예약을 만들지 않습니다.

```bash
node --experimental-strip-types --test tests/azit.test.ts tests/azit-api.test.mjs tests/notify.test.ts
npx tsc --noEmit
```

공개 시간표는 실시간 신호를 받으면 다시 조회하고, 연결 상태와 무관하게 15초마다
보완 조회합니다. 실제 DB 충돌 제약·실시간 이벤트는 마이그레이션 적용 후 별도로 확인해야 합니다.

## 두 번째 컬렉션

같은 코드가 두 사람의 컬렉션을 서비스합니다. 어느 쪽인지는 코드 분기가 아니라
Vercel 프로젝트의 환경 변수가 정합니다.

| 변수 | 용도 |
| --- | --- |
| `NEXT_PUBLIC_COLLECTION` | 비우면 `data/games.json`(주 컬렉션), `b`면 `data/games.b.json` |
| `NEXT_PUBLIC_SITE_TITLE` | 헤더·`<title>`·홈화면 설치 이름 |

`b`로 띄운 사이트는 **목록 전용**입니다 — 모임 신청·랭킹·플레이 카드 라우트가
404를 돌려주고 네비게이션에서도 빠집니다. 그래서 그 프로젝트에는 Supabase도
알림 채널도 넣을 필요가 없습니다.

두 값 모두 `NEXT_PUBLIC_` 접두사라 **빌드 시점에 박힙니다.** 바꾸면 재배포해야
반영됩니다.

데이터는 `python export_collection_b.py`로 다시 만듭니다
(`inputs/collection_b.tsv` = 소장 목록, `inputs/collection_b_ids.json` = 보드라이프 id).


## 데이터 갱신

게임 데이터와 자료는 상위 폴더의 파이썬 파이프라인이 만듭니다. 캐시된 보드라이프
HTML만 읽으므로 네트워크 없이 다시 돌릴 수 있습니다.

```bash
cd ..
source venv/bin/activate
python export_web_data.py    # -> web/data/games.json (122종)
python build_materials.py    # -> web/public/materials/ + web/data/materials.json
```

새 게임을 추가하려면 `output/2026-07-05/게임목록_3월_5월_7월.xlsx`에 행을 넣고
해당 보드라이프 페이지를 `cache/boardlife/bl_<id>.html`로 저장한 뒤 위 스크립트를
다시 돌립니다. 커버 이미지는 `cache/images/bl_<id>.jpg`에서 가져옵니다.

새 자료를 붙이려면 `build_materials.py`의 `MAP`에
`(게임 한글명, 종류, 라벨, 파일명)` 한 줄을 추가하세요. 2.5MB가 넘는 PDF는
130 DPI로 자동 재압축됩니다.

## 인스타 피드 이미지

```bash
cd ..
python make_insta.py posts/example.yaml    # -> output/instagram/example/*.png
```

`posts/*.yaml`에 게임 이름·사진·등수·후기만 쓰면 영문명·커버·난이도·평점·인원·시간·
소개글은 `games.json`에서 자동으로 채워집니다. 템플릿은 `review`(후기),
`intro`(소개), `rules`(간단 규칙) 세 가지입니다. 내용이 캔버스를 넘치면 렌더할 때
경고가 찍히므로, 그때만 후기를 줄이거나 스텝을 빼면 됩니다.

## 구조

- `src/lib/games.ts` — 게임 데이터 로딩, 인원 적합도(`playerFit`), 표시용 포매터
- `src/components/GameCard.tsx` — 인쇄 카드와 같은 디자인. 그리드에서 hover하면
  카드 위에 설명·베스트/추천 인원·디자이너·순위가 뜹니다
- `src/components/GameSheet.tsx` — 카드를 누르면 열리는 액션 시트
  (대여 예약 / 모임 열어주세요 / 플레이 기록 / 상세)
- `src/lib/collection.ts` — 플레이 기록. 계정이 없으므로 localStorage에 저장하고,
  기록한 게임의 카드가 「내 카드」에서 열립니다
- `src/app/api/requests/route.ts` — 신청 접수. 허니팟 + IP당 10분 5건 제한
