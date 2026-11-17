"""유튜브 한국 인기 동영상 수집 (YouTube Data API v3, videos.list chart=mostPopular).

전체 + 카테고리별 인기 영상을 매일 스냅샷으로 저장. 호출당 1유닛이라 하루 20유닛 내외.
환경변수: YOUTUBE_API_KEY
"""
from __future__ import annotations

from common import DATA, env, http, now_kst_str, save_json, today_kst

API = "https://www.googleapis.com/youtube/v3"
# 한국에서 인기 차트가 제공되는 주요 카테고리
CATEGORIES = {"0": "전체", "1": "영화/애니", "2": "자동차", "10": "음악", "15": "동물", "17": "스포츠",
              "20": "게임", "22": "인물/블로그", "23": "코미디", "24": "엔터테인먼트", "25": "뉴스/정치",
              "26": "노하우/스타일", "27": "교육", "28": "과학기술"}


def popular(key: str, cat: str) -> list[dict]:
    params = {"part": "snippet,statistics,contentDetails", "chart": "mostPopular", "regionCode": "KR",
              "hl": "ko", "maxResults": 50, "key": key}
    if cat != "0":
        params["videoCategoryId"] = cat
    try:
        items = http("GET", f"{API}/videos", params=params).json().get("items", [])
    except RuntimeError as e:  # 일부 카테고리는 차트 미제공(404)
        print(f"  카테고리 {cat} 건너뜀: {str(e)[:80]}")
        return []
    out = []
    for rank, it in enumerate(items, 1):
        sn, st = it["snippet"], it.get("statistics", {})
        out.append({"id": it["id"], "rank": rank, "title": sn["title"], "channel": sn["channelTitle"],
                    "cat": sn.get("categoryId"), "published": sn["publishedAt"],
                    "tags": (sn.get("tags") or [])[:15], "views": int(st.get("viewCount", 0)),
                    "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0)),
                    "duration": it.get("contentDetails", {}).get("duration", "")})
    return out


def main():
    key = env("YOUTUBE_API_KEY")
    if not key:
        print("YOUTUBE_API_KEY 없음 → 유튜브 건너뜀")
        return
    snap = {"updated": now_kst_str(), "categories": CATEGORIES,
            "charts": {c: popular(key, c) for c in CATEGORIES}}
    save_json(DATA / "history" / "youtube" / f"{today_kst().isoformat()}.json", snap)
    print(f"  유튜브 ✓ ({sum(len(v) for v in snap['charts'].values())}개)")


if __name__ == "__main__":
    main()
