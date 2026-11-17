"""전체 수집 → 분석. 한 소스가 실패해도 나머지는 계속 진행합니다."""
import sys
import traceback

import analyze
import crypto_news
import google_trends_rss
import naver_datalab
import naver_searchad
import youtube_trending

STEPS = [("네이버 데이터랩", naver_datalab.main), ("네이버 검색광고", naver_searchad.main),
         ("유튜브", youtube_trending.main), ("구글 급상승", google_trends_rss.main),
         ("코인 뉴스·시세", crypto_news.main)]


def prune(days=90):
    """유튜브·구글 일별 스냅샷은 90일만 보관 (저장소 용량 관리)."""
    from datetime import timedelta
    from common import DATA, today_kst
    cutoff = (today_kst() - timedelta(days=days)).isoformat()
    for kind in ("youtube", "google", "crypto"):
        d = DATA / "history" / kind
        for f in d.glob("*.json") if d.exists() else []:
            if f.stem < cutoff:
                f.unlink()


def main():
    prune()
    failed = []
    for name, fn in STEPS:
        print(f"▶ {name}")
        try:
            fn()
        except Exception:
            traceback.print_exc()
            failed.append(name)
    print("▶ 분석")
    analyze.main()
    if failed:
        print(f"⚠ 실패한 소스: {', '.join(failed)} (이전 데이터로 사이트 생성)")
    # 모든 소스가 실패하면 워크플로우를 실패로 표시해 알림을 받게 함
    sys.exit(1 if len(failed) == len(STEPS) else 0)


if __name__ == "__main__":
    main()
