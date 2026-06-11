import os
import re
from datetime import date
from pathlib import Path
from playwright.sync_api import sync_playwright

SITES = {
    "M0823": "site_8023",  # 호란
    "M0824": "site_8024",  # 소미
}

XPATH_LOGIN_ID = '//*[@id="input-27"]'
XPATH_LOGIN_PW = '//*[@id="input-28"]'
# 절대 XPath 백업 — 텍스트 기반 선택자를 우선 시도
XPATH_LOGIN_BTN = '/html/body/div/div/div[1]/main/div/div[2]/main/div/div/div[2]/div[5]/div/button/span'
CSS_LOGIN_BTN = "button.v-btn--contained, button[type='submit']"
XPATH_DATE_INPUT = '/html/body/div/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/div[2]/div/div/div[2]/div/div/input'
XPATH_MONTHLY_TAB = '//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[1]/div/div/div[2]/div/div[3]'
XPATH_EXCEL_BTN = '//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/button[1]'
XPATH_CAL_HEADER_BTN = '/html/body/div/div[2]/div/div/div/div[1]/div/div/button'
XPATH_CAL_PREV_BTN = '/html/body/div/div[2]/div/div/div/div[1]/button[1]'
XPATH_CAL_NEXT_BTN = '/html/body/div/div[2]/div/div/div/div[1]/button[2]'
XPATH_CAL_MID_DAY = '/html/body/div/div[2]/div/div/div/div[2]/table/tbody/tr[3]/td[4]/button'
XPATH_DATE_DISPLAY = '/html/body/div/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/div[2]/div/div/div[2]/div'
XPATH_SEARCH_BTN = '/html/body/div/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/button[2]'

BASE_DIR = Path(__file__).parent / "past_data"

_MONTH_ABBR = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def _date_display_matches(display_text: str, year: int, month: int) -> bool:
    """날짜 입력창 표시값이 기대 연월과 일치하는지 확인. ISO·한국어·슬래시 포맷 모두 지원."""
    if not display_text:
        return False
    # ISO 형식: "2026-06-15"
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', display_text)
    if m:
        return int(m.group(1)) == year and int(m.group(2)) == month
    # 한국어 형식: "2026년 6월" / "2026년 06월 15일"
    m = re.search(r'(\d{4})[^\d]+(\d{1,2})', display_text)
    if m:
        return int(m.group(1)) == year and int(m.group(2)) == month
    # 슬래시 형식: "2026/06/15"
    m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', display_text)
    if m:
        return int(m.group(1)) == year and int(m.group(2)) == month
    # 폴백: 연도와 구분자 포함 월 패턴
    return str(year) in display_text and any(
        p in display_text for p in (
            f"-{month:02d}-", f"/{month:02d}/",
            f"년 {month:02d}월", f"년 {month}월",
        )
    )


def _parse_cal_header(text: str) -> tuple[int, int] | None:
    """연월 헤더 파싱. 'YYYY년 M월' 및 'Month YYYY' 형식 모두 지원."""
    m = re.search(r"(\d{4})[^\d]+(\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"([A-Za-z]{3,})\s+(\d{4})", text)
    if m:
        month_num = _MONTH_ABBR.get(m.group(1).lower()[:3])
        if month_num:
            return int(m.group(2)), month_num
    return None


def _months_in_range(start_ym: tuple[int, int], end_ym: tuple[int, int]) -> list[tuple[int, int]]:
    months = []
    y, m = start_ym
    while (y, m) <= end_ym:
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _safe_screenshot(page, path: str, timeout: int = 5000) -> None:
    try:
        page.screenshot(path=path, timeout=timeout)
    except Exception as e:
        print(f"[스크린샷 실패] {path}: {e}", flush=True)


def _login(page) -> None:
    print("[1] 로그인 페이지 이동 중...", flush=True)
    page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
    page.wait_for_selector(XPATH_LOGIN_ID, timeout=30000)
    _safe_screenshot(page, "/tmp/debug_01_page_loaded.png")

    # v-overlay 다이얼로그 닫기 시도 (공지사항 등 상시 팝업)
    if page.locator('.v-overlay--active').count() > 0:
        print("[오버레이] 감지 → 버튼 클릭 또는 ESC로 닫기 시도", flush=True)
        try:
            page.locator('.v-overlay--active button').first.click(timeout=3000)
            page.wait_for_selector('.v-overlay--active', state='hidden', timeout=5000)
            print("[오버레이] 버튼 클릭으로 닫힘", flush=True)
        except Exception:
            page.keyboard.press("Escape")
            try:
                page.wait_for_selector('.v-overlay--active', state='hidden', timeout=5000)
                print("[오버레이] ESC로 닫힘", flush=True)
            except Exception:
                print("[오버레이] 닫기 실패 — 계속 진행", flush=True)
        _safe_screenshot(page, "/tmp/debug_02_overlay_dismissed.png")

    print("[2] 아이디/비밀번호 입력 (keyboard.type)", flush=True)
    # fill()은 Vue 반응형 모델을 갱신하지 못할 수 있어 keyboard.type() 사용
    page.click(f'xpath={XPATH_LOGIN_ID}', force=True)
    page.keyboard.type(os.environ["HES_USERNAME"])
    page.click(f'xpath={XPATH_LOGIN_PW}', force=True)
    page.keyboard.type(os.environ["HES_PASSWORD"])
    _safe_screenshot(page, "/tmp/debug_03_form_filled.png")

    print("[3] 로그인 버튼 클릭", flush=True)
    # 텍스트 기반 선택자 우선 시도 → 실패 시 절대 XPath 폴백
    btn_clicked = False
    try:
        login_btn = page.locator('//button[.//span[contains(text(),"로그인")] or contains(text(),"로그인")]').first
        login_btn.click(timeout=5000)
        btn_clicked = True
        print("[3] 텍스트 기반 버튼 클릭 성공", flush=True)
    except Exception as e:
        print(f"[3] 텍스트 기반 버튼 클릭 실패({e}) → 절대 XPath 시도", flush=True)
    if not btn_clicked:
        try:
            page.click(f'xpath={XPATH_LOGIN_BTN}', timeout=5000)
            btn_clicked = True
            print("[3] 절대 XPath 버튼 클릭 성공", flush=True)
        except Exception as e:
            print(f"[3] 절대 XPath 버튼 클릭 실패({e}) → CSS 선택자 시도", flush=True)
    if not btn_clicked:
        page.click(CSS_LOGIN_BTN)
        print("[3] CSS 선택자 버튼 클릭 성공", flush=True)

    _safe_screenshot(page, "/tmp/debug_04_after_login_click.png")

    # URL 변경 또는 로그인 입력창 소멸 중 먼저 충족되는 조건 대기
    try:
        page.wait_for_url(lambda url: "#/login" not in url, timeout=30000)
        print(f"[4] 로그인 완료 (URL 변경) → {page.url}", flush=True)
    except Exception:
        _safe_screenshot(page, "/tmp/debug_05_login_timeout.png")
        # URL이 바뀌지 않았더라도 폼이 사라졌으면 성공으로 간주
        if page.locator(f'xpath={XPATH_LOGIN_ID}').count() == 0:
            print(f"[4] 로그인 완료 (폼 소멸) → {page.url}", flush=True)
        else:
            # 오류 메시지 캡처
            err_texts = page.locator('.v-messages__message, .error--text, [role="alert"]').all_inner_texts()
            if err_texts:
                print(f"[오류] 로그인 실패 메시지: {err_texts}", flush=True)
            raise


def _select_date_in_picker(page, year: int, month: int) -> None:
    print(f"    [날짜] 피커 열기 ({year}-{month:02d})", flush=True)
    page.click(f'xpath={XPATH_DATE_INPUT}')
    page.wait_for_selector(f'xpath={XPATH_CAL_HEADER_BTN}', timeout=5000)

    target = year * 12 + month
    header_loc = page.locator(f'xpath={XPATH_CAL_HEADER_BTN}').first
    for _ in range(36):
        header_text = header_loc.inner_text().strip()
        print(f"    [날짜] 현재 달력: {header_text!r}", flush=True)
        parsed = _parse_cal_header(header_text)
        if not parsed:
            print("    [날짜] 헤더 파싱 실패, 중단", flush=True)
            break
        cur = parsed[0] * 12 + parsed[1]
        if cur == target:
            print(f"    [날짜] 목표 달 도달", flush=True)
            break
        elif cur > target:
            print(f"    [날짜] 이전 달로 이동", flush=True)
            page.click(f'xpath={XPATH_CAL_PREV_BTN}')
        else:
            print(f"    [날짜] 다음 달로 이동", flush=True)
            page.click(f'xpath={XPATH_CAL_NEXT_BTN}')
        # 헤더가 실제로 바뀔 때까지 대기 (최대 3초)
        for _ in range(20):
            page.wait_for_timeout(150)
            if header_loc.inner_text().strip() != header_text:
                break

    print(f"    [날짜] 중간 날짜 클릭 → 팝업 닫기", flush=True)
    page.click(f'xpath={XPATH_CAL_MID_DAY}')
    page.wait_for_timeout(500)


def _download_month(page, site_id: str, year: int, month: int, save_dir: Path, force: bool = False) -> None:
    save_path = save_dir / f"{year}-{month:02d}-01.xlsx"
    if save_path.exists() and not force:
        print(f"  [스킵] 이미 존재: {save_path.name}", flush=True)
        return

    print(f"  [다운로드] {site_id} {year}-{month:02d} 페이지 이동 중...", flush=True)
    page.goto(f"https://hs3.hyundai-es.co.kr/#/siteWork?site_id={site_id}")
    page.wait_for_selector(f'xpath={XPATH_DATE_INPUT}', timeout=15000)
    print(f"  [다운로드] 페이지 로드 완료", flush=True)

    _select_date_in_picker(page, year, month)

    display_text = page.locator(f'xpath={XPATH_DATE_INPUT}').input_value().strip()
    print(f"  [확인] 날짜 표시값: {display_text!r}", flush=True)
    if not _date_display_matches(display_text, year, month):
        print(f"  [스킵] 날짜 불일치 ({year}-{month:02d} 기대, 실제: {display_text!r})", flush=True)
        return

    print(f"  [다운로드] 날짜 확인 완료 → 조회 버튼 클릭 (데이터 응답 대기 중...)", flush=True)
    with page.expect_response(
        lambda r: r.request.resource_type in ("xhr", "fetch") and r.status == 200,
        timeout=15000
    ):
        page.click(f'xpath={XPATH_SEARCH_BTN}')
    # 임의 지연 대신 네트워크 안정화까지 대기 (데이터 완전 로딩 보장)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        page.wait_for_timeout(1500)
    print(f"  [다운로드] 데이터 갱신 완료 → 월간 탭 클릭", flush=True)

    page.click(f'xpath={XPATH_MONTHLY_TAB}')
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        page.wait_for_timeout(1500)
    print(f"  [다운로드] 엑셀 다운로드 시작...", flush=True)
    with page.expect_download(timeout=30000) as dl_info:
        page.click(f'xpath={XPATH_EXCEL_BTN}')
    dl_info.value.save_as(str(save_path))
    print(f"  [완료] 저장: {save_path.name}", flush=True)


def get_past_excel(
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    force: bool = False,
) -> None:
    today = date.today()
    if end is None:
        end = (today.year, today.month)
    if start is None:
        sy, sm = today.year, today.month - 11
        if sm <= 0:
            sm += 12
            sy -= 1
        start = (sy, sm)

    months = _months_in_range(start, end)
    print(f"대상 기간: {start[0]}-{start[1]:02d} ~ {end[0]}-{end[1]:02d} ({len(months)}개월)", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            _login(page)
        except Exception:
            _safe_screenshot(page, "/tmp/debug_login.png")
            print(f"[디버그] 스크린샷 저장: /tmp/debug_login.png  현재 URL: {page.url}", flush=True)
            raise

        for site_id, folder in SITES.items():
            save_dir = BASE_DIR / folder
            save_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n--- {site_id} ({folder}) ---", flush=True)
            for year, month in months:
                _download_month(page, site_id, year, month, save_dir, force=force)

        browser.close()
    print("\n전체 완료", flush=True)


if __name__ == "__main__":
    import sys
    if "--current-month" in sys.argv:
        today = date.today()
        get_past_excel(start=(today.year, today.month), force=True)
    else:
        get_past_excel(start=(2022, 1))
