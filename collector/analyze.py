"""수집된 원자료 → 사이트용 summary.json 생성 (지표 계산·신호 판정·교차 플랫폼 매칭)."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from common import DATA, SITE_DATA, load_config, load_json, norm_kw, now_kst_str, save_json, today_kst

YT_CAT_NAMES = {"1": "영화/애니", "2": "자동차", "10": "음악", "15": "동물", "17": "스포츠", "19": "여행/이벤트",
                "20": "게임", "22": "인물/블로그", "23": "코미디", "24": "엔터테인먼트", "25": "뉴스/정치",
                "26": "노하우/스타일", "27": "교육", "28": "과학기술", "29": "비영리/사회"}
STOP = set("""공식 영상 뮤직비디오 official mv m/v shorts short 쇼츠 오늘 진짜 이번 그냥 우리 하는 있는 없는 이런 저런
the and for with feat ft live full ver version teaser trailer 예고 예고편 티저 하이라이트 highlight 1화 2화 3화
ep episode 리뷰 브이로그 vlog 무대 직캠 풀버전 최초 공개 단독 반응 #shorts
of you love vs to in on my is it me we your this that at by from new news 뉴스 이유 방법 만든 최후 비밀 모든 가장 처음 진짜로 근황""".split())
TOKEN = re.compile(r"[가-힣A-Za-z][가-힣A-Za-z0-9]{1,}")


# ── 시계열 지표 ──────────────────────────────────────────────
def pct(a, b):
    return None if not b else round((a / b - 1) * 100, 1)


def month_metrics(series: dict[str, float]) -> dict:
    """월간 시리즈 → 전년동월비, 최근3개월 모멘텀 (진행 중인 이번 달 제외)."""
    cur_month = today_kst().replace(day=1).isoformat()
    pts = sorted((p, v) for p, v in series.items() if p < cur_month)
    if not pts:
        return {"yoy": None, "mom3": None, "last": None}
    last_p, last_v = pts[-1]
    d = datetime.fromisoformat(last_p)
    prev_year = d.replace(year=d.year - 1).date().isoformat()
    vals = [v for _, v in pts]
    mom3 = pct(sum(vals[-3:]) / 3, sum(vals[-6:-3]) / 3) if len(vals) >= 6 else None
    return {"yoy": pct(last_v, series.get(prev_year)), "mom3": mom3, "last": last_p}


def day_metrics(series: dict[str, float]) -> dict:
    vals = [v for _, v in sorted(series.items())]
    if len(vals) < 56:
        return {"d28": None}
    return {"d28": pct(sum(vals[-28:]), sum(vals[-56:-28]))}


def signal(yoy, d28, mom3=None):
    s = d28 if d28 is not None else mom3
    y = yoy if yoy is not None else 0
    if s is None:
        return "데이터 부족"
    if s >= 30 and y >= 0:
        return "급상승"
    if s <= -20 and y < 0:
        return "하락"
    if s <= -10:
        return "둔화"
    if s >= 10 or y >= 20:
        return "상승"
    return "보합"


def to_pairs(series: dict | None, keep_partial=True):
    if not series:
        return []
    return [[p, round(v, 3)] for p, v in sorted(series.items())]


# ── 매칭 ─────────────────────────────────────────────────────
def matcher(words):
    ws = [w.lower() for w in words]
    return lambda text: any(w in text.lower() for w in ws)


def history_files(kind: str, days: int):
    d = DATA / "history" / kind
    if not d.exists():
        return []
    files = sorted(d.glob("*.json"))
    cutoff = (today_kst() - timedelta(days=days)).isoformat()
    return [f for f in files if f.stem >= cutoff]


# ── 유튜브 ───────────────────────────────────────────────────
def tokens(v):
    text = v["title"] + " " + " ".join(v.get("tags", []))
    return {t.lower() for t in TOKEN.findall(text) if t.lower() not in STOP}


def analyze_youtube(markets):
    files = history_files("youtube", 8)
    if not files:
        return None, {}
    snaps = [(f.stem, load_json(f)) for f in files]
    date, latest = snaps[-1]
    uniq = {}
    for vids in latest["charts"].values():
        for v in vids:
            uniq.setdefault(v["id"], v)
    top = latest["charts"].get("0", [])
    now = datetime.now(timezone.utc)
    for v in uniq.values():
        hrs = max((now - datetime.fromisoformat(v["published"].replace("Z", "+00:00"))).total_seconds() / 3600, 1)
        v["vph"] = round(v["views"] / hrs)
    cat_share = Counter(YT_CAT_NAMES.get(v["cat"], "기타") for v in top)

    # 제목·태그 단어: 오늘 등장 영상 수 vs 지난 스냅샷 평균
    def term_counts(snap):
        c = Counter()
        seen = {}
        for vids in snap["charts"].values():
            for v in vids:
                seen.setdefault(v["id"], v)
        for v in seen.values():
            c.update(tokens(v))
        return c
    today_c = term_counts(latest)
    prev = [term_counts(s) for _, s in snaps[:-1]]
    rising = []
    for term, n in (today_c.items() if prev else []):  # 비교할 지난 스냅샷이 없으면 표시하지 않음
        base = sum(p.get(term, 0) for p in prev) / len(prev) if prev else 0
        if n >= 3 and n - base >= 2:
            rising.append({"term": term, "today": n, "base": round(base, 1), "new": base == 0})
    rising.sort(key=lambda r: (-(r["today"] - r["base"]), -r["today"]))

    hits = {}
    for m in markets:
        f = matcher(m["match"])
        vids = [v for v in uniq.values() if f(v["title"] + " " + " ".join(v.get("tags", [])))]
        daily = []
        for d, s in snaps:
            ids = {v["id"] for vs in s["charts"].values() for v in vs
                   if f(v["title"] + " " + " ".join(v.get("tags", [])))}
            daily.append([d, len(ids)])
        hits[m["id"]] = {"count": len(vids), "daily": daily,
                         "top": sorted(vids, key=lambda v: -v["views"])[:6]}
    slim = lambda v: {k: v[k] for k in ("id", "title", "channel", "cat", "views", "likes", "comments", "published", "vph", "rank") if k in v}
    for h in hits.values():
        h["top"] = [slim(v) for v in h["top"]]
    return {"date": date, "updated": latest.get("updated"), "top": [slim(uniq[v["id"]]) for v in top[:50]],
            "cat_share": cat_share.most_common(), "velocity": [slim(v) for v in sorted(uniq.values(), key=lambda v: -v["vph"])[:15]],
            "rising": rising[:30], "total_unique": len(uniq)}, hits


# ── 구글 급상승 ──────────────────────────────────────────────
def analyze_google(markets):
    files = history_files("google", 7)
    if not files:
        return None, {}
    days = [(f.stem, load_json(f)) for f in files]
    date, latest = days[-1]
    today = sorted(latest["items"].values(), key=lambda x: -x["traffic"])
    agg = {}
    for d, s in days:
        for q, it in s["items"].items():
            a = agg.setdefault(q, {"q": q, "days": [], "traffic": 0, "news": it.get("news", [])})
            a["days"].append(d)
            a["traffic"] = max(a["traffic"], it["traffic"])
    week = sorted(agg.values(), key=lambda x: (-len(x["days"]), -x["traffic"]))
    for w in week:
        w["n"] = len(w["days"])
        w["last"] = max(w["days"])
        del w["days"]
    hits = {}
    for m in markets:
        f = matcher(m["match"])
        hs = [w for w in week if f(w["q"] + " " + " ".join(n["title"] or "" for n in w["news"]))]
        hits[m["id"]] = {"count": len(hs), "items": hs[:8]}
    return {"date": date, "updated": latest.get("updated"), "today": today[:40], "week": week[:60]}, hits


# ── 키워드 기회 점수 ─────────────────────────────────────────
COMP_W = {"낮음": 1.0, "중간": 0.6, "높음": 0.25}


def prev_keyword_snapshot():
    d = DATA / "history" / "keywords"
    this_month = f"{today_kst():%Y-%m}"
    files = sorted(f for f in d.glob("*.json") if f.stem < this_month) if d.exists() else []
    return load_json(files[-1]) if files else None


def main():
    cfg = load_config()
    markets = cfg["markets"]
    trend = load_json(DATA / "naver" / "search_trend.json")
    shop = load_json(DATA / "naver" / "shopping.json")
    kws = load_json(DATA / "naver" / "keywords.json")
    prev_kws = prev_keyword_snapshot()
    yt, yt_hits = analyze_youtube(markets)
    gg, gg_hits = analyze_google(markets)

    prev_vol = {}
    if prev_kws:
        for mk in prev_kws["markets"].values():
            for r in mk["related"]:
                prev_vol[norm_kw(r["kw"])] = r["vol"]

    shop_metrics = {}
    shop_out = None
    if shop:
        cats = []
        for c in cfg["shopping_categories"]:
            s = shop["trend"].get(c["name"])
            if s is None:  # 기준 분야
                cats.append({"name": c["name"], "code": c["code"], "anchor": True, "monthly": [], "yoy": None, "mom3": None})
                continue
            mm = month_metrics(s)
            shop_metrics[c["code"]] = mm
            cats.append({"name": c["name"], "code": c["code"], "monthly": to_pairs(s), **mm})
        shop_out = {"updated": shop["updated"], "categories": cats, "demo": shop["demo"], "demo_period": shop["demo_period"]}

    out_markets, opps = [], []
    for m in markets:
        mid = m["id"]
        tm = (trend or {}).get("markets", {}).get(mid, {})
        km = (kws or {}).get("markets", {}).get(mid, {})
        groups = []
        tot_m, tot_d = defaultdict(float), defaultdict(float)
        for g in m["groups"]:
            ms, ds = tm.get("month", {}).get(g["name"], {}), tm.get("date", {}).get(g["name"], {})
            for p, v in ms.items():
                tot_m[p] += v
            for p, v in ds.items():
                tot_d[p] += v
            mm, dm = month_metrics(ms), day_metrics(ds)
            groups.append({"name": g["name"], "keywords": g["keywords"], "monthly": to_pairs(ms), "daily": to_pairs(ds),
                           "vol": km.get("groups", {}).get(g["name"], {}).get("vol"), **mm, **dm,
                           "signal": signal(mm["yoy"], dm["d28"], mm["mom3"])})
        mm, dm = month_metrics(tot_m), day_metrics(tot_d)
        related = []
        for r in km.get("related", []):
            pv = prev_vol.get(norm_kw(r["kw"]))
            g = pct(r["vol"], pv) if pv else None
            related.append({**r, "growth": g})
            if r["vol"] >= 1000:
                gw = max(min((g or 0) / 100, 2), -0.5)
                score = math.log10(r["vol"]) * COMP_W.get(r["comp"], 0.5) * (1 + gw)
                opps.append({"kw": r["kw"], "market": m["name"], "vol": r["vol"], "comp": r["comp"],
                             "growth": g, "clk": r.get("clk"), "score": round(score, 2)})
        out_markets.append({
            "id": mid, "name": m["name"], "groups": groups,
            "total": {"monthly": to_pairs(tot_m), "daily": to_pairs(tot_d), "vol": sum(g["vol"] or 0 for g in groups) or None,
                      **mm, **dm, "signal": signal(mm["yoy"], dm["d28"], mm["mom3"])},
            "shopping": [{"code": c, "name": next((x["name"] for x in cfg["shopping_categories"] if x["code"] == c), c),
                          **shop_metrics.get(c, {})} for c in m.get("categories", [])],
            "related": related[:100],
            "youtube": yt_hits.get(mid), "google": gg_hits.get(mid),
        })
    opps.sort(key=lambda o: -o["score"])

    summary = {
        "generated": now_kst_str(), "demo": bool(load_json(DATA / "DEMO", False)),
        "sources": {"naver_trend": (trend or {}).get("updated"), "naver_shopping": (shop or {}).get("updated"),
                    "naver_keywords": (kws or {}).get("updated"), "keywords_prev_month": bool(prev_kws),
                    "youtube": (yt or {}).get("updated"), "google": (gg or {}).get("updated")},
        "anchor": ", ".join(cfg["anchor"]["keywords"]), "markets": out_markets, "shopping": shop_out,
        "youtube": yt, "google": gg, "opportunities": opps[:80],
    }
    save_json(SITE_DATA / "summary.json", summary)
    print(f"  summary.json 생성 ✓ ({len(out_markets)}개 시장, 기회 키워드 {len(opps)}개)")


if __name__ == "__main__":
    main()
