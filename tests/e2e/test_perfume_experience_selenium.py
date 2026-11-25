# 6 test case: hiển thị lỗi ==> Chọn nước hoa ==> Luồng trải nghiệm
# ==> thanh toán demo (thành công) ==> lỗi, không cho thanh toán lại ==> máy bị khóa 


import os
from pathlib import Path
import urllib.request
import pytest

selenium = pytest.importorskip("selenium")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:5099"
SHOTS = Path(os.getenv("SHOTS_DIR", "test-results/selenium"))

def shot(browser, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    browser.save_screenshot(str(SHOTS / f"{name}.png"))


def server_up():
    try:
        urllib.request.urlopen(BASE + "/kiosk/", timeout=2)
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not server_up(), reason="Mock kiosk server chưa chạy tại port 5099")


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("E2E_HEADLESS", "0") == "1":
        options.add_argument("--headless=new")
    options.add_argument("--window-size=540,960")
    browser = webdriver.Chrome(options=options)
    browser.implicitly_wait(0)
    yield browser
    browser.quit()


def wait_screen(browser, screen):
    return WebDriverWait(browser, 12).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, f"#s-{screen}.on"))
    )


def reset_mode(mode="ok"):
    urllib.request.urlopen(urllib.request.Request(BASE + f"/__mode/{mode}", method="POST"), timeout=3)


def configure(browser, secret="sec", serial="K1"):
    browser.get(BASE + "/kiosk/?dev=1")
    wait_screen(browser, "config")
    browser.find_element(By.ID, "cfg-serial").send_keys(serial)
    browser.find_element(By.ID, "cfg-secret").send_keys(secret)
    browser.find_element(By.ID, "cfg-save").click()


def enter_choose(browser):
    wait_screen(browser, "idle")
    browser.find_element(By.ID, "idle-start").click()
    wait_screen(browser, "choose")


def test_wrong_device_secret_shows_error(driver):
    driver.get(BASE + "/kiosk/?dev=1")
    wait_screen(driver, "config")
    driver.find_element(By.ID, "cfg-serial").send_keys("K1")
    driver.find_element(By.ID, "cfg-secret").send_keys("wrong-secret")
    driver.find_element(By.ID, "cfg-save").click()
    wait_screen(driver, "config")
    assert "không đúng" in driver.find_element(By.ID, "cfg-err").text
    shot(driver, "TC01-invalid-device")


def test_catalog_selection_and_perfume_details(driver):
    reset_mode("unblock")
    configure(driver)
    enter_choose(driver)
    cards = driver.find_elements(By.CSS_SELECTOR, "#choose-grid .card")
    assert len(cards) == 2
    names = [c.find_element(By.CSS_SELECTOR, ".name").text for c in cards]
    assert "Rose <b>Noir</b>" in names  # verifies text is not interpreted as HTML
    assert "Sắp hết" in driver.find_element(By.ID, "choose-grid").text
    cards[0].click()
    wait_screen(driver, "confirm")
    assert driver.find_element(By.ID, "cf-name").text == "Rose <b>Noir</b>"
    assert driver.find_element(By.ID, "cf-price").text
    assert driver.find_element(By.ID, "cf-top").text == "Hồng"
    shot(driver, "TC02-perfume-details")


def test_order_shows_payment_qr_and_amount(driver):
    reset_mode("unblock")
    configure(driver)
    enter_choose(driver)
    driver.find_element(By.CSS_SELECTOR, "#choose-grid .card").click()
    wait_screen(driver, "confirm")
    driver.find_element(By.ID, "cf-go").click()
    wait_screen(driver, "pay")
    assert driver.find_element(By.ID, "pay-amount").text == "50.000đ"
    qr = driver.find_element(By.ID, "pay-qr")
    assert qr.find_elements(By.CSS_SELECTOR, "canvas, img, .qrtext")
    assert driver.find_element(By.ID, "dev").is_displayed()
    shot(driver, "TC03-payment-qr")


def test_demo_payment_reaches_success_screen(driver):
    reset_mode("ok")
    configure(driver)
    enter_choose(driver)
    driver.find_element(By.CSS_SELECTOR, "#choose-grid .card").click()
    wait_screen(driver, "confirm")
    driver.find_element(By.ID, "cf-go").click()
    wait_screen(driver, "pay")
    driver.find_element(By.ID, "dev-pay").click()
    wait_screen(driver, "dispensing")
    wait_screen(driver, "success")
    assert "Hoàn tất" in driver.find_element(By.ID, "s-success").text
    shot(driver, "TC04-experience-success")


def test_dispense_failure_does_not_offer_retry_payment(driver):
    reset_mode("fail")
    configure(driver)
    enter_choose(driver)
    driver.find_element(By.CSS_SELECTOR, "#choose-grid .card").click()
    wait_screen(driver, "confirm")
    driver.find_element(By.ID, "cf-go").click()
    wait_screen(driver, "pay")
    driver.find_element(By.ID, "dev-pay").click()
    wait_screen(driver, "failed")
    assert driver.find_element(By.ID, "fl-code").text.startswith("ORD-")
    buttons = driver.find_elements(By.CSS_SELECTOR, "#s-failed .btn")
    assert len(buttons) == 1  # only return-home, no retry/pay button
    shot(driver, "TC05-dispense-failure")


def test_machine_blocked_displays_unavailable_screen(driver):
    reset_mode("blocked")
    configure(driver)
    wait_screen(driver, "blocked")
    assert "bảo trì" in driver.find_element(By.ID, "blocked-reason").text.lower()
    shot(driver, "TC06-machine-blocked")
    reset_mode("unblock")
