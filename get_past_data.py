import os
import re
from datetime import date
from pathlib import Path
from playwright.sync_api import sync_playwright

SITES = {
    "M0823": "site_8023",  # 호란
    "M0824": "site_8024",  # 소미
}

XPATH_LOGIN_BTN = '/html/body/div/div/div[1]/main/div/div[2]/main/div/div/div[2]/div[5]/div/button/span'
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


def _find_login_inputs(page) -> tuple[str | None, str | None]:
    """Vuetify 자동 생성 input ID를 동적으로 탐지한다.

    Vuetify는 input-N 형식의 ID를 컴포넌트 순서대로 생성하므로,
    사이트 업데이트 시 N값이 바뀌어도 동적으로 첫 두 visible input을 찾는다.
    """
    visible_ids: list[str] = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('input[id^="input-"]'))
            .filter(el => el.offsetParent !== null && !el.disabled)
            .map(el => el.id);
    }""")
    print(f"    [입력탐지] visible Vuetify input IDs: {visible_ids}")
    if len(visible_ids) >= 2:
        return f'//*[@id="{visible_ids[0]}"]', f'//*[@id="{visible_ids[1]}"]'
    return None, None


def _login(page) -> None:
    print("[1] 로그인 페이지 이동 중...")
    page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
    page.wait_for_selector('input:visible', timeout=15000)
    page.screenshot(path="/tmp/debug_01_page_loaded.png")

    # v-overlay 다이얼로그 닫기 시도 (공지사항 등 상시 팝업)
    if page.locator('.v-overlay--active').count() > 0:
        print("[오버레이] 감지 → 버튼 클릭 또는 ESC로 닫기 시도")
        try:
            page.locator('.v-overlay--active button').first.click(timeout=3000)
            page.wait_for_selector('.v-overlay--active', state='hidden', timeout=5000)
            print("[오버레이] 버튼 클릭으로 닫힘")
        except Exception:
            page.keyboard.press("Escape")
            try:
                page.wait_for_selector('.v-overlay--active', state='hidden', timeout=5000)
                print("[오버레이] ESC로 닫힘")
            except Exception:
                print("[오버레이] 닫기 실패 — 계속 진행")
        page.screenshot(path="/tmp/debug_02_overlay_dismissed.png")

    print("[2] 아이디/비밀번호 입력 (keyboard.type)")
    # fill()은 Vue 반응형 모델을 갱신하지 못할 수 있어 keyboard.type() 사용
    id_xpath, pw_xpath = _find_login_inputs(page)
    if id_xpath and pw_xpath:
        page.click(f'xpath={id_xpath}', force=True)
        page.keyboard.type(os.environ["HES_USERNAME"])
        page.click(f'xpath={pw_xpath}', force=True)
        page.keyboard.type(os.environ["HES_PASSWORD"])
    else:
        # Vuetify input-N 패턴이 없을 때: 순서 기반으로 첫 두 visible input 사용
        visible_inputs = page.locator('input:visible')
        n = visible_inputs.count()
        print(f"    [입력탐지] visible input 수: {n} → 순서 기반 사용")
        if n < 2:
            raise Exception(f"로그인 입력 필드를 찾을 수 없음 (visible inputs: {n})")
        visible_inputs.nth(0).click(force=True)
        page.keyboard.type(os.environ["HES_USERNAME"])
        visible_inputs.nth(1).click(force=True)
        page.keyboard.type(os.environ["HES_PASSWORD"])
    page.screenshot(path="/tmp/debug_03_form_filled.png")

    print("[3] 로그인 버튼 클릭")
    # 텍스트 기반 버튼 탐지를 먼저 시도하고, 실패 시 XPath fallback
    btn_clicked = False
    try:
        login_btn = page.locator('button').filter(has_text='로그인')
        if login_btn.count() > 0:
            login_btn.first.click()
            btn_clicked = True
            print("    '로그인' 텍스트 버튼 클릭")
    except Exception as e:
        print(f"    텍스트 버튼 탐지 실패: {e}")
    if not btn_clicked:
        page.click(f'xpath={XPATH_LOGIN_BTN}')
        print("    XPath 버튼 클릭 (fallback)")

    # 로그인 성공 확인: URL이 /login에서 벗어날 때까지 대기
    page.wait_for_function(
        "() => !window.location.hash.startsWith('#/login')",
        timeout=30000,
    )
    print(f"[4] 로그인 완료 → {page.url}")


def _select_date_in_picker(page, year: int, month: int) -> None:
    print(f"    [날짜] 피커 열기 ({year}-{month:02d})")
    page.click(f'xpath={XPATH_DATE_INPUT}')
    page.wait_for_selector(f'xpath={XPATH_CAL_HEADER_BTN}', timeout=5000)

    target = year * 12 + month
    header_loc = page.locator(f'xpath={XPATH_CAL_HEADER_BTN}').first
    for _ in range(36):
        header_text = header_loc.inner_text().strip()
        print(f"    [날짜] 현재 달력: {header_text!r}")
        parsed = _parse_cal_header(header_text)
        if not parsed:
            print("    [날짜] 헤더 파싱 실패, 중단")
            break
        cur = parsed[0] * 12 + parsed[1]
        if cur == target:
            print(f"    [날짜] 목표 달 도달")
            break
        elif cur > target:
            print(f"    [날짜] 이전 달로 이동")
            page.click(f'xpath={XPATH_CAL_PREV_BTN}')
        else:
            print(f"    [날짜] 다음 달로 이동")
            page.click(f'xpath={XPATH_CAL_NEXT_BTN}')
        # 헤더가 실제로 바뀔 때까지 대기 (최대 3초)
        for _ in range(20):
            page.wait_for_timeout(150)
            if header_loc.inner_text().strip() != header_text:
                break

    print(f"    [날짜] 중간 날짜 클릭 → 팝업 닫기")
    page.click(f'xpath={XPATH_CAL_MID_DAY}')
    page.wait_for_timeout(500)


def _download_month(page, site_id: str, year: int, month: int, save_dir: Path, force: bool = False) -> None:
    save_path = save_dir / f"{year}-{month:02d}-01.xlsx"
    if save_path.exists() and not force:
        print(f"  [스킵] 이미 존재: {save_path.name}")
        return

    print(f"  [다운로드] {site_id} {year}-{month:02d} 페이지 이동 중...")
    page.goto(f"https://hs3.hyundai-es.co.kr/#/siteWork?site_id={site_id}")
    page.wait_for_selector(f'xpath={XPATH_DATE_INPUT}', timeout=15000)
    print(f"  [다운로드] 페이지 로드 완료")

    _select_date_in_picker(page, year, month)

    display_text = page.locator(f'xpath={XPATH_DATE_INPUT}').input_value().strip()
    print(f"  [확인] 날짜 표시값: {display_text!r}")
    if str(year) not in display_text or f"{month:02d}" not in display_text:
        print(f"  [스킵] 날짜 불일치 ({year}-{month:02d} 기대, 실제: {display_text!r})")
        return

    print(f"  [다운로드] 날짜 확인 완료 → 조회 버튼 클릭 (데이터 응답 대기 중...)")
    with page.expect_response(
        lambda r: r.request.resource_type in ("xhr", "fetch") and r.status == 200,
        timeout=15000
    ):
        page.click(f'xpath={XPATH_SEARCH_BTN}')
    page.wait_for_timeout(500)
    print(f"  [다운로드] 데이터 갱신 완료 → 월간 탭 클릭")

    page.click(f'xpath={XPATH_MONTHLY_TAB}')
    page.wait_for_timeout(1000)
    print(f"  [다운로드] 엑셀 다운로드 시작...")
    with page.expect_download(timeout=30000) as dl_info:
        page.click(f'xpath={XPATH_EXCEL_BTN}')
    dl_info.value.save_as(str(save_path))
    print(f"  [완료] 저장: {save_path.name}")


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
    print(f"대상 기간: {start[0]}-{start[1]:02d} ~ {end[0]}-{end[1]:02d} ({len(months)}개월)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            _login(page)
        except Exception:
            page.screenshot(path="/tmp/debug_login.png")
            print(f"[디버그] 스크린샷 저장: /tmp/debug_login.png  현재 URL: {page.url}")
            raise

        for site_id, folder in SITES.items():
            save_dir = BASE_DIR / folder
            save_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n--- {site_id} ({folder}) ---")
            for year, month in months:
                _download_month(page, site_id, year, month, save_dir, force=force)

        browser.close()
    print("\n전체 완료")


if __name__ == "__main__":
    import sys
    if "--current-month" in sys.argv:
        today = date.today()
        get_past_excel(start=(today.year, today.month), force=True)
    else:
        get_past_excel(start=(2022, 1))
