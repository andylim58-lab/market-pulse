"""인사이트 JSON 검증 + 목록(index.json) 갱신.

사용: python collector/insight_publish.py site/insights/2026-11-17.json
- 필수 항목·개수·글자 수를 검사하고, 문제가 있으면 무엇이 틀렸는지 출력하고 실패(exit 1)합니다.
- 통과하면 site/insights/index.json 에 그날 항목을 추가/갱신합니다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INS = ROOT / "site" / "insights"
CATS = {"쇼핑·유통", "디지털 자산", "금융·투자", "마케팅·미디어", "테크·AI"}
TONES = {"teal", "orange", "blue", "violet"}


def check(doc: dict) -> list[str]:
    err = []
    if not isinstance(doc.get("date"), str) or len(doc["date"]) != 10:
        err.append("date 는 YYYY-MM-DD")
    items = doc.get("items") or []
    if len(items) != 3:
        err.append(f"items 는 정확히 3개여야 함 (현재 {len(items)})")
    for i, it in enumerate(items, 1):
        p = f"items[{i}]"
        for k in ("keyword", "slug", "category", "title", "lead"):
            if not it.get(k):
                err.append(f"{p}.{k} 없음")
        if it.get("category") not in CATS:
            err.append(f"{p}.category 는 {sorted(CATS)} 중 하나")
        if not (2 <= len(it.get("summary", [])) <= 3):
            err.append(f"{p}.summary 2~3문장")
        if not (2 <= len(it.get("tags", [])) <= 8):
            err.append(f"{p}.tags 2~8개")
        kp = it.get("kpis", [])
        if not (2 <= len(kp) <= 4):
            err.append(f"{p}.kpis 2~4개")
        for j, k in enumerate(kp):
            if not k.get("label") or not k.get("value"):
                err.append(f"{p}.kpis[{j}] label/value 필요")
            if k.get("tone") and k["tone"] not in TONES:
                err.append(f"{p}.kpis[{j}].tone 은 {sorted(TONES)}")
        for sec in ("phenomenon", "cause", "implication"):
            s = it.get(sec) or {}
            if not s.get("title") or not (2 <= len(s.get("points", [])) <= 5):
                err.append(f"{p}.{sec} 에 title 과 points 2~5개 필요")
        if not (1 <= len(it.get("watch", [])) <= 4):
            err.append(f"{p}.watch 1~4개")
        src = it.get("sources", [])
        if len(src) < 2 or any(not s.get("url", "").startswith("http") for s in src):
            err.append(f"{p}.sources 2개 이상, url 은 http 로 시작")
        sig = it.get("signals") or {}
        if not sig.get("from"):
            err.append(f"{p}.signals.from (어디서 포착했는지) 필요")
    return err


def main():
    path = Path(sys.argv[1])
    doc = json.loads(path.read_text(encoding="utf-8"))
    errs = check(doc)
    if errs:
        print("검증 실패:")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    idx_path = INS / "index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"days": []}
    entry = {"date": doc["date"], "items": [{"keyword": it["keyword"], "slug": it["slug"], "category": it["category"],
                                             "title": it["title"]} for it in doc["items"]]}
    idx["days"] = sorted([d for d in idx["days"] if d["date"] != doc["date"]] + [entry], key=lambda d: d["date"], reverse=True)
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"검증 통과 ✓ — index.json 갱신 ({len(idx['days'])}일치)")


if __name__ == "__main__":
    main()
