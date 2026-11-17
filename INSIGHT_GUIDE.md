# 오늘의 인사이트 작성 가이드 (매일 예약 작업용)

매일 오전 9시대에 Claude 예약 작업이 이 문서를 읽고 그날의 인사이트 3건을 작성·게시합니다.

## 1. 후보 뽑기
```bash
git pull origin main
python collector/insight_candidates.py
```
- 출력은 구글 실시간 인기 검색어(오늘·어제), 유튜브 인기 영상·급증 단어, 네이버 시장 신호입니다.
- `data/insight_candidates.json` 에도 저장됩니다(뉴스 제목·URL 포함).

## 2. 키워드 3개 고르기
- **사업 관련 분야를 우선합니다.** 분야는 `쇼핑·유통`, `디지털 자산`, `금융·투자`, `마케팅·미디어`, `테크·AI` 중 하나로 지정합니다.
- **3개는 가능하면 서로 다른 분야**로 고릅니다.
- **제외합니다:** 정치 공방, 사건·사고, 범죄, 연예인 사생활, 부고, 스포츠 경기 결과. 단, 그 이슈가 기업·시장에 직접 영향을 줄 때는 예외입니다.
- **최근 7일 안에 다룬 키워드는 피합니다.** `site/insights/index.json` 을 확인합니다. 큰 진전이 있으면 예외입니다.
- 사업 관련 후보가 3개가 안 되면 유튜브 인기 영상과 네이버 시장 신호(급상승·반등)에서 보충합니다.

## 3. 조사
- 키워드마다 웹 검색을 3~5회 합니다. 이유·수치·업계 반응을 각각 따로 찾습니다.
- **모든 수치는 출처 기사에서 확인한 것만 씁니다.** 추정치는 "추정", "전망"으로 표시합니다.
- 출처는 2~6개 넣습니다. 후보 데이터에 들어 있는 뉴스 URL을 우선 활용합니다.
- **저작권:** 기사 문장을 그대로 옮기지 말고 모두 새로 써서 요약합니다. 직접 인용은 쓰지 않습니다.

## 4. 작성 (`site/insights/YYYY-MM-DD.json`)
형식은 `site/insights/2026-11-17.json` 을 그대로 따릅니다.

| 항목 | 내용 |
|---|---|
| keyword / slug | 키워드 원문, 영문 소문자-하이픈 슬러그 |
| category | 위 5개 분야 중 하나 |
| title | 쉼표 하나가 들어간 한 줄 헤드라인. 쉼표 앞부분이 강조색으로 표시됨 |
| lead | 왜 오늘 떴는지 1~2문장 |
| summary | 핵심 인사이트 2~3문장 |
| tags | 해시태그 4~6개 |
| signals.from | 어디서 포착했는지 (예: "구글 급상승 (11/17, 200+)") |
| kpis | 출처가 있는 수치 2~4개. 각 항목에 label, value, unit, note, tone(teal/orange/blue/violet) |
| phenomenon | 현상: 무슨 일이 있나. title + points 2~5개 |
| cause | 원인: 왜 지금인가. title + points 2~5개 |
| implication | 시사점: 사업 관점. title + points 2~5개. 광고·마케팅·커머스·영업 관점의 구체적 기회와 위험 |
| watch | 앞으로 볼 지표 1~4개 |
| sources | title, publisher, url |

문체는 "~어요/~예요/~입니다"를 섞은 부드러운 존댓말로 씁니다. 과장과 단정을 피합니다.

## 5. 검증·게시
```bash
python collector/insight_publish.py site/insights/YYYY-MM-DD.json   # 실패하면 지적된 항목 고쳐서 재실행
git add site/insights && git commit -m "insight: YYYY-MM-DD" && git push origin main
```
push하면 "인사이트 게시" 워크플로우가 2분 안에 사이트에 반영합니다.


---

# 코인 뉴스 Top 5 작성 가이드 (같은 예약 작업에서 이어서 진행)

## 1. 후보 보기
```bash
python collector/crypto_news.py candidates
```
- 코인마켓캡 뉴스 페이지에 모이는 주요 매체(Cointelegraph·CoinDesk·Decrypt·The Block·CryptoPotato·Bitcoin Magazine·코인마켓캡 Academy·블록미디어)의 최근 36시간 기사가 출력됩니다.
- 앞의 [숫자]는 **보도 강도**입니다. 다른 매체가 비슷한 제목으로 함께 다룬 수라서, 높을수록 시장 전체가 주목한 뉴스입니다.
- 시세(시가총액·BTC 점유율·공포탐욕 지수)도 함께 출력됩니다. 시세가 없으면 `site/data/crypto_market.json`이 없는 것이니 그대로 진행합니다.
- 필요하면 WebFetch/WebSearch로 원문과 코인마켓캡 뉴스(https://coinmarketcap.com/headlines/news/)를 확인해 보강합니다.

## 2. 5건 고르기
- **우선순위:**
  1. 시장 전체를 움직인 뉴스(가격 급변, 거시경제, ETF·기관 자금)
  2. 규제·정책
  3. 대형 기업·금융사의 사업 발표
  4. 보안 사고
  5. 국내 거래소·제도 이슈
- **빼는 것:** 단순 가격 예측 글, 인플루언서 발언, 보도자료성 소규모 프로젝트 기사
- 같은 사건은 하나로 묶고, 보도 강도가 높은 기사를 우선합니다.

## 3. 작성 (`site/crypto/YYYY-MM-DD.json`)
형식은 `site/crypto/2026-11-17.json`을 그대로 따릅니다.

| 항목 | 내용 |
|---|---|
| market_note | 오늘 시장 한 줄. 가격·공포탐욕 지수 등 확인한 수치만 씀 |
| rank | 1~5 |
| title_ko | 한국어 제목 (새로 씀) |
| title_en | 원문 제목 |
| summary | 2문장 한국어 요약. 원문 문장을 옮기지 말고 새로 씀 |
| why | 왜 중요한가 1문장. 사업·마케팅·투자 관점 |
| coins | 관련 코인 티커 |
| source / url / published | 원문 출처, 링크, 발행 시각 |
| coverage | 후보 출력의 보도 강도 숫자 |
| cmc_url | 관련 코인의 코인마켓캡 페이지 (예: https://coinmarketcap.com/currencies/bitcoin/), 없으면 "" |

## 4. 검증·게시
```bash
python collector/crypto_publish.py site/crypto/YYYY-MM-DD.json
git add site/crypto && git commit -m "crypto top5: YYYY-MM-DD" && git push origin main
```
