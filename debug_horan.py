#!/usr/bin/env python3
"""호란발전소 데이터 크롤링 디버그 스크립트."""
import os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HEADLESS_SHELL = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"
BROWSER_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]

XPATH_LOGIN_ID  = '//*[@id="input-27"]'
XPATH_LOGIN_PW  = '//*[@id="input-28"]'
XPATH_DATE_INPUT = '/html/body/div/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/div[2]/div/div/div[2]/div/div/input'
XPATH_MONTHLY_TAB = '//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[1]/div/div/div[2]/div/div[3]'
XPATH_EXCEL_BTN   = '//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/button[1]'
XPATH_SEARCH_BTN  = '/html/body/div/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/button[2]'
XPATH_CAL_HEADER_BTN = '/html/body/div/div[2]/div/div/div/div[1]/div/div/button'
XPATH_CAL_PREV_BTN   = '/html/body/div/div[2]/div/div/div/div[1]/button[1]'
XPATH_CAL_NEXT_BTN   = '/html/body/div/div[2]/div/div/div/div[1]/button[2]'
XPATH_CAL_MID_DAY    = '/html/body/div/div[2]/div/div/div/div[2]/table/tbody/tr[3]/td[4]/button'

SNAP_DIR = Path("/tmp/debug_horan")
SNAP_DIR.mkdir(exist_ok=True)

_MONTH_ABBR = {
    'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
    'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
}

def snap(page, name):
    p = str(SNAP_DIR / f"{name}.png")
    try:
        page.screenshot(path=p, timeout=8000)
        print(f"  📸 {p}", flush=True)
    except Exception as e:
        print(f"  [스크린샷 실패] {name}: {e}", flush=True)

def parse_cal_header(text):
    m = re.search(r"(\d{4})[^\d]+(\d{1,2})", text)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r"([A-Za-z]{3,})\s+(\d{4})", text)
    if m:
        mn = _MONTH_ABBR.get(m.group(1).lower()[:3])
        if mn: return int(m.group(2)), mn
    return None

def main():
    username = os.environ.get("HES_USERNAME", "")
    password = os.environ.get("HES_PASSWORD", "")
    if not username or not password:
        print("ERROR: HES_USERNAME / HES_PASSWORD 환경변수 필요", flush=True)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=HEADLESS_SHELL,
            args=BROWSER_ARGS,
        )
        page = browser.new_page(ignore_https_errors=True)

        # --- 로그인 ---
        print("\n[1] 로그인 페이지 이동", flush=True)
        page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
        snap(page, "00_login_initial")
        print(f"  URL: {page.url}", flush=True)

        # 입력창 존재 확인 (input-27 폴백으로 모든 input 탐색)
        all_inputs = page.locator('input').all()
        print(f"  input 수: {len(all_inputs)}", flush=True)
        for inp in all_inputs:
            try:
                print(f"    id={inp.get_attribute('id')!r} type={inp.get_attribute('type')!r} placeholder={inp.get_attribute('placeholder')!r}", flush=True)
            except Exception:
                pass

        login_id_sel = None
        for candidate in [
            f'xpath={XPATH_LOGIN_ID}',
            'input[type="text"]', 'input[type="email"]',
            'input[placeholder*="아이디"]', 'input[placeholder*="ID"]',
        ]:
            try:
                if page.locator(candidate).count() > 0:
                    login_id_sel = candidate
                    print(f"  아이디 입력창 선택자: {candidate!r}", flush=True)
                    break
            except Exception:
                pass

        login_pw_sel = None
        for candidate in [
            f'xpath={XPATH_LOGIN_PW}',
            'input[type="password"]',
            'input[placeholder*="비밀번호"]',
        ]:
            try:
                if page.locator(candidate).count() > 0:
                    login_pw_sel = candidate
                    print(f"  비번 입력창 선택자: {candidate!r}", flush=True)
                    break
            except Exception:
                pass

        if not login_id_sel or not login_pw_sel:
            # 페이지 HTML 일부 출력
            html = page.content()
            print(f"\n  페이지 HTML (앞 2000자):\n{html[:2000]}", flush=True)
            snap(page, "01_login_fail")
            print("ERROR: 로그인 폼 찾기 실패", flush=True)
            browser.close(); return
        snap(page, "01_login_page")

        print("[2] 아이디/비번 입력", flush=True)
        page.click(login_id_sel, force=True)
        page.keyboard.type(username)
        page.click(login_pw_sel, force=True)
        page.keyboard.type(password)
        snap(page, "02_filled")

        print("[3] 로그인 버튼 클릭", flush=True)
        try:
            page.locator('//button[.//span[contains(text(),"로그인")] or contains(text(),"로그인")]').first.click(timeout=5000)
        except Exception:
            page.click(f'xpath={XPATH_LOGIN_BTN}', timeout=5000) if hasattr(page,'click') else None

        try:
            page.wait_for_url(lambda url: "#/login" not in url, timeout=30000)
            print(f"  로그인 완료 → {page.url}", flush=True)
        except Exception as e:
            snap(page, "03_login_fail")
            err = page.locator('.v-messages__message,.error--text,[role="alert"]').all_inner_texts()
            print(f"ERROR: 로그인 실패: {e}\n  에러 메시지: {err}", flush=True)
            browser.close(); return
        snap(page, "03_after_login")

        # --- 호란(M0823) 페이지 이동 ---
        print("\n[4] 호란(M0823) siteWork 페이지 이동", flush=True)
        page.goto("https://hs3.hyundai-es.co.kr/#/siteWork?site_id=M0823")
        try:
            page.wait_for_selector(f'xpath={XPATH_DATE_INPUT}', timeout=15000)
            print("  페이지 로드 완료", flush=True)
        except Exception as e:
            snap(page, "04_horan_load_fail")
            print(f"ERROR: 호란 페이지 로드 실패: {e}", flush=True)
            browser.close(); return
        snap(page, "04_horan_loaded")
        print(f"  현재 URL: {page.url}", flush=True)

        # --- 날짜 피커: 2026년 6월 선택 ---
        print("\n[5] 날짜 피커 열기 (2026-06)", flush=True)
        page.click(f'xpath={XPATH_DATE_INPUT}')
        try:
            page.wait_for_selector(f'xpath={XPATH_CAL_HEADER_BTN}', timeout=5000)
        except Exception as e:
            snap(page, "05_cal_open_fail")
            print(f"ERROR: 달력 열기 실패: {e}", flush=True)
            browser.close(); return
        snap(page, "05_cal_opened")

        target = 2026 * 12 + 6
        header_loc = page.locator(f'xpath={XPATH_CAL_HEADER_BTN}').first
        for i in range(36):
            header_text = header_loc.inner_text().strip()
            print(f"  달력 헤더: {header_text!r}", flush=True)
            parsed = parse_cal_header(header_text)
            if not parsed:
                print("  헤더 파싱 실패 → 중단", flush=True)
                break
            cur = parsed[0] * 12 + parsed[1]
            if cur == target:
                print(f"  2026-06 도달!", flush=True)
                break
            elif cur > target:
                page.click(f'xpath={XPATH_CAL_PREV_BTN}')
            else:
                page.click(f'xpath={XPATH_CAL_NEXT_BTN}')
            for _ in range(20):
                page.wait_for_timeout(150)
                if header_loc.inner_text().strip() != header_text:
                    break

        snap(page, "06_cal_target_month")

        # 달력 테이블 HTML 출력
        try:
            cal_html = page.locator('xpath=/html/body/div/div[2]/div/div/div/div[2]/table').inner_html()
            print(f"\n  달력 HTML (앞 500자):\n{cal_html[:500]}", flush=True)
        except Exception as e:
            print(f"  달력 HTML 추출 실패: {e}", flush=True)

        print("\n[6] 중간 날짜 클릭", flush=True)
        try:
            page.click(f'xpath={XPATH_CAL_MID_DAY}')
        except Exception as e:
            snap(page, "07_cal_mid_click_fail")
            print(f"ERROR: 중간 날짜 클릭 실패: {e}", flush=True)
            # 달력 버튼들 나열
            btns = page.locator('xpath=/html/body/div/div[2]/div/div/div/div[2]/table//button').all()
            print(f"  달력 버튼 수: {len(btns)}", flush=True)
            for b in btns[:5]:
                print(f"    버튼: {b.inner_text().strip()!r}", flush=True)
            browser.close(); return

        page.wait_for_timeout(500)
        snap(page, "07_after_date_select")

        # 날짜 입력창 값 확인
        date_val = page.locator(f'xpath={XPATH_DATE_INPUT}').input_value().strip()
        print(f"\n[확인] 날짜 입력값: {date_val!r}", flush=True)

        # --- 조회 버튼 클릭 ---
        print("\n[7] 조회 버튼 클릭", flush=True)
        captured_responses = []
        page.on("response", lambda r: captured_responses.append(
            f"  {r.status} {r.request.resource_type:6s} {r.url[:100]}"
        ) if r.request.resource_type in ("xhr","fetch") else None)

        try:
            with page.expect_response(
                lambda r: r.request.resource_type in ("xhr","fetch") and r.status == 200,
                timeout=15000
            ):
                page.click(f'xpath={XPATH_SEARCH_BTN}')
        except Exception as e:
            snap(page, "08_search_fail")
            print(f"ERROR: 조회 버튼 오류: {e}", flush=True)

        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            page.wait_for_timeout(2000)
        snap(page, "08_after_search")

        print(f"\n  캡처된 XHR/fetch 응답:", flush=True)
        for r in captured_responses:
            print(r, flush=True)

        # --- 월간 탭 클릭 ---
        print("\n[8] 월간 탭 클릭", flush=True)
        try:
            page.click(f'xpath={XPATH_MONTHLY_TAB}')
        except Exception as e:
            snap(page, "09_monthly_tab_fail")
            print(f"ERROR: 월간 탭 클릭 실패: {e}", flush=True)
            # 탭 목록 출력
            tabs = page.locator('xpath=//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[1]/div/div/div[2]/div/div').all()
            print(f"  탭 수: {len(tabs)}", flush=True)
            for t in tabs:
                print(f"    탭: {t.inner_text().strip()!r}", flush=True)
            browser.close(); return

        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            page.wait_for_timeout(1500)
        snap(page, "09_monthly_tab")

        # 테이블 HTML 일부 출력 (데이터 확인)
        try:
            tbl_txt = page.locator('xpath=//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]').inner_text()
            print(f"\n  월간 데이터 영역 텍스트 (앞 600자):\n{tbl_txt[:600]}", flush=True)
        except Exception as e:
            print(f"  데이터 영역 텍스트 추출 실패: {e}", flush=True)

        # --- 엑셀 다운로드 ---
        print("\n[9] 엑셀 다운로드", flush=True)
        try:
            with page.expect_download(timeout=30000) as dl_info:
                page.click(f'xpath={XPATH_EXCEL_BTN}')
            dl = dl_info.value
            save_path = "/tmp/debug_horan_M0823.xlsx"
            dl.save_as(save_path)
            print(f"  다운로드 완료: {save_path} ({Path(save_path).stat().st_size} bytes)", flush=True)
        except Exception as e:
            snap(page, "10_excel_fail")
            print(f"ERROR: 엑셀 다운로드 실패: {e}", flush=True)
            # 엑셀 버튼 탐색
            btns = page.locator('xpath=//*[@id="app"]/div[1]/div[1]/main/div/div[2]/div/div[3]/div/div[2]/div/div/div/div/div[1]/div[2]/div[3]/button').all()
            print(f"  버튼 수: {len(btns)}", flush=True)
            for b in btns:
                print(f"    {b.inner_text().strip()!r}", flush=True)

        browser.close()

    # 다운로드된 파일 분석
    xlsx = Path("/tmp/debug_horan_M0823.xlsx")
    if xlsx.exists():
        import zipfile, xml.etree.ElementTree as ET
        print("\n[10] 다운로드 파일 분석", flush=True)
        with zipfile.ZipFile(xlsx) as z:
            ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                root = ET.fromstring(z.read("xl/sharedStrings.xml").decode("utf-8"))
                for si in root.iter(f"{{{ns}}}si"):
                    strings.append("".join(t.text or "" for t in si.iter(f"{{{ns}}}t")))
            root = ET.fromstring(z.read("xl/worksheets/sheet1.xml").decode("utf-8"))
            for i, row in enumerate(root.iter(f"{{{ns}}}row")):
                if i > 12: break
                cells = {}
                for cell in row.iter(f"{{{ns}}}c"):
                    ref = cell.get("r","")
                    col = re.sub(r"\d","",ref)
                    v = cell.find(f"{{{ns}}}v")
                    t = cell.get("t","")
                    if t=="s" and v is not None and v.text:
                        cells[col] = strings[int(v.text)]
                    elif v is not None:
                        cells[col] = v.text
                print(f"  행{i}: {cells}", flush=True)

    print(f"\n스크린샷: {SNAP_DIR}", flush=True)

if __name__ == "__main__":
    main()
