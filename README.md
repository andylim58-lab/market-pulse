# 마켓 펄스 (Market Pulse)

네이버 · 유튜브 · 구글 데이터를 한 화면에서 보는 **개인용 시장 흐름 대시보드**입니다.
GitHub Actions가 하루 3번 데이터를 수집·분석하고, GitHub Pages가 사이트를 보여줍니다. 서버 비용은 0원입니다.

```
[GitHub Actions: 06:47 / 12:47 / 18:47 KST]
  네이버 데이터랩(검색어 트렌드·쇼핑인사이트) ─┐
  네이버 검색광고 키워드도구 ─────────────────┤→ data/ (원자료·히스토리 커밋)
  유튜브 한국 인기 동영상 ───────────────────┤→ analyze.py → site/data/summary.json
  구글 실시간 인기 검색어 RSS ────────────────┘→ GitHub Pages 배포 (site/)
```

## 화면 구성
| 탭 | 내용 |
|---|---|
| 개요 | 7개 시장 카드(30일 검색수, 전년비, 28일 변화, 신호), 플랫폼 교차 신호표, 시장 간 관심도 비교 |
| 시장 상세 | 주제어별 검색 추이(월간 36개월/일간 120일), 주제어 지표, 연관 키워드 Top 30, 이 시장 관련 유튜브·구글 항목 |
| 쇼핑 분야 | 쇼핑 분야별 클릭 전년비, 분야 추이 비교, 연령·성별 클릭 비중(최근 3개월 vs 1년 전) |
| 지금 뜨는 것 | 구글 실시간 인기 검색어(오늘/7일 반복), 유튜브 새로 뜨는 단어, 카테고리 비중, 조회수 상승 속도 |
| 기회 키워드 | 검색수 크고 · 경쟁도 낮고 · 전월보다 늘어난 키워드 순위 |

---

## 설치 (약 30분, 한 번만)

### 1단계. API 키 4종 발급

| 키 | 발급처 | 비용 |
|---|---|---|
| ① 네이버 데이터랩 | 네이버클라우드 콘솔 → Services → Application Services → **NAVER API HUB** → Application 등록 → **검색어 트렌드 + 쇼핑 인사이트** 선택 → 인증정보에서 Client ID / Secret 확인 | 현재 한시 무료 (API별 월 5만 건) |
| ② 네이버 검색광고 | searchad.naver.com → 광고시스템 → 도구 → **API 사용 관리** → 서비스 신청 → CUSTOMER_ID, 액세스라이선스, 비밀키 | 무료 (광고 집행 불필요) |
| ③ 유튜브 | Google Cloud Console → 새 프로젝트 → API 및 서비스 → **YouTube Data API v3** 사용 설정 → 사용자 인증 정보 → API 키 생성 (키 제한: YouTube Data API v3만) | 무료 (하루 1만 유닛, 이 프로젝트는 하루 약 45유닛) |
| ④ 구글 트렌드 | 필요 없음 (공개 RSS) | 무료 |

> 2026-07-31 이전에 네이버 **개발자센터**에서 받은 데이터랩 키가 있다면 그대로 쓸 수 있습니다(2027-06-30까지). 이 경우 아래 Secrets에 `NAVER_LEGACY` = `1` 을 추가하세요.

### 2단계. GitHub 저장소 만들기
1. GitHub에서 새 저장소 생성 (예: `market-pulse`).
   - **공개(Public)** 저장소여야 무료 계정에서 Pages를 쓸 수 있습니다. API 키는 Secrets에만 들어가므로 공개되지 않고, 공개되는 것은 코드와 집계 데이터뿐입니다.
   - 사이트에는 검색엔진 노출 차단(noindex)이 걸려 있어 주소를 아는 사람만 보게 됩니다. 완전 비공개가 필요하면 GitHub Pro(유료)에서 비공개 저장소 + Pages를 쓰거나, 미니PC로 옮기면 됩니다.
2. 이 폴더 전체를 업로드합니다 (웹에서 "Add file → Upload files"로 끌어다 놓거나 `git push`).
   - `.github` 폴더가 빠지지 않게 주의하세요(숨김 폴더).

### 3단계. Secrets 등록
저장소 → **Settings → Secrets and variables → Actions → New repository secret** 으로 아래 6개를 추가합니다.

| 이름 | 값 |
|---|---|
| `NAVER_HUB_ID` | ① Client ID |
| `NAVER_HUB_SECRET` | ① Client Secret |
| `NAVER_AD_CUSTOMER_ID` | ② CUSTOMER_ID (숫자) |
| `NAVER_AD_ACCESS_LICENSE` | ② 액세스라이선스 |
| `NAVER_AD_SECRET_KEY` | ② 비밀키 |
| `YOUTUBE_API_KEY` | ③ API 키 |

키가 없는 소스는 자동으로 건너뜁니다. 예를 들어 유튜브 키만 먼저 넣어도 동작합니다.

### 4단계. Pages 켜기
저장소 → **Settings → Pages → Build and deployment → Source: GitHub Actions** 선택.

### 5단계. 첫 실행
저장소 → **Actions → "수집 및 사이트 배포" → Run workflow**. 2~3분 뒤 초록 체크가 뜨면
`https://<GitHub아이디>.github.io/market-pulse/` 에서 사이트가 열립니다. 이후 하루 3번 자동 갱신됩니다.

> 처음 업로드한 상태의 사이트는 **데모 데이터**(노란 배너)입니다. 첫 수집이 성공하면 실제 데이터로 바뀝니다.

---

## 추적 시장 바꾸기
`config/markets.yaml` 만 고치면 됩니다. 시장 추가·삭제, 주제어·검색어, 연관 키워드 시드, 쇼핑 분야, 유튜브/구글 매칭 단어를 모두 여기서 정합니다.

## 지표 읽는 법
- **기준지수**: 데이터랩은 요청마다 최댓값=100인 상대값만 줍니다. 모든 요청에 같은 기준 검색어(날씨)를 함께 넣고 그것으로 나눠, 시장끼리 비교할 수 있게 맞췄습니다. 절대 검색 횟수가 아닙니다.
- **30일 검색수**: 검색광고 키워드도구의 실제 검색수(PC+모바일)입니다. 10회 미만은 5회로 계산합니다.
- **신호**: 최근 28일 변화(없으면 3개월 모멘텀)와 전년비로 판정합니다. 급상승 = 28일 +30% 이상 & 전년비 0 이상 / 하락 = 28일 -20% 이하 & 전년비 마이너스 / 둔화 = 28일 -10% 이하 / 상승 = 28일 +10% 이상 또는 전년비 +20% 이상 / 나머지 보합.
- **기회 키워드 전월비**: 매월 저장하는 키워드 스냅샷과 비교하므로 **설치 다음 달부터** 채워집니다.
- **유튜브 새로 뜨는 단어**: 일별 스냅샷이 2일 이상 쌓여야 비교됩니다.

## 로컬에서 미리 보기 (선택)
```bash
pip install -r requirements.txt
MP_DATA=/tmp/demo python collector/make_demo_data.py      # 가짜 데이터 생성
MP_DATA=/tmp/demo python collector/analyze.py             # site/data/summary.json 생성
python -m http.server 8000 -d site                        # http://localhost:8000
```
실제 키로 로컬 수집: 환경변수에 키를 넣고 `python collector/run_all.py`.

## 주의사항 (2026-11-17 기준)
- NAVER API HUB는 현재 한시 무료이며 유료 전환 시 사전 공지 예정입니다.
- 네이버 **검색 API**(블로그·뉴스 등)는 2026-09 개정 약관에서 용도가 제한되어 이 프로젝트에서는 쓰지 않습니다.
- 구글 트렌드 공식 API는 알파(승인제)라 쓰지 않았고, 공개 RSS만 사용합니다. 승인되면 `collector/`에 수집기를 추가하면 됩니다.
- 쿠팡·메타는 1차 범위에서 제외했습니다(쿠팡 파트너스 API는 승인·호출 제한, 메타 광고 라이브러리 API는 한국 상업 광고 미제공).
- 유튜브·구글 일별 스냅샷은 90일만 보관합니다.

## 폴더 구조
```
config/markets.yaml          추적 시장 설정
collector/naver_datalab.py   검색어 트렌드 + 쇼핑인사이트
collector/naver_searchad.py  키워드도구 (검색수·연관 키워드)
collector/youtube_trending.py 유튜브 인기 동영상
collector/google_trends_rss.py 구글 실시간 인기 검색어
collector/analyze.py         지표 계산 → site/data/summary.json
collector/run_all.py         전체 실행 (Actions가 호출)
site/                        대시보드 (index.html, app.js, style.css)
data/                        수집 원자료 + 히스토리 (자동 커밋)
.github/workflows/collect.yml 스케줄·배포
```
