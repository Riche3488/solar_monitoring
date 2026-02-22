import os

from playwright.sync_api import sync_playwright

XPATH_발전소1_발전시간 = '//*[@id="app"]/div/div[1]/main/div/div[2]/div/div[6]/div[1]/div/div[2]/div/div/div[3]/span'
XPATH_발전소2_발전시간 = '//*[@id="app"]/div/div[1]/main/div/div[2]/div/div[6]/div[2]/div/div[2]/div/div/div[3]/span'


def get_generation_time() -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://hs3.hyundai-es.co.kr/#/login")
        page.wait_for_selector('//*[@id="input-27"]')
        page.fill('//*[@id="input-27"]', os.environ["HES_USERNAME"])
        page.fill('//*[@id="input-28"]', os.environ["HES_PASSWORD"])
        page.click('//*[@id="app"]/div/div[1]/main/div/div[2]/main/div/div/div[2]/button')
        page.wait_for_url(lambda url: "login" not in url, timeout=10000)
        page.wait_for_selector(XPATH_발전소1_발전시간, timeout=10000)

        result = {
            "발전소1": page.inner_text(XPATH_발전소1_발전시간),
            "발전소2": page.inner_text(XPATH_발전소2_발전시간),
        }
        browser.close()
    return result


if __name__ == "__main__":
    data = get_generation_time()
    print(f"발전소1 발전 시간: {data['발전소1']}")
    print(f"발전소2 발전 시간: {data['발전소2']}")
