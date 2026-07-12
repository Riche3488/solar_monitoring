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


def _parse_rows(path: Path, year: int, month: int) -> list[dict]:
    """xlsx에서 과거 날짜 행을 파싱해 {day, gen, hours} 리스트 반환. 오류 시 빈 리스트."""
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
            rows = []
            for i, row in enumerate(root.iter(f"{{{ns}}}row")):
                if i < 2:
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
                rows.append({
                    "day": day,
                    "gen": _to_float(cells.get(2)),
                    "hours": _to_float(cells.get(4)),
                })
        return rows
    except Exception as e:
        print(f"  [검증] 파일 파싱 오류: {e}")
        return []


def _count_data_rows(path: Path, year: int, month: int) -> int:
    """xlsx에서 과거 날짜 중 gen/hours 값이 있는 행 수를 반환. 파싱 오류 시 -1."""
    rows = _parse_rows(path, year, month)
    if not rows and not path.exists():
        return -1
    return sum(1 for r in rows if r["gen"] is not None or r["hours"] is not None)


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
    try:
        get_past_excel(start=(year, month), end=(year, month))
        print("Download complete.")
    except Exception as e:
        print(f"  [경고] 다운로드 실패: {e}")
        print("  [재시도] 다운로드 재시도 중...")
        try:
            get_past_excel(start=(year, month), end=(year, month))
            print("Download complete (재시도 성공).")
        except Exception as e2:
            print(f"  [오류] 재시도도 실패: {e2}")
            print("  [복구] 이전 파일로 폴백 후 배포 계속 진행")

    # 다운로드된 파일 검증 — 빈 파일이면 이전 파일 복원
    failed = False
    parsed: dict[str, list] = {}
    for folder in ["site_8023", "site_8024"]:
        xlsx = BASE_DIR / folder / f"{year}-{month:02d}-01.xlsx"
        if not xlsx.exists():
            print(f"  [경고] {folder}: 파일이 다운로드되지 않음")
            if folder in backups:
                xlsx.write_bytes(backups[folder])
                print(f"  [복구] {folder}: 이전 파일 복원 완료 (배포 계속)")
            else:
                print(f"  [오류] {folder}: 백업 없음 → 배포 중단")
                failed = True
            continue

        rows = _parse_rows(xlsx, year, month)
        parsed[folder] = rows
        count = sum(1 for r in rows if r["gen"] is not None or r["hours"] is not None)
        nonzero = sum(1 for r in rows if (r["gen"] or 0) > 0 or (r["hours"] or 0) > 0)
        print(f"  [검증] {folder}: {count}개 데이터 행 (0 초과: {nonzero}개)", flush=True)
        if count == 0:
            print(f"  [경고] {folder}: 유효 데이터 없음 — 이전 파일 복원")
            if folder in backups:
                xlsx.write_bytes(backups[folder])
                print(f"  [복구] {folder}: 이전 파일 복원 완료 (배포 계속)")
            else:
                xlsx.unlink()
                print(f"  [오류] {folder}: 백업 없음 → 빈 파일 삭제, 배포 중단")
                failed = True

    # 최근 5일 기준: 한 사이트만 모두 0이면 포털 데이터 이상 경고
    _check_recent_zeros(parsed, year, month, today)

    if failed:
        print("\n[오류] 다운로드 검증 실패 — 복구 불가, 배포 중단")
        sys.exit(1)


def _check_recent_zeros(parsed: dict, year: int, month: int, today: date) -> None:
    """최근 N일 동안 한 사이트만 0이고 다른 사이트는 정상이면 경고 출력."""
    LOOKBACK = 5
    site_recent: dict[str, list[float | None]] = {}
    for folder, rows in parsed.items():
        recent = sorted(
            [r for r in rows if date(year, month, r["day"]) <= today],
            key=lambda r: r["day"],
            reverse=True,
        )[:LOOKBACK]
        site_recent[folder] = [r["gen"] for r in recent]

    for folder, gens in site_recent.items():
        other = [f for f in site_recent if f != folder]
        if not gens:
            continue
        all_zero = all((g is None or g == 0) for g in gens)
        if not all_zero:
            continue
        for other_folder in other:
            other_gens = site_recent[other_folder]
            other_has_data = any((g is not None and g > 0) for g in other_gens)
            if other_has_data:
                print(
                    f"  [경고] {folder}: 최근 {len(gens)}일 발전량 모두 0"
                    f" (반면 {other_folder}는 정상) — 포털 데이터 또는 발전소 상태 확인 필요",
                    flush=True,
                )


if __name__ == "__main__":
    main()
