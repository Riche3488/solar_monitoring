import os
import re
from datetime import date
from pathlib import Path
from playwright.sync_api import sync_playwright

SITES = {
    "M0823": "site_8023",  # 호란
    "M0824": "site_8024",  # 소미
}

# placeholder/type 기반 선택자 — Vuetify 자동생성 ID(input-N)는 업데이트마다 변경되므로 사용하지 않음
XPATH_LOGIN_ID = '//input[@placeholder="아이디를 입력하세요" or @placeholder="아이디" or @type="text"][1]'
XPATH_LOGIN_PW = '//input[@type="password"][1]'
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


def _dismiss_overlay_if_blocking(page) -> None:
    """로그인 폼을 가리는 별도 팝업만 닫는다. 로그인 폼 자체가 오버레이면 건드리지 않는다."""
    overlay = page.locator('.v-overlay--active')
    if overlay.count() == 0:
        return

    # 오버레이가 로그인 입력창을 포함하면 로그인 폼 자체이므로 닫지 않음
    if overlay.locator(f'xpath={XPATH_LOGIN_ID}').count() > 0:
        print("[오버레이] 로그인 폼이 오버레이 내부 → 닫지 않고 진행")
        return

    print("[오버레이] 별도 팝업 감지 → 닫기 시도")
    # 닫기(X) 버튼 또는 확인/닫기 텍스트 버튼 우선
    for selector in [
        '.v-overlay--active .v-btn--icon',
        '.v-overlay--active button:has-text("닫기")',
        '.v-overlay--active button:has-text("확인")',
        '.v-overlay--active button:has-text("Close")',
        '.v-overlay--active button',
    ]:
        try:
            btn = page.locator(selector).first
            if btn.count() > 0:
                btn.click(timeout=3000)
                overlay.wait_for(state='hidden', timeout=5000)
                print(f"[오버레이] '{selector}' 클릭으로 닫힘")
                page.wait_for_timeout(300)
                return
        except Exception:
            continue

    print("[오버레이] 버튼 닫기 실패 — 오버레이 무시하고 계속 진행")


def _type_into_input(page, xpath: str, value: str) -> None:
    """Vue v-model과 호환되도록 입력값을 주입한다."""
    loc = page.locator(f'xpath={xpath}')
    loc.click()
    # 기존 값 전체 선택 후 덮어씀
    page.keyboard.press("Control+a")
    page.keyboard.type(value)
    # 입력값이 반영됐는지 확인; 안 됐으면 JS로 강제 주입
    actual = loc.input_value()
    if actual != value:
        page.evaluate(
            """([sel, val]) => {
                const el = document.evaluate(sel, document, null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!el) return;
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                setter.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [xpath, value],
        )
        actual = loc.input_value()
    print(f"  입력 확인: 길이={len(actual)} (기대={len(value)})")


def _login(page) -> None:
    print("[1] 로그인 페이지 이동 중...")
    page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
    page.wait_for_selector(f'xpath={XPATH_LOGIN_ID}', timeout=15000)
    page.screenshot(path="/tmp/debug_01_page_loaded.png")

    _dismiss_overlay_if_blocking(page)
    page.screenshot(path="/tmp/debug_02_after_overlay.png")

    # 오버레이 처리 후 로그인 폼이 여전히 보이는지 확인
    if not page.locator(f'xpath={XPATH_LOGIN_ID}').is_visible():
        print("[복구] 로그인 폼 비가시 → 페이지 재이동")
        page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
        page.wait_for_selector(f'xpath={XPATH_LOGIN_ID}', timeout=15000)
        page.screenshot(path="/tmp/debug_02b_reloaded.png")

    print("[2] 아이디/비밀번호 입력")
    _type_into_input(page, XPATH_LOGIN_ID, os.environ["HES_USERNAME"])
    _type_into_input(page, XPATH_LOGIN_PW, os.environ["HES_PASSWORD"])
    page.screenshot(path="/tmp/debug_03_form_filled.png")

    print("[3] 로그인 버튼 클릭")
    btn_clicked = False
    for label, fn in [
        ("텍스트 XPath", lambda: page.locator('//button[.//span[contains(text(),"로그인")] or contains(text(),"로그인")]').first.click(timeout=5000)),
        ("절대 XPath",   lambda: page.click(f'xpath={XPATH_LOGIN_BTN}', timeout=5000)),
        ("CSS",          lambda: page.click(CSS_LOGIN_BTN, timeout=5000)),
    ]:
        if btn_clicked:
            break
        try:
            fn()
            btn_clicked = True
            print(f"[3] {label} 버튼 클릭 성공")
        except Exception as e:
            print(f"[3] {label} 버튼 클릭 실패 → {e}")

    if not btn_clicked:
        raise RuntimeError("로그인 버튼을 찾지 못함")

    page.screenshot(path="/tmp/debug_04_after_login_click.png")

    # 로그인 성공 대기 — URL 변경 또는 로그인 폼 소멸
    try:
        page.wait_for_url(lambda url: "#/login" not in url, timeout=30000)
        print(f"[4] 로그인 완료 (URL 변경) → {page.url}")
    except Exception:
        page.screenshot(path="/tmp/debug_05_login_timeout.png")
        if page.locator(f'xpath={XPATH_LOGIN_ID}').count() == 0:
            print(f"[4] 로그인 완료 (폼 소멸) → {page.url}")
        else:
            err_texts = page.locator(
                '.v-messages__message, .error--text, [role="alert"], .v-snack__content'
            ).all_inner_texts()
            print(f"[오류] 로그인 실패 — 화면 메시지: {err_texts or '없음'}")
            raise


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
