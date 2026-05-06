# app/utils/open_now.py
from __future__ import annotations

import json
from datetime import datetime, time
from typing import Any, List, Optional, Tuple
from zoneinfo import ZoneInfo


def _parse_hhmm(s: Any) -> Optional[time]:
    if s is None:
        return None
    if not isinstance(s, str):
        return None
    t = s.strip()
    if not t:
        return None

    # accept "9:00" / "09:00"
    try:
        hh, mm = t.split(":")
        return time(hour=int(hh), minute=int(mm))
    except Exception:
        return None


def _normalize_windows(windows: Any) -> List[Tuple[str, str]]:
    """
    Normalize hours "windows" into List[(start_str, end_str)].

    Accept:
      - [("09:00","17:00"), ("18:00","20:00")]
      - [["09:00","17:00"], ["18:00","20:00"]]
      - ["09:00-17:00", "18:00-20:00"]
      - "09:00-17:00"
      - mixed / dirty inputs -> invalid entries are skipped
    """
    if not windows:
        return []

    # single string -> list
    if isinstance(windows, str):
        windows = [windows]

    out: List[Tuple[str, str]] = []

    # list/tuple expected
    if not isinstance(windows, (list, tuple)):
        return []

    for w in windows:
        # case A: ("09:00","17:00") or ["09:00","17:00"]
        if isinstance(w, (list, tuple)):
            if len(w) != 2:
                # <-- key fix: don't crash if len != 2
                continue
            start_s, end_s = w[0], w[1]
            if isinstance(start_s, str) and isinstance(end_s, str):
                out.append((start_s.strip(), end_s.strip()))
            continue

        # case B: "09:00-17:00"
        if isinstance(w, str):
            s = w.strip()
            if "-" not in s:
                continue
            a, b = s.split("-", 1)
            a, b = a.strip(), b.strip()
            if a and b:
                out.append((a, b))
            continue

        # other types -> skip
        continue

    return out


def is_open_now(hours: Any) -> Optional[bool]:
    """
    Return:
      - True / False if we can determine open state now
      - None if hours format is missing/unknown/unparseable

    NOTE: This function is defensive: it must never raise due to bad data.
    """

    if not hours:
        return None

    # Your store.hours might already be "windows", a JSON string,
    # or a dict keyed by weekday.
    # We'll support a few common patterns defensively.
    parsed_hours = hours
    tz_name = None

    if isinstance(hours, str):
        stripped = hours.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed_hours = json.loads(stripped)
            except Exception:
                parsed_hours = hours

    if isinstance(parsed_hours, dict):
        tz_name = parsed_hours.get("timezone")

    if tz_name:
        try:
            now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now = datetime.now()
    else:
        now = datetime.now()

    weekday = now.strftime("%a").lower()  # e.g. "mon", "tue"
    now_t = now.time()

    # -------- 1) If hours is dict-like: {"mon":[...], "tue":[...]} --------
    if isinstance(parsed_hours, dict):
        weekly_hours = parsed_hours.get("weekly", parsed_hours)
        # try common keys
        candidates = [
            weekday,
            weekday[:3],  # mon
            weekday.capitalize(),  # Mon (unlikely but safe)
        ]
        windows_raw = None
        for k in candidates:
            if k in weekly_hours:
                windows_raw = weekly_hours.get(k)
                break
        if windows_raw is None:
            # try full weekday keys: "monday"
            full = now.strftime("%A").lower()  # "monday"
            windows_raw = weekly_hours.get(full)

        windows = _normalize_windows(windows_raw)
    else:
        # -------- 2) else: treat hours itself as windows --------
        windows = _normalize_windows(parsed_hours)

    if not windows:
        return None

    # -------- 3) Evaluate windows --------
    for start_s, end_s in windows:
        st = _parse_hhmm(start_s)
        et = _parse_hhmm(end_s)
        if st is None or et is None:
            continue

        # normal window: 09:00-17:00
        if st <= et:
            if st <= now_t <= et:
                return True
        else:
            # overnight window: 22:00-02:00
            if now_t >= st or now_t <= et:
                return True

    return False
