#!/usr/bin/env python3
"""
past_data/**/*.xlsx 를 읽어 dashboard/frontend/public/data.json 으로 변환.
firebase deploy 전, 또는 새 xlsx 추가 후 실행하면 된다.
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "past_data"
OUT_FILE = BASE_DIR / "dashboard" / "frontend" / "public" / "data.json"


def _col_to_idx(col: str) -> int:
    idx = 0
    for c in col.upper():
        idx = idx * 26 + (ord(c) - ord("A") + 1)
    return idx - 1


def _read_xlsx(path: Path) -> list:
    with zipfile.ZipFile(path) as z:
        strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml").decode("utf-8"))
            ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            for si in root.iter(f"{{{ns}}}si"):
                strings.append("".join(t.text or "" for t in si.iter(f"{{{ns}}}t")))

        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml").decode("utf-8"))
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        result = []
        for row in root.iter(f"{{{ns}}}row"):
            cells: dict[int, str | None] = {}
            max_col = 0
            for cell in row.iter(f"{{{ns}}}c"):
                ref = cell.get("r", "")
                col_str = re.sub(r"\d", "", ref)
                if not col_str:
                    continue
                col_idx = _col_to_idx(col_str)
                max_col = max(max_col, col_idx)
                t = cell.get("t", "")
                v_el = cell.find(f"{{{ns}}}v")
                if t == "s" and v_el is not None and v_el.text:
                    cells[col_idx] = strings[int(v_el.text)]
                elif t == "inlineStr":
                    t_el = cell.find(f".//{{{ns}}}t")
                    cells[col_idx] = t_el.text if t_el is not None else ""
                elif v_el is not None:
                    cells[col_idx] = v_el.text
                else:
                    cells[col_idx] = None
            result.append([cells.get(i) for i in range(max_col + 1)])
        return result


def _to_float(v) -> float | None:
    if v is None or str(v).strip() in ("", "-"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_file(site_id: str, year: int, month: int, path: Path) -> list:
    try:
        rows = _read_xlsx(path)
    except Exception as e:
        print(f"  Warning: {path.name}: {e}", file=sys.stderr)
        return []

    result = []
    for row in rows[2:]:  # row[0]=헤더, row[1]=월평균
        if not row or len(row) < 3:
            continue
        day_str = row[1] if len(row) > 1 else None
        if not day_str:
            continue
        m = re.match(r"(\d+)", str(day_str))
        if not m:
            continue
        gen = _to_float(row[2] if len(row) > 2 else None)
        hours = _to_float(row[4] if len(row) > 4 else None)
        if gen is None and hours is None:
            continue
        day = int(m.group(1))
        result.append({
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "year": year,
            "month": month,
            "day": day,
            "site_id": site_id,
            "generation_kwh": gen,
            "generation_hours": hours,
        })
    return result


def build() -> None:
    all_data: list[dict] = []
    for site_dir in sorted(d for d in DATA_DIR.iterdir() if d.is_dir()):
        files = sorted(site_dir.glob("*.xlsx"))
        print(f"  {site_dir.name}: {len(files)} files")
        for xlsx in files:
            m = re.match(r"(\d{4})-(\d{2})-\d{2}\.xlsx", xlsx.name)
            if not m:
                continue
            all_data.extend(
                _parse_file(site_dir.name, int(m.group(1)), int(m.group(2)), xlsx)
            )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"\nDone: {len(all_data):,} records -> {OUT_FILE.relative_to(BASE_DIR)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    print(f"Reading from: {DATA_DIR}")
    build()
