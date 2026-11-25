"""Kiem thu giao dien (E2E) bang Selenium tren trang Swagger /docs cua ScentStation.

Phat trien tu file mau TestLoginHistaff.py cua mon hoc, da sua cac diem yeu cua file mau:
  - 2 ham trung ten test_search_in_python_org (ham sau de ham truoc, test dau khong bao gio chay)
  - mat khau ghi cung trong code  -> doc tu bien moi truong
  - time.sleep(1000) trong tearDown (cho 16 phut) -> bo, dung WebDriverWait
  - khong co assert nen test khong the that bai -> co assert ro rang
  - driver.close() -> driver.quit()

Yeu cau: backend DANG CHAY (python src/app.py) voi tai khoan admin da duoc tao, Chrome da cai.
  pip install selenium
  PowerShell:
    $env:E2E_BASE_URL = "http://localhost:9999"
    $env:E2E_EMAIL = "admin@scentstation.local"
    $env:E2E_PASSWORD = "Admin@12345"
    python -m pytest tests/e2e -v
Khong co backend dang chay -> ca file tu bo qua.
"""
import os
import urllib.request

import pytest

selenium = pytest.importorskip("selenium")
from selenium import webdriver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.common.keys import Keys  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:9999")
EMAIL = os.getenv("E2E_EMAIL", "admin@scentstation.local")
PASSWORD = os.getenv("E2E_PASSWORD", "")
LOGIN_PATH = "/api/v1/auth/login"


def backend_is_up() -> bool:
    try:
        urllib.request.urlopen(BASE_URL + "/openapi.json", timeout=3)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not backend_is_up(), reason=f"Backend chua chay tai {BASE_URL}")


@pytest.fixture()
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("E2E_HEADLESS", "0") == "1":
        options.add_argument("--headless=new")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(0)
    yield drv
    drv.quit()


def open_login_operation(drv):
    drv.get(BASE_URL + "/docs")
    wait = WebDriverWait(drv, 20)
    summary = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, f'span.opblock-summary-path[data-path="{LOGIN_PATH}"]')))
    summary.click()
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".try-out__btn"))).click()
    return wait


def execute_login(drv, wait, email, password):
    body = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea.body-param__text")))
    body.send_keys(Keys.CONTROL, "a")
    body.send_keys(Keys.DELETE)
    body.send_keys('{"email": "%s", "password": "%s"}' % (email, password))
    drv.find_element(By.CSS_SELECTOR, "button.execute").click()
    status = wait.until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".live-responses-table td.response-col_status")))
    return status.text.strip()


def test_docs_page_loads_and_lists_login_endpoint(driver):
    driver.get(BASE_URL + "/docs")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, f'span.opblock-summary-path[data-path="{LOGIN_PATH}"]')))
    assert "ScentStation" in driver.title


@pytest.mark.skipif(not PASSWORD, reason="Dat E2E_PASSWORD de chay test dang nhap that")
def test_login_with_valid_account_returns_200(driver):
    wait = open_login_operation(driver)
    status = execute_login(driver, wait, EMAIL, PASSWORD)
    assert status.startswith("200")
    assert "access_token" in driver.find_element(By.CSS_SELECTOR, ".live-responses-table").text


def test_login_with_wrong_password_returns_401(driver):
    wait = open_login_operation(driver)
    # dung email khong ton tai de khong lam tang bo dem khoa (5 lan sai) cua tai khoan admin that
    status = execute_login(driver, wait, "khong-co@test.local", "mat-khau-sai-123")
    assert status.startswith("401")


def test_login_with_empty_body_returns_422(driver):
    wait = open_login_operation(driver)
    body = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea.body-param__text")))
    body.send_keys(Keys.CONTROL, "a")
    body.send_keys("{}")
    driver.find_element(By.CSS_SELECTOR, "button.execute").click()
    status = wait.until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".live-responses-table td.response-col_status"))).text.strip()
    assert status.startswith("422")
