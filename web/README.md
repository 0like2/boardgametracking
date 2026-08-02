# 보드게임 컬렉션

소장 보드게임 122종 목록 · 자료실 · 대여 예약 / 모임 요청 · 플레이 카드 수집.

Next.js 16 + Tailwind 4 + Supabase(선택). PWA로 홈화면에 설치할 수 있습니다.

## 실행

```bash
npm install
npm run dev        # http://localhost:3000
```

## 배포 전 설정

`.env.example`을 `.env.local`로 복사하고 채웁니다. **모든 값이 선택 사항이고,
비어 있는 채널은 그냥 건너뜁니다.** 다만 알림 채널과 Supabase가 전부 비어 있으면
신청 API가 503을 돌려줍니다 — 아무 데도 안 갔는데 "전달됐습니다"라고 하지 않기 위해서입니다.

| 변수 | 용도 |
| --- | --- |
| `DISCORD_WEBHOOK_URL` | 신청이 오면 디스코드 채널에 임베드로 전송 |
| `SMTP_USER` / `SMTP_PASSWORD` / `NOTIFY_EMAIL_TO` | 신청 알림 이메일 (Gmail 앱 비밀번호) |
| `NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | 신청 내역 저장 + 「신청 현황」 페이지 |

Supabase를 쓴다면 `supabase/schema.sql`을 SQL Editor에 붙여넣어 실행하세요.
RLS는 켜두고 정책을 만들지 않습니다 — 서버(service role)만 접근하므로 연락처가
공개로 새지 않습니다.

Vercel에 올릴 때는 같은 변수를 프로젝트 환경 변수에 넣으면 됩니다.

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
