"""공통 유틸: 경로, 설정 로딩, JSON 저장, 날짜, HTTP 재시도."""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("MP_DATA") or ROOT / "data")
SITE_DATA = Path(os.environ.get("MP_SITE_DATA") or ROOT / "site" / "data")
KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


def now_kst_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def load_config() -> dict:
    with open(ROOT / "config" / "markets.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp.replace(path)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def http(method: str, url: str, *, retries: int = 3, **kw) -> requests.Response:
    """429/5xx에 대해 지수 백오프 재시도. 4xx(429 제외)는 즉시 예외."""
    kw.setdefault("timeout", 30)
    last = None
    for i in range(retries):
        try:
            r = requests.request(method, url, **kw)
        except requests.RequestException as e:  # 네트워크 오류
            last = e
            time.sleep(2 ** i)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last = RuntimeError(f"{r.status_code} {r.text[:200]}")
            time.sleep(2 ** (i + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} {url}: {r.text[:300]}")
        return r
    raise RuntimeError(f"재시도 실패 {url}: {last}")


def norm_kw(s: str) -> str:
    """키워드 비교용 정규화: 공백 제거 + 대문자."""
    return "".join(str(s).split()).upper()
