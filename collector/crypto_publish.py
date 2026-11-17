"""코인 Top 5 JSON 검증 + 목록(index.json) 갱신.
사용: python collector/crypto_publish.py site/crypto/2026-11-17.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "crypto"


def check(doc):
    err = []
    items = doc.get("items") or []
    if len(items) != 5:
        err.append(f"items 는 정확히 5개 (현재 {len(items)})")
    for n, it in enumerate(items, 1):
        p = f"items[{n}]"
        if it.get("rank") != n:
            err.append(f"{p}.rank 는 {n}")
        for k in ("title_ko", "title_en", "why", "source", "url"):
            if not it.get(k):
                err.append(f"{p}.{k} 없음")
        if not str(it.get("url", "")).startswith("http"):
            err.append(f"{p}.url 은 http 로 시작")
        if not (2 <= len(it.get("summary", [])) <= 3):
            err.append(f"{p}.summary 2~3문장")
        if not isinstance(it.get("coins", []), list):
            err.append(f"{p}.coins 는 목록")
    if not doc.get("market_note"):
        err.append("market_note (오늘 시장 한 줄) 없음")
    return err


def main():
    path = Path(sys.argv[1])
    doc = json.loads(path.read_text(encoding="utf-8"))
    errs = check(doc)
    if errs:
        print("검증 실패:\n" + "\n".join(" - " + e for e in errs))
        sys.exit(1)
    idx_p = OUT / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {"days": []}
    entry = {"date": doc["date"], "top": [i["title_ko"] for i in doc["items"]]}
    idx["days"] = sorted([d for d in idx["days"] if d["date"] != doc["date"]] + [entry], key=lambda d: d["date"], reverse=True)
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"검증 통과 ✓ — index.json 갱신 ({len(idx['days'])}일치)")


if __name__ == "__main__":
    main()
