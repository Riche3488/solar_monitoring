#!/usr/bin/env python3
"""
당월 xlsx 파일을 재다운로드한다.
기존 파일을 삭제하고 get_past_data.get_past_excel() 로 재취득.
daily_update.yml 에서 호출된다.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from get_past_data import get_past_excel, BASE_DIR


def _col_to_idx(col: str) -> int:
    idx = 0
    for c in col.upper():
        idx = idx * 26 + (ord(c) - ord("A") + 1)
    return idx - 1


def _to_float(v) -> float | None:
    if v is None or str(v).strip() in ("", "-"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _count_data_rows(path: Path, year: int, month: int) -> int:
    """xlsx에서 과거 날짜 중 gen/hours 값이 있는 행 수를 반환. 파싱 오류 시 -1."""
    try:
        with zipfile.ZipFile(path) as z:
            strings: list[str] = []
            ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            if "xl/sharedStrings.xml" in z.namelist():
                root = ET.fromstring(z.read("xl/sharedStrings.xml").decode("utf-8"))
                for si in root.iter(f"{{{ns}}}si"):
                    strings.append("".join(t.text or "" for t in si.iter(f"{{{ns}}}t")))

            root = ET.fromstring(z.read("xl/worksheets/sheet1.xml").decode("utf-8"))
            today = date.today()
            count = 0
            for i, row in enumerate(root.iter(f"{{{ns}}}row")):
                if i < 2:  # skip header + monthly-average rows
                    continue
                cells: dict[int, str | None] = {}
                for cell in row.iter(f"{{{ns}}}c"):
                    ref = cell.get("r", "")
                    col_str = re.sub(r"\d", "", ref)
                    if not col_str:
                        continue
                    col_idx = _col_to_idx(col_str)
                    t = cell.get("t", "")
                    v_el = cell.find(f"{{{ns}}}v")
                    if t == "s" and v_el is not None and v_el.text:
                        cells[col_idx] = strings[int(v_el.text)]
                    elif v_el is not None:
                        cells[col_idx] = v_el.text
                    else:
                        cells[col_idx] = None

                day_str = cells.get(1)
                if not day_str:
                    continue
                m = re.match(r"(\d+)", str(day_str))
                if not m:
                    continue
                day = int(m.group(1))
                try:
                    if date(year, month, day) > today:
                        continue
                except ValueError:
                    continue

                if _to_float(cells.get(2)) is not None or _to_float(cells.get(4)) is not None:
                    count += 1
        return count
    except Exception as e:
        print(f"  [검증] 파일 파싱 오류: {e}")
        return -1


def main() -> None:
    today = date.today()
    year, month = today.year, today.month

    # 당월 파일 삭제 전 백업 보관
    backups: dict[str, bytes] = {}
    for folder in ["site_8023", "site_8024"]:
        xlsx = BASE_DIR / folder / f"{year}-{month:02d}-01.xlsx"
        if xlsx.exists():
            backups[folder] = xlsx.read_bytes()
            xlsx.unlink()
            print(f"Removed stale file: {xlsx.name} (백업 보관)")

    print(f"Downloading {year}-{month:02d} for all sites...")
    get_past_excel(start=(year, month), end=(year, month))
    print("Download complete.")

    # 다운로드된 파일 검증 — 빈 파일이면 이전 파일 복원
    failed = False
    for folder in ["site_8023", "site_8024"]:
        xlsx = BASE_DIR / folder / f"{year}-{month:02d}-01.xlsx"
        if not xlsx.exists():
            print(f"  [경고] {folder}: 파일이 다운로드되지 않음")
            if folder in backups:
                xlsx.write_bytes(backups[folder])
                print(f"  [복구] {folder}: 이전 파일 복원")
            failed = True
            continue

        count = _count_data_rows(xlsx, year, month)
        print(f"  [검증] {folder}: {count}개 데이터 행")
        if count == 0:
            print(f"  [경고] {folder}: 유효 데이터 없음 — 이전 파일 복원")
            if folder in backups:
                xlsx.write_bytes(backups[folder])
                print(f"  [복구] {folder}: 이전 파일 복원 완료")
            else:
                xlsx.unlink()
                print(f"  [복구] {folder}: 백업 없음 → 빈 파일 삭제")
            failed = True

    if failed:
        print("\n[오류] 다운로드 검증 실패 — 이전 데이터 유지, 배포 중단")
        sys.exit(1)


if __name__ == "__main__":
    main()
