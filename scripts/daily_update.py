#!/usr/bin/env python3
"""
당월 xlsx 파일을 재다운로드한다.
기존 파일을 삭제하고 get_past_data.get_past_excel() 로 재취득.
daily_update.yml 에서 호출된다.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from get_past_data import get_past_excel, BASE_DIR


def main() -> None:
    today = date.today()
    year, month = today.year, today.month

    # 당월 파일 삭제 → 강제 재다운로드
    for folder in ["site_8023", "site_8024"]:
        xlsx = BASE_DIR / folder / f"{year}-{month:02d}-01.xlsx"
        if xlsx.exists():
            xlsx.unlink()
            print(f"Removed stale file: {xlsx.name}")

    print(f"Downloading {year}-{month:02d} for all sites...")
    get_past_excel(start=(year, month), end=(year, month))
    print("Download complete.")


if __name__ == "__main__":
    main()
