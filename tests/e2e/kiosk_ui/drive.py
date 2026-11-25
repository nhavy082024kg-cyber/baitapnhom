"""Kiem tra giao dien kiosk bang trinh duyet that (Playwright) voi mock_server.py dang chay.
  pip install playwright && playwright install chromium
  python mock_server.py      (cua so 1)
  python drive.py            (cua so 2)
"""
import json, urllib.request
from playwright.sync_api import sync_playwright

import os, tempfile
SHOTS = os.getenv("SHOTS_DIR", tempfile.gettempdir())
BASE = "http://127.0.0.1:5099"
def mode(m): urllib.request.urlopen(urllib.request.Request(f"{BASE}/__mode/{m}", method="POST"))
def on(page): return page.evaluate("[...document.querySelectorAll('section.on')].map(s=>s.id)")
results = []
def check(name, cond, extra=""):
    results.append((name, bool(cond), extra)); print(("PASS " if cond else "FAIL ") + name, extra)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 540, "height": 960})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # 1) khong co thong tin may -> man cai dat
    page.goto(BASE + "/kiosk/")
    page.wait_for_selector("#s-config.on")
    check("khong co credential -> man cai dat", on(page) == ["s-config"])
    # 2) nhap sai secret -> bao loi 401
    page.fill("#cfg-serial", "K1"); page.fill("#cfg-secret", "sai"); page.click("#cfg-save")
    page.wait_for_selector("#s-config.on")
    page.wait_for_function("document.querySelector('#cfg-err').textContent.length>0")
    check("secret sai -> thong bao loi", "không đúng" in page.inner_text("#cfg-err"))
    # 3) nhap dung
    page.fill("#cfg-secret", "sec"); page.click("#cfg-save")
    page.wait_for_selector("#s-idle.on")
    check("secret dung -> man hinh cho", on(page) == ["s-idle"])
    check("hien gia tu", "50.000đ" in page.inner_text("#idle-price"), page.inner_text("#idle-price"))
    page.screenshot(path=SHOTS + "/01-idle.png")
    # 4) chon huong
    page.click("#idle-start"); page.wait_for_selector("#s-choose.on")
    cards = page.query_selector_all("#choose-grid .card")
    check("hien 2 mui huong", len(cards) == 2)
    check("ten san pham khong bi hieu la HTML (XSS)", page.inner_text("#choose-grid .card .name") == "Rose <b>Noir</b>" and not page.query_selector("#choose-grid b"))
    check("slot sap het co nhan", "Sắp hết" in page.inner_text("#choose-grid"))
    page.screenshot(path=SHOTS + "/02-choose.png")
    cards[0].click(); page.wait_for_selector("#s-confirm.on")
    check("man xac nhan co gia", page.inner_text("#cf-price") == "50.000đ")
    page.screenshot(path=SHOTS + "/03-confirm.png")
    # 5) tao don (bam doi) -> chi 1 don
    page.dblclick("#cf-go"); page.wait_for_selector("#s-pay.on")
    check("man QR hien so tien", page.inner_text("#pay-amount") == "50.000đ")
    check("co QR hoac noi dung QR", page.query_selector("#pay-qr canvas, #pay-qr img, #pay-qr .qrtext") is not None)
    check("khong co nut gia lap khi khong dev", page.evaluate("document.querySelector('#dev').hidden") is True)
    page.screenshot(path=SHOTS + "/04-pay.png")
    # 6) bat dev, gia lap thanh toan -> xit -> thanh cong
    page.goto(BASE + "/kiosk/?dev=1"); page.wait_for_selector("#s-idle.on")
    page.click("#idle-start"); page.click("#choose-grid .card"); page.click("#cf-go"); page.wait_for_selector("#s-pay.on")
    check("dev=1 -> co nut gia lap", page.evaluate("document.querySelector('#dev').hidden") is False)
    page.click("#dev-pay")
    page.wait_for_selector("#s-dispensing.on", timeout=8000)
    check("sau thanh toan -> man dang xit", True); page.screenshot(path=SHOTS + "/05-dispensing.png")
    page.wait_for_selector("#s-success.on", timeout=12000)
    check("xit xong -> man thanh cong", True); page.screenshot(path=SHOTS + "/06-success.png")
    # 7) xit loi -> MANUAL_REVIEW -> man loi, khong co nut xit lai
    mode("fail")
    page.click("#s-success [data-go=idle]"); page.wait_for_selector("#s-idle.on")
    page.click("#idle-start"); page.click("#choose-grid .card"); page.click("#cf-go"); page.wait_for_selector("#s-pay.on")
    page.click("#dev-pay"); page.wait_for_selector("#s-failed.on", timeout=15000)
    check("xit loi -> man da thanh toan nhung chua xit", "ORD-" in page.inner_text("#fl-code"))
    check("man loi khong co nut thanh toan/xit lai", page.query_selector("#s-failed .btn:not([data-go=idle])") is None)
    page.screenshot(path=SHOTS + "/07-failed.png")
    # 8) may tam ngung
    mode("blocked")
    page.click("#s-failed [data-go=idle]"); page.wait_for_selector("#s-blocked.on")
    check("orderable=false -> man tam ngung", "bảo trì" in page.inner_text("#blocked-reason"))
    page.screenshot(path=SHOTS + "/08-blocked.png")
    check("khong co loi JavaScript", not errors, str(errors))
    b.close()
bad = [r for r in results if not r[1]]
print(f"\n{len(results)-len(bad)}/{len(results)} kiem tra dat")
