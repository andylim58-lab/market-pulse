"""API 키 없이 사이트를 미리 보기 위한 '가짜' 원자료 생성기.
사용: MP_DATA=/tmp/demo python collector/make_demo_data.py && MP_DATA=/tmp/demo python collector/analyze.py
※ 생성된 숫자는 모두 임의값이며 실제 시장 데이터가 아닙니다.
"""
import math
import random
from datetime import datetime, timedelta, timezone

from common import DATA, load_config, now_kst_str, save_json, today_kst

random.seed(7)


def series(start, n, step, base, trend, season, noise):
    out, d = {}, start
    for i in range(n):
        m = d.month
        v = base * (1 + trend * i / n) * (1 + season * math.sin((m - 3) / 12 * 2 * math.pi)) * random.uniform(1 - noise, 1 + noise)
        out[d.isoformat()] = round(max(v, 0.01), 3)
        d = step(d)
    return out


def add_month(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def main():
    cfg = load_config()
    today = today_kst()
    m0 = (today.replace(day=1) - timedelta(days=365 * 3)).replace(day=1)
    d0 = today - timedelta(days=120)
    trend = {}
    for m in cfg["markets"]:
        trend[m["id"]] = {"month": {}, "date": {}}
        for g in m["groups"]:
            base, tr, se = random.uniform(3, 60), random.uniform(-0.4, 1.6), random.uniform(0, 0.35)
            trend[m["id"]]["month"][g["name"]] = series(m0, 37, add_month, base, tr, se, 0.08)
            boost = random.choice([1, 1, 1.4, 0.8])
            dd = series(d0, 120, lambda d: d + timedelta(days=1), base / 30, tr * 0.2, se, 0.15)
            keys = sorted(dd)
            for k in keys[-28:]:
                dd[k] = round(dd[k] * boost, 3)
            trend[m["id"]]["date"][g["name"]] = dd
    save_json(DATA / "naver" / "search_trend.json", {"updated": now_kst_str(), "markets": trend})

    shop_tr, demo = {}, {}
    anc = cfg["shopping_anchor"]["name"]
    for c in cfg["shopping_categories"]:
        shop_tr[c["name"]] = None if c["name"] == anc else series(m0, 37, add_month, random.uniform(20, 160), random.uniform(-0.2, 0.6), random.uniform(0, 0.3), 0.06)
        def dist(keys):
            w = [random.uniform(5, 30) for _ in keys]
            s = sum(w)
            return {k: round(x / s * 100, 1) for k, x in zip(keys, w)}
        ages = ["10", "20", "30", "40", "50", "60"]
        demo[c["name"]] = {"age": {"recent": dist(ages), "prev": dist(ages)}, "gender": {"recent": dist(["f", "m"]), "prev": dist(["f", "m"])}}
    save_json(DATA / "naver" / "shopping.json", {"updated": now_kst_str(), "trend": shop_tr, "demo": demo,
                                                  "demo_period": {"recent": ["2026-08-01", "2026-10-31"], "prev": ["2025-08-01", "2025-10-31"]}})

    suffix = ["추천", "가격", "비교", "후기", "순위", "방법", "할인", "사이트", "업체", "2026", "브랜드", "종류", "효과", "구매", "무료"]
    kw_out, kw_prev = {}, {}
    for m in cfg["markets"]:
        rel = []
        for s in m["seeds"]:
            for suf in [""] + random.sample(suffix, 9):
                vol = int(10 ** random.uniform(2.5, 5.3))
                rel.append({"kw": s + suf, "pc": vol // 4, "mo": vol - vol // 4, "vol": vol,
                            "comp": random.choice(["낮음", "중간", "높음"]), "depth": random.randint(5, 15), "clk": round(vol * 0.01, 1)})
        groups = {g["name"]: {"vol": int(10 ** random.uniform(3.5, 5.6)), "detail": []} for g in m["groups"]}
        kw_out[m["id"]] = {"groups": groups, "related": sorted(rel, key=lambda r: -r["vol"])}
        kw_prev[m["id"]] = {"groups": groups, "related": [{**r, "vol": int(r["vol"] * random.uniform(0.6, 1.3))} for r in rel]}
    save_json(DATA / "naver" / "keywords.json", {"updated": now_kst_str(), "markets": kw_out})
    prev_month = (today.replace(day=1) - timedelta(days=1))
    save_json(DATA / "history" / "keywords" / f"{prev_month:%Y-%m}.json", {"updated": "demo", "markets": kw_prev})

    titles = ["골프 드라이버 비거리 늘리는 법", "일본 후쿠오카 여행 브이로그", "챗GPT 신기능 총정리", "AI 영상 만들기 클로드 활용",
              "가을 패딩 하울 신상", "유산균 고르는 법 약사가 알려줌", "수능 국어 공부법", "올리브영 세일 추천템",
              "캠핑 장비 리뷰", "제주 맛집 투어", "스크린골프 스윙 교정", "마라톤 러닝화 비교", "갤럭시 신제품 언박싱",
              "프로야구 하이라이트", "아이돌 컴백 무대", "먹방 라면", "게임 신작 플레이", "뉴스 속보 정리", "코미디 콩트",
              "강아지 일상", "다이어트 단백질 레시피", "영어회화 기초", "테크 뉴스 AI 에이전트", "광고 마케팅 트렌드 2026"]
    cats = ["17", "19", "28", "28", "26", "26", "27", "26", "19", "19", "17", "17", "28", "17", "10", "22", "20", "25", "23", "15", "26", "27", "28", "22"]
    now = datetime.now(timezone.utc)
    for back in range(7, -1, -1):
        d = today - timedelta(days=back)
        charts = {}
        for c in ["0", "10", "17", "20", "22", "24", "26", "28"]:
            vids = []
            for r in range(1, 31):
                i = random.randrange(len(titles))
                pub = now - timedelta(hours=random.uniform(5, 200))
                vids.append({"id": f"v{back}{c}{r}{i}", "rank": r, "title": titles[i] + f" #{random.randint(1, 99)}", "channel": f"채널{i}",
                             "cat": cats[i] if c == "0" else c, "published": pub.isoformat().replace("+00:00", "Z"),
                             "tags": titles[i].split()[:3], "views": int(10 ** random.uniform(4.5, 6.8)),
                             "likes": random.randint(100, 50000), "comments": random.randint(10, 5000), "duration": "PT8M"})
            charts[c] = vids
        save_json(DATA / "history" / "youtube" / f"{d.isoformat()}.json", {"updated": now_kst_str(), "categories": {}, "charts": charts})

    qs = ["골프존 대회", "후쿠오카 날씨", "챗GPT 장애", "수능 등급컷", "유산균 리콜", "항공권 특가", "제미나이 3", "프로야구 시리즈",
          "블랙프라이데이", "올리브영 세일", "AI 광고 규제", "캠핑장 예약", "환율", "주식", "날씨", "로또"]
    for back in range(6, -1, -1):
        d = today - timedelta(days=back)
        items = {}
        for q in random.sample(qs, 9):
            t = random.choice([200, 500, 1000, 2000, 5000, 10000, 20000, 50000])
            items[q] = {"q": q, "traffic": t, "traffic_label": f"{t:,}+", "pub": "", "news": [{"title": f"{q} 관련 기사", "url": "https://example.com", "source": "데모뉴스"}]}
        save_json(DATA / "history" / "google" / f"{d.isoformat()}.json", {"updated": now_kst_str(), "items": items})
    save_json(DATA / "DEMO", True)
    print("데모 원자료 생성 완료:", DATA)


if __name__ == "__main__":
    main()
