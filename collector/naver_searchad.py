"""네이버 검색광고 키워드도구 (GET /keywordstool) 수집.

시장마다 (1) 시드 키워드의 연관 키워드 상위 200개, (2) 주제어에 속한 검색어의 실제 월간 검색수.
월별 스냅샷을 남겨 다음 달부터 '검색수 증감'을 계산할 수 있게 합니다.

환경변수: NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from common import DATA, env, http, load_config, norm_kw, now_kst_str, save_json, today_kst

BASE = "https://api.searchad.naver.com"


def _num(v) -> int:
    # 검색수가 매우 적으면 "< 10" 문자열로 옴 → 5로 간주
    if isinstance(v, (int, float)):
        return int(v)
    return 5


def keywordstool(hints: list[str]) -> list[dict]:
    uri = "/keywordstool"
    ts = str(int(time.time() * 1000))
    msg = f"{ts}.GET.{uri}".encode()
    sig = base64.b64encode(hmac.new(env("NAVER_AD_SECRET_KEY").encode(), msg, hashlib.sha256).digest()).decode()
    headers = {"X-Timestamp": ts, "X-API-KEY": env("NAVER_AD_ACCESS_LICENSE"),
               "X-Customer": env("NAVER_AD_CUSTOMER_ID"), "X-Signature": sig}
    params = {"hintKeywords": ",".join("".join(h.split()) for h in hints[:5]), "showDetail": "1"}
    r = http("GET", BASE + uri, headers=headers, params=params)
    time.sleep(0.4)  # 과호출 방지
    rows = []
    for k in r.json().get("keywordList", []):
        pc, mo = _num(k.get("monthlyPcQcCnt")), _num(k.get("monthlyMobileQcCnt"))
        rows.append({"kw": k["relKeyword"], "pc": pc, "mo": mo, "vol": pc + mo,
                     "comp": k.get("compIdx", ""), "depth": k.get("plAvgDepth", 0),
                     "clk": round(float(k.get("monthlyAvePcClkCnt") or 0) + float(k.get("monthlyAveMobileClkCnt") or 0), 1)})
    return rows


def main():
    if not env("NAVER_AD_CUSTOMER_ID"):
        print("NAVER_AD_CUSTOMER_ID 없음 → 검색광고 건너뜀")
        return
    cfg = load_config()
    out = {}
    for m in cfg["markets"]:
        related = {}
        for row in keywordstool(m["seeds"]):
            related[norm_kw(row["kw"])] = row
        # 주제어 검색어들의 실제 검색수 (5개씩 나눠 조회, 응답에 힌트 자신도 포함됨)
        group_kws = [k for g in m["groups"] for k in g["keywords"]]
        exact = {}
        for i in range(0, len(group_kws), 5):
            for row in keywordstool(group_kws[i:i + 5]):
                exact.setdefault(norm_kw(row["kw"]), row)
        groups = {}
        for g in m["groups"]:
            hits = [exact.get(norm_kw(k)) for k in g["keywords"]]
            # "CTV광고"와 "CTV 광고"처럼 띄어쓰기만 다른 검색어는 같은 키워드로 집계되므로 중복 합산 방지
            uniq = {norm_kw(h["kw"]): h["vol"] for h in hits if h}
            groups[g["name"]] = {"vol": sum(uniq.values()),
                                 "detail": [{"kw": k, "vol": h["vol"] if h else None} for k, h in zip(g["keywords"], hits)]}
        top = sorted(related.values(), key=lambda r: -r["vol"])[:200]
        out[m["id"]] = {"groups": groups, "related": top}
        print(f"  검색광고 {m['name']} ✓ (연관 {len(related)}개)")
    snap = {"updated": now_kst_str(), "markets": out}
    save_json(DATA / "naver" / "keywords.json", snap)
    save_json(DATA / "history" / "keywords" / f"{today_kst():%Y-%m}.json", snap)  # 월별 스냅샷(월 내 덮어씀)


if __name__ == "__main__":
    main()
