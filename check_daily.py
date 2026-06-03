#!/usr/bin/env python3
"""
오늘의 일일 발전량을 현대ES 포털에서 스크레이핑한다.
"""
import os
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

SITES = {
    "M0823": "호란",
    "M0824": "소미",
}

XPATH_LOGIN_ID = '//*[@id="input-27"]'
XPATH_LOGIN_PW = '//*[@id="input-28"]'
XPATH_LOGIN_BTN = '/html/body/div/div/div[1]/main/div/div[2]/main/div/div/div[2]/div[5]/div/button/span'

KST = timezone(timedelta(hours=9))


def _login(page) -> None:
    print("[1] 로그인 중...")
    page.goto("https://hs3.hyundai-es.co.kr/#/login", wait_until="domcontentloaded")
    page.wait_for_selector(f'xpath={XPATH_LOGIN_ID}', timeout=20000)

    # 팝업 닫기
    if page.locator('.v-overlay--active').count() > 0:
        try:
            page.locator('.v-overlay--active button').first.click(timeout=3000)
            page.wait_for_selector('.v-overlay--active', state='hidden', timeout=5000)
        except Exception:
            page.keyboard.press("Escape")

    page.click(f'xpath={XPATH_LOGIN_ID}', force=True)
    page.keyboard.type(os.environ["HES_USERNAME"])
    page.click(f'xpath={XPATH_LOGIN_PW}', force=True)
    page.keyboard.type(os.environ["HES_PASSWORD"])
    page.click(f'xpath={XPATH_LOGIN_BTN}')
    page.wait_for_selector(f'xpath={XPATH_LOGIN_ID}', state='detached', timeout=30000)
    print(f"[2] 로그인 완료 → {page.url}")


def _get_daily_generation(page, site_id: str, site_name: str) -> dict:
    print(f"\n[{site_name}] 페이지 이동: site_id={site_id}")
    page.goto(f"https://hs3.hyundai-es.co.kr/#/siteWork?site_id={site_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    page.screenshot(path=f"/tmp/daily_{site_id}_01_loaded.png")

    # 페이지 전체 텍스트에서 발전량 관련 정보 추출
    content = page.content()

    # 발전량 데이터를 API 응답에서 인터셉트하는 방법 사용
    # 대신 페이지의 보이는 텍스트를 파싱
    try:
        # 오늘 날짜 기준으로 일간 탭이 기본인지 확인
        # 페이지 로드 후 주요 수치 요소 찾기
        page.wait_for_timeout(2000)
        page.screenshot(path=f"/tmp/daily_{site_id}_02_after_wait.png")

        # 숫자 데이터가 담긴 주요 카드/패널 텍스트 수집
        body_text = page.locator('body').inner_text()

        return {
            "site_id": site_id,
            "site_name": site_name,
            "body_text": body_text,
        }
    except Exception as e:
        print(f"  [오류] {e}")
        return {"site_id": site_id, "site_name": site_name, "error": str(e)}


def _get_daily_via_network(site_id: str, site_name: str) -> dict:
    """네트워크 응답을 인터셉트하여 발전량 데이터 수집."""
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        api_data = []

        def on_response(response):
            url = response.url
            if "hyundai-es.co.kr" in url and response.request.resource_type in ("xhr", "fetch"):
                try:
                    data = response.json()
                    api_data.append({"url": url, "data": data})
                    print(f"  [API] {url}")
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            _login(page)
        except Exception as e:
            page.screenshot(path="/tmp/daily_login_fail.png")
            print(f"[로그인 실패] {e}")
            browser.close()
            return {"error": f"로그인 실패: {e}"}

        for sid, sname in SITES.items():
            print(f"\n--- {sname} ({sid}) ---")
            api_data.clear()
            page.goto(f"https://hs3.hyundai-es.co.kr/#/siteWork?site_id={sid}", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path=f"/tmp/daily_{sid}_loaded.png")

            # 조회 버튼 클릭 (있으면)
            try:
                search_btns = page.locator('button').all()
                for btn in search_btns:
                    txt = btn.inner_text().strip()
                    if '조회' in txt or '검색' in txt:
                        btn.click()
                        page.wait_for_timeout(2000)
                        print(f"  [조회] 버튼 클릭: {txt!r}")
                        break
            except Exception:
                pass

            page.wait_for_timeout(2000)
            page.screenshot(path=f"/tmp/daily_{sid}_after_search.png")

            # 페이지 텍스트에서 kWh 수치 파싱
            body_text = page.locator('body').inner_text()
            results[sname] = {
                "site_id": sid,
                "api_responses": len(api_data),
                "body_text": body_text,
                "api_data": api_data[:3],  # 처음 3개만
            }

        browser.close()

    return results


if __name__ == "__main__":
    import json

    kst_now = datetime.now(KST)
    print(f"현재 시각 (KST): {kst_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not os.environ.get("HES_USERNAME") or not os.environ.get("HES_PASSWORD"):
        print("[오류] HES_USERNAME / HES_PASSWORD 환경변수가 설정되지 않았습니다.")
        exit(1)

    results = _get_daily_via_network("", "")
    print("\n=== 결과 ===")
    for site, data in results.items() if isinstance(results, dict) else []:
        print(f"\n[{site}]")
        if "error" in data:
            print(f"  오류: {data['error']}")
        else:
            print(f"  API 응답 수: {data['api_responses']}")
            # kWh 패턴 찾기
            import re
            kwh_matches = re.findall(r'[\d,]+\.?\d*\s*kWh', data.get("body_text", ""), re.IGNORECASE)
            mwh_matches = re.findall(r'[\d,]+\.?\d*\s*MWh', data.get("body_text", ""), re.IGNORECASE)
            print(f"  kWh 수치: {kwh_matches[:10]}")
            print(f"  MWh 수치: {mwh_matches[:10]}")
            if data.get("api_data"):
                print(f"  API 데이터 샘플:")
                for item in data["api_data"]:
                    print(f"    URL: {item['url']}")
                    print(f"    데이터: {json.dumps(item['data'], ensure_ascii=False)[:300]}")
