"""오늘의 인사이트 후보 키워드 추출.

구글 실시간 인기 검색어(최근 2일) + 유튜브 인기 영상 제목·급증 단어 + 네이버 시장 신호를 모아
사업 관련 분야(쇼핑·디지털 자산·금융·마케팅·테크)로 분류하고 점수순으로 출력합니다.
최종 3개 선정과 글 작성은 사람(또는 Claude 예약 작업)이 합니다.

사용: python collector/insight_candidates.py  →  화면 출력 + data/insight_candidates.json
"""
from __future__ import annotations

import json
import re
from datetime import timedelta

from common import DATA, SITE_DATA, load_json, save_json, today_kst

CATEGORIES = {
    "쇼핑·유통": ["쇼핑", "세일", "할인", "블랙프라이데이", "쿠팡", "올리브영", "다이소", "무신사", "컬리", "이마트", "홈플러스",
               "백화점", "신제품", "언박싱", "가격", "구매", "배송", "직구", "테무", "알리", "브랜드", "편의점", "출시", "리콜",
               "품절", "예약", "사전예약", "굿즈", "팝업", "명품", "아울렛", "네이버플러스", "스토어"],
    "디지털 자산": ["비트코인", "코인", "이더리움", "리플", "솔라나", "업비트", "빗썸", "두나무", "코인원", "스테이블코인", "가상자산",
               "디지털 자산", "디지털자산", "토큰", "nft", "블록체인", "원화 스테이블", "거래소", "김치프리미엄"],
    "금융·투자": ["주식", "코스피", "코스닥", "환율", "금리", "기준금리", "은행", "증권", "대출", "etf", "배당", "연금", "보험",
               "카드", "실적", "상장", "ipo", "공모", "펀드", "투자", "부동산", "청약", "세금", "최저임금", "사모펀드", "인수",
               "합병", "m&a", "파트너스", "캐피탈", "금융", "주가", "나스닥", "달러", "엔화", "금값", "유가"],
    "마케팅·미디어": ["광고", "마케팅", "캠페인", "인플루언서", "챌린지", "바이럴", "콜라보", "브랜딩", "숏폼", "유튜버", "틱톡",
                "인스타", "광고모델", "앰배서더", "cf", "흥행", "관객", "시청률", "ott", "넷플릭스", "티빙", "쿠팡플레이"],
    "테크·AI": ["ai", "인공지능", "챗gpt", "gpt", "제미나이", "클로드", "엔비디아", "반도체", "hbm", "아이폰", "갤럭시", "앱",
              "게임", "출시일", "gta", "업데이트", "로봇", "자율주행", "전기차", "테슬라", "데이터센터"],
}


def _hit(w: str, t: str) -> bool:
    # 영문 단어(ai, cf, etf 등)는 단어 경계로만 매칭 — "Wai" 같은 오탐 방지
    if w.isascii():
        return re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) is not None
    return w in t


def classify(text: str) -> list[str]:
    t = text.lower()
    return [c for c, ws in CATEGORIES.items() if any(_hit(w, t) for w in ws)]


def main():
    today = today_kst()
    items = []

    # 1) 구글 실시간 인기 검색어 (오늘 + 어제)
    for back in (0, 1):
        d = (today - timedelta(days=back)).isoformat()
        g = load_json(DATA / "history" / "google" / f"{d}.json")
        if not g:
            continue
        for q, it in g["items"].items():
            news = " ".join(n.get("title") or "" for n in it.get("news", []))
            cats = classify(q + " " + news)
            score = (len(cats) > 0) * 50 + min(it["traffic"], 100000) ** 0.5 / 10 + (10 if back == 0 else 0)
            items.append({"source": "구글 급상승", "date": d, "keyword": q, "traffic": it["traffic_label"],
                          "categories": cats, "score": round(score, 1), "news": it.get("news", [])[:3]})

    # 2) 유튜브: 사업 분야에 걸리는 인기 영상 + 급증 단어
    summary = load_json(SITE_DATA / "summary.json", {})
    yt = summary.get("youtube") or {}
    for v in yt.get("top", []):
        cats = classify(v["title"])
        if cats:
            items.append({"source": "유튜브 인기", "keyword": v["title"], "channel": v["channel"], "views": v["views"],
                          "categories": cats, "score": round(30 + (v["views"] ** 0.5) / 100, 1),
                          "url": f"https://www.youtube.com/watch?v={v['id']}"})
    for r in yt.get("rising", []):
        cats = classify(r["term"])
        items.append({"source": "유튜브 급증 단어", "keyword": r["term"], "count": r["today"], "base": r["base"],
                      "categories": cats, "score": round((40 if cats else 5) + r["today"] - r["base"], 1)})

    # 3) 네이버 시장 신호 (참고용)
    signals = [{"market": m["name"], "signal": m["total"]["signal"], "yoy": m["total"]["yoy"], "d28": m["total"]["d28"]}
               for m in summary.get("markets", [])]

    items.sort(key=lambda x: -x["score"])
    out = {"date": today.isoformat(), "candidates": items[:40], "naver_signals": signals}
    save_json(DATA / "insight_candidates.json", out)

    print(f"=== {today} 인사이트 후보 (사업 분야 우선, 점수순) ===")
    for i, c in enumerate(items[:30], 1):
        extra = c.get("traffic") or c.get("views") or c.get("count")
        news = c["news"][0]["title"] if c.get("news") else c.get("channel", "")
        print(f"{i:>2}. [{c['score']:>5}] {c['source']} | {c['keyword']} | {extra} | {','.join(c['categories']) or '-'} | {news}")
    print("\n네이버 시장 신호:", json.dumps(signals, ensure_ascii=False))


if __name__ == "__main__":
    main()
