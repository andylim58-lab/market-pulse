"""네이버 데이터랩 수집 (NAVER API HUB).

- 검색어 트렌드: 시장마다 [주제어 4개 + 기준 검색어] 를 한 번에 요청 → 기준 검색어로 나눠
  요청이 달라도 비교 가능한 '기준지수'로 환산 (기준 검색어 기간 평균 = 100).
- 쇼핑인사이트: 분야 2개 + 기준 분야를 함께 요청해 같은 방식으로 환산, 분야별 연령·성별 분포.

환경변수: NAVER_HUB_ID, NAVER_HUB_SECRET
(기존 개발자센터 키를 쓰려면 NAVER_LEGACY=1 → openapi.naver.com 경로 사용, 2027-06-30까지)
"""
from __future__ import annotations

from datetime import timedelta

from common import DATA, env, http, load_config, load_json, now_kst_str, save_json, today_kst

HUB = "https://naverapihub.apigw.ntruss.com"
LEGACY = "https://openapi.naver.com"


def _endpoints():
    if env("NAVER_LEGACY"):
        return {
            "trend": f"{LEGACY}/v1/datalab/search",
            "cats": f"{LEGACY}/v1/datalab/shopping/categories",
            "age": f"{LEGACY}/v1/datalab/shopping/category/age",
            "gender": f"{LEGACY}/v1/datalab/shopping/category/gender",
        }, {"X-Naver-Client-Id": env("NAVER_HUB_ID"), "X-Naver-Client-Secret": env("NAVER_HUB_SECRET")}
    return {
        "trend": f"{HUB}/search-trend/v1/search",
        "cats": f"{HUB}/shopping/v1/categories",
        "age": f"{HUB}/shopping/v1/category/age",
        "gender": f"{HUB}/shopping/v1/category/gender",
    }, {"X-NCP-APIGW-API-KEY-ID": env("NAVER_HUB_ID"), "X-NCP-APIGW-API-KEY": env("NAVER_HUB_SECRET")}


def _post(url, headers, body):
    return http("POST", url, headers={**headers, "Content-Type": "application/json"}, json=body).json()


def _anchor_scale(results: list[dict], anchor_title: str, keep_anchor=False) -> dict[str, dict[str, float]]:
    """응답 results → {주제어: {period: 기준지수}}. 기준 검색어 기간평균을 100으로 환산."""
    series = {r["title"]: {d["period"]: float(d["ratio"]) for d in r["data"]} for r in results}
    anchor = series.get(anchor_title) if keep_anchor else series.pop(anchor_title, None)
    if not anchor:
        return series
    base = sum(anchor.values()) / max(len(anchor), 1)
    if base <= 0:
        return series
    return {t: {p: round(v / base * 100, 4) for p, v in s.items()} for t, s in series.items()}


def collect_search_trend(cfg, urls, headers):
    today = today_kst()
    end = (today - timedelta(days=1)).isoformat()
    windows = {
        "month": ((today.replace(day=1) - timedelta(days=365 * 3)).replace(day=1).isoformat(), end),
        "date": ((today - timedelta(days=120)).isoformat(), end),
    }
    anchor = cfg["anchor"]
    out = {}
    for m in cfg["markets"]:
        groups = [{"groupName": g["name"], "keywords": g["keywords"][:20]} for g in m["groups"][:4]]
        groups.append({"groupName": anchor["name"], "keywords": anchor["keywords"]})
        out[m["id"]] = {}
        for unit, (s, e) in windows.items():
            res = _post(urls["trend"], headers, {"startDate": s, "endDate": e, "timeUnit": unit, "keywordGroups": groups})
            out[m["id"]][unit] = _anchor_scale(res["results"], anchor["name"])
        print(f"  검색어 트렌드 {m['name']} ✓")
    return out


def collect_shopping(cfg, urls, headers):
    today = today_kst()
    end = (today - timedelta(days=1)).isoformat()
    start = (today.replace(day=1) - timedelta(days=365 * 3)).replace(day=1).isoformat()
    anc = cfg["shopping_anchor"]
    cats = [c for c in cfg["shopping_categories"] if c["code"] != anc["code"]]
    trend = {}
    for i in range(0, len(cats), 2):
        chunk = cats[i:i + 2] + [anc]
        body = {"startDate": start, "endDate": end, "timeUnit": "month",
                "category": [{"name": c["name"], "param": [c["code"]]} for c in chunk]}
        res = _post(urls["cats"], headers, body)
        trend.update(_anchor_scale(res["results"], anc["name"], keep_anchor=True))

    # 분야별 연령·성별 분포: 최근 3개월 vs 1년 전 같은 3개월
    recent_s = (today.replace(day=1) - timedelta(days=92)).replace(day=1)
    recent_e = today.replace(day=1) - timedelta(days=1)
    prev_s = recent_s.replace(year=recent_s.year - 1)
    prev_e = recent_e.replace(year=recent_e.year - 1)
    demo = {}
    for c in cfg["shopping_categories"]:
        demo[c["name"]] = {}
        for kind in ("age", "gender"):
            body = {"startDate": prev_s.isoformat(), "endDate": recent_e.isoformat(), "timeUnit": "month", "category": c["code"]}
            res = _post(urls[kind], headers, body)
            rows = res["results"][0]["data"] if res.get("results") else []
            def share(s, e):
                agg = {}
                for d in rows:
                    if s.isoformat() <= d["period"] <= e.isoformat():
                        agg[d["group"]] = agg.get(d["group"], 0) + float(d["ratio"])
                tot = sum(agg.values()) or 1
                return {k: round(v / tot * 100, 1) for k, v in sorted(agg.items())}
            demo[c["name"]][kind] = {"recent": share(recent_s, recent_e), "prev": share(prev_s, prev_e)}
    print("  쇼핑인사이트 ✓")
    return {"trend": trend, "demo": demo,
            "demo_period": {"recent": [recent_s.isoformat(), recent_e.isoformat()], "prev": [prev_s.isoformat(), prev_e.isoformat()]}}


def main():
    if not env("NAVER_HUB_ID"):
        print("NAVER_HUB_ID 없음 → 데이터랩 건너뜀")
        return
    # 데이터랩은 하루 단위로 갱신되므로 하루 1회(그날 첫 실행 = 아침)만 호출. 강제 실행은 DATALAB_FORCE=1
    prev = load_json(DATA / "naver" / "search_trend.json", {})
    if not env("DATALAB_FORCE") and str(prev.get("updated", "")).startswith(today_kst().isoformat()):
        print("  데이터랩은 오늘 이미 수집함 → 건너뜀 (하루 1회)")
        return
    cfg = load_config()
    urls, headers = _endpoints()
    save_json(DATA / "naver" / "search_trend.json", {"updated": now_kst_str(), "markets": collect_search_trend(cfg, urls, headers)})
    save_json(DATA / "naver" / "shopping.json", {"updated": now_kst_str(), **collect_shopping(cfg, urls, headers)})


if __name__ == "__main__":
    main()
