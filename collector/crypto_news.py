"""코인 뉴스·시세 수집.

1) 뉴스: 코인마켓캡 뉴스 페이지가 모아 보여주는 주요 매체의 공식 RSS를 수집합니다.
   여러 매체가 동시에 다룬 기사일수록 '보도 강도' 점수가 높아집니다(Top 5 선정 참고용).
2) 시세: 코인마켓캡 무료(Basic) API — 전체 시가총액·BTC 점유율, 공포·탐욕 지수, 시가총액 Top 10.
   환경변수 CMC_API_KEY 가 없으면 시세는 건너뜁니다.
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from common import DATA, KST, SITE_DATA, env, http, load_json, now_kst_str, save_json, today_kst

FEEDS = [
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("CryptoPotato", "https://cryptopotato.com/feed/"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/.rss/full/"),
    ("블록미디어", "https://www.blockmedia.co.kr/feed"),
]
UA = {"User-Agent": "Mozilla/5.0 (market-pulse personal dashboard; RSS reader)"}
STOP = set("""the a an of to in on for and or is are as at by with from after over into its it this that be will
has have new says say said why how what price prediction today analysis news update week could can may amid
crypto cryptocurrency market markets report""".split())
TICKERS = ["BTC", "ETH", "XRP", "SOL", "BNB", "DOGE", "ADA", "TRX", "ZEC", "HYPE", "USDT", "USDC", "LINK", "AVAX", "SUI", "TON"]
NAMES = {"bitcoin": "BTC", "ethereum": "ETH", "ether": "ETH", "solana": "SOL", "ripple": "XRP", "dogecoin": "DOGE",
         "cardano": "ADA", "zcash": "ZEC", "tether": "USDT", "hyperliquid": "HYPE", "비트코인": "BTC", "이더리움": "ETH", "리플": "XRP", "솔라나": "SOL"}


def _text(el, tag, ns=None):
    x = el.find(tag, ns) if ns else el.find(tag)
    return (x.text or "").strip() if x is not None and x.text else ""


def _clean(s: str, n=320) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def _date(s: str):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None


def fetch_feed(name, url):
    xml = http("GET", url, headers=UA, timeout=20).content
    root = ET.fromstring(xml)
    out = []
    atom = "{http://www.w3.org/2005/Atom}"
    items = root.iter("item") if root.find(".//item") is not None else root.iter(f"{atom}entry")
    for it in items:
        title = _clean(_text(it, "title") or _text(it, f"{atom}title"), 200)
        link = _text(it, "link")
        if not link:
            le = it.find(f"{atom}link")
            link = le.get("href") if le is not None else ""
        pub = _date(_text(it, "pubDate") or _text(it, f"{atom}published") or _text(it, f"{atom}updated"))
        desc = _clean(_text(it, "description") or _text(it, f"{atom}summary"))
        if title and link:
            out.append({"source": name, "title": title, "url": link, "summary": desc,
                        "published": pub.isoformat() if pub else None})
    return out


def coins_of(text: str) -> list[str]:
    found = {t for t in TICKERS if re.search(rf"(?<![A-Z]){t}(?![A-Z])", text)}
    low = text.lower()
    found |= {v for k, v in NAMES.items() if k in low}
    return sorted(found)


def score(items):
    """다른 매체가 비슷한 제목으로 다룬 횟수 = 보도 강도."""
    toks = [{w for w in re.findall(r"[a-z0-9가-힣$]{3,}", i["title"].lower()) if w not in STOP} for i in items]
    for i, it in enumerate(items):
        peers = {items[j]["source"] for j in range(len(items))
                 if j != i and items[j]["source"] != it["source"] and len(toks[i] & toks[j]) >= 2}
        it["coverage"] = len(peers)
        it["coins"] = coins_of(it["title"] + " " + it["summary"])


def collect_news():
    now = datetime.now(timezone.utc)
    path = DATA / "history" / "crypto" / f"{today_kst().isoformat()}.json"
    day = load_json(path, {"items": {}})
    ok = []
    for name, url in FEEDS:
        try:
            for it in fetch_feed(name, url):
                if it["published"] and now - datetime.fromisoformat(it["published"]) > timedelta(hours=36):
                    continue
                day["items"].setdefault(it["url"], it)
            ok.append(name)
        except Exception as e:
            print(f"  {name} 건너뜀: {str(e)[:80]}")
    items = list(day["items"].values())
    score(items)
    day["items"] = {i["url"]: i for i in items}
    day["updated"] = now_kst_str()
    day["feeds_ok"] = ok
    save_json(path, day)
    # 사이트용 최신 헤드라인 40개 (원문 제목·링크만)
    latest = sorted(items, key=lambda i: i["published"] or "", reverse=True)[:40]
    save_json(SITE_DATA / "crypto_headlines.json", {"updated": day["updated"], "feeds": ok,
              "items": [{k: i[k] for k in ("source", "title", "url", "published", "coins", "coverage")} for i in latest]})
    print(f"  코인 뉴스 ✓ ({len(ok)}/{len(FEEDS)}개 매체, 오늘 누적 {len(items)}건)")
    return day


def collect_market():
    key = env("CMC_API_KEY")
    if not key:
        print("  CMC_API_KEY 없음 → 코인 시세 건너뜀")
        return None
    base = "https://pro-api.coinmarketcap.com"
    h = {"X-CMC_PRO_API_KEY": key, "Accept": "application/json"}
    out = {"updated": now_kst_str()}
    g = http("GET", f"{base}/v1/global-metrics/quotes/latest", headers=h).json()["data"]
    q = g["quote"]["USD"]
    out["global"] = {"total_mcap": q["total_market_cap"], "mcap_change_24h": q.get("total_market_cap_yesterday_percentage_change"),
                     "volume_24h": q["total_volume_24h"], "btc_dominance": g["btc_dominance"], "eth_dominance": g["eth_dominance"]}
    try:
        fg = http("GET", f"{base}/v3/fear-and-greed/latest", headers=h).json()["data"]
        out["fear_greed"] = {"value": fg["value"], "label": fg["value_classification"]}
    except RuntimeError as e:
        print(f"  공포·탐욕 지수 건너뜀: {str(e)[:80]}")
    lst = http("GET", f"{base}/v1/cryptocurrency/listings/latest", headers=h, params={"limit": 10, "convert": "USD"}).json()["data"]
    out["top"] = [{"rank": c["cmc_rank"], "name": c["name"], "symbol": c["symbol"], "slug": c["slug"],
                   "price": c["quote"]["USD"]["price"], "ch24": c["quote"]["USD"]["percent_change_24h"],
                   "ch7d": c["quote"]["USD"]["percent_change_7d"], "mcap": c["quote"]["USD"]["market_cap"]} for c in lst]
    save_json(SITE_DATA / "crypto_market.json", out)
    print("  코인 시세 ✓")
    return out


def candidates():
    """Top 5 선정용 후보: 최근 36시간, 보도 강도(여러 매체 동시 보도) → 최신순."""
    now = datetime.now(timezone.utc)
    items = {}
    for back in (0, 1):
        d = load_json(DATA / "history" / "crypto" / f"{(today_kst() - timedelta(days=back)).isoformat()}.json", {"items": {}})
        items.update(d["items"])
    rows = [i for i in items.values() if not i["published"] or now - datetime.fromisoformat(i["published"]) <= timedelta(hours=36)]
    score(rows)
    rows.sort(key=lambda i: (-i["coverage"], i["published"] or ""), reverse=False)
    rows.sort(key=lambda i: -i["coverage"])
    save_json(DATA / "crypto_candidates.json", {"date": today_kst().isoformat(), "items": rows[:60]})
    print(f"=== {today_kst()} 코인 뉴스 후보 (보도 강도순) ===")
    for n, i in enumerate(rows[:40], 1):
        t = datetime.fromisoformat(i["published"]).astimezone(KST).strftime("%m-%d %H:%M") if i["published"] else "-"
        print(f"{n:>2}. [{i['coverage']}] {t} {i['source']} | {i['title']} | {','.join(i['coins'])}\n     {i['url']}\n     {i['summary'][:160]}")
    m = load_json(SITE_DATA / "crypto_market.json")
    if m:
        print("\n시세:", {k: m[k] for k in ("global", "fear_greed") if k in m})


def main():
    collect_news()
    collect_market()


if __name__ == "__main__":
    import sys
    candidates() if sys.argv[1:] == ["candidates"] else main()
