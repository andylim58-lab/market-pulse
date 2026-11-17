"""구글 트렌드 '실시간 인기'(한국) RSS 수집. API 키 불필요.

하루에 여러 번 돌아도 같은 날짜 파일에 검색어 단위로 합쳐 저장합니다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from common import DATA, http, load_json, now_kst_str, save_json, today_kst

URL = "https://trends.google.com/trending/rss?geo=KR"
NS = {"ht": "https://trends.google.com/trending/rss"}


def _traffic(s: str) -> int:
    s = (s or "").replace(",", "").replace("+", "").strip().upper()
    mult = 1000 if s.endswith("K") else 1_000_000 if s.endswith("M") else 1
    try:
        return int(float(s.rstrip("KM")) * mult)
    except ValueError:
        return 0


def fetch() -> list[dict]:
    xml = http("GET", URL, headers={"User-Agent": "Mozilla/5.0 market-pulse"}).text
    root = ET.fromstring(xml)
    items = []
    for it in root.iter("item"):
        def t(tag):
            el = it.find(tag, NS) if ":" in tag else it.find(tag)
            return el.text if el is not None else ""
        news = []
        for n in it.findall("ht:news_item", NS):
            g = lambda tag: (n.find(tag, NS).text if n.find(tag, NS) is not None else "")
            news.append({"title": g("ht:news_item_title"), "url": g("ht:news_item_url"), "source": g("ht:news_item_source")})
        items.append({"q": t("title"), "traffic": _traffic(t("ht:approx_traffic")), "traffic_label": t("ht:approx_traffic"),
                      "pub": t("pubDate"), "news": news[:3]})
    return items


def main():
    path = DATA / "history" / "google" / f"{today_kst().isoformat()}.json"
    day = load_json(path, {"items": {}})
    for it in fetch():
        prev = day["items"].get(it["q"])
        if not prev or it["traffic"] >= prev["traffic"]:
            day["items"][it["q"]] = it
    day["updated"] = now_kst_str()
    save_json(path, day)
    print(f"  구글 급상승 ✓ (오늘 누적 {len(day['items'])}개)")


if __name__ == "__main__":
    main()
