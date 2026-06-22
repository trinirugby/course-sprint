import pathlib
from playwright.sync_api import sync_playwright

URL = pathlib.Path(r"C:\Users\taylo\course-sprint\index.html").as_uri()
errors = []
results = []

def check(name, cond):
    results.append((name, bool(cond)))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # iPhone-ish mobile viewport
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3)
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_load_state("networkidle")

    # 1. No console/page errors
    check("no JS errors on load", len(errors) == 0)

    # 2. All four units render
    units = page.locator("details.unit").count()
    check("4 units render", units == 4)

    # 3. Total task cards == 39 (our TASKS length)
    cards = page.locator(".card").count()
    check("39 task cards render", cards == 39)

    # 4. A project (Greetings) is LOCKED initially (its watch not done)
    greet = page.locator("#cbx-u1-build-greetings")
    check("Greetings locked initially", greet.is_disabled())
    check("Greetings shows lock hint", page.locator("#card-u1-build-greetings.locked").count() == 1)

    # 5. Overall starts at 0%
    check("overall starts 0%", page.locator("#overallPct").inner_text().strip() == "0%")

    # 6. Tick the gating watch (Input & Output) -> Greetings unlocks live
    #    (click the input via JS = same path as clicking its custom label in the UI)
    page.eval_on_selector("#cbx-u1-watch-io", "el => el.click()")
    page.wait_for_timeout(150)
    check("Greetings unlocks after watch ticked", not greet.is_disabled())
    check("lock class removed", page.locator("#card-u1-build-greetings.locked").count() == 0)

    # 7. Overall % moved off 0 and unit-1 count updated
    check("overall advanced", page.locator("#overallPct").inner_text().strip() != "0%")
    check("unit1 count shows 1/", page.locator("#count-1").inner_text().startswith("1/"))

    # 8. Next task button enabled and dashboard shows current unit
    check("next btn enabled", page.locator("#nextBtn").is_enabled())
    check("dash shows Unit", "Unit" in page.locator("#dashSub").inner_text())

    # 9. Now complete Greetings, then Next task should target a still-incomplete unlocked task
    page.eval_on_selector("#cbx-u1-build-greetings", "el => el.click()")
    page.wait_for_timeout(100)
    page.eval_on_selector("#nextBtn", "el => el.click()")
    page.wait_for_timeout(400)

    # 10. Every watch/install resource link has a real http href + target=_blank
    links = page.locator("a.res")
    n = links.count()
    bad = 0
    for i in range(n):
        href = links.nth(i).get_attribute("href") or ""
        tgt = links.nth(i).get_attribute("target") or ""
        if not href.startswith("http") or tgt != "_blank":
            bad += 1
    check("all resource links http + new tab", bad == 0 and n >= 14)

    # 11. PERSISTENCE: reload, ticked state survives
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(150)
    check("watch-io still checked after reload", page.locator("#cbx-u1-watch-io").is_checked())
    check("greetings still checked after reload", page.locator("#cbx-u1-build-greetings").is_checked())
    check("overall persisted (non-zero)", page.locator("#overallPct").inner_text().strip() != "0%")

    # 12. Locked checkbox cannot be toggled by label click (Tic Tac Toe still locked)
    before = page.locator("#cbx-u2-build-tictactoe").is_checked()
    page.eval_on_selector("label.title[for='cbx-u2-build-tictactoe']", "el => el.click()")
    page.wait_for_timeout(100)
    after = page.locator("#cbx-u2-build-tictactoe").is_checked()
    check("locked task not togglable via label", before == after == False)

    page.screenshot(path=r"C:\Users\taylo\course-sprint\_verify_mobile.png", full_page=True)
    browser.close()

print("\n=== VERIFICATION RESULTS ===")
allpass = True
for name, ok in results:
    print(("PASS" if ok else "FAIL"), "-", name)
    if not ok:
        allpass = False
if errors:
    print("\nConsole/page errors captured:")
    for e in errors:
        print("  ", e)
print("\nOVERALL:", "ALL PASS" if allpass else "SOME FAILED")
