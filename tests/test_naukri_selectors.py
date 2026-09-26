from src.ingestion.naukri_browser import NaukriBrowser


print("\n========== NAUKRI SELECTOR TEST ==========")

browser = NaukriBrowser()

try:
    browser.start()

    browser.search_jobs(
        role="Data Analyst",
        location="Remote"
    )

    selectors = [
        "div.srp-jobtuple-wrapper",
        "article.jobTuple",
        "div.jobTuple",
        "article"
    ]

    print("\n========== SELECTOR COUNTS ==========")

    for selector in selectors:
        count = browser.page.locator(selector).count()

        print(f"{selector} -> {count}")

    print("\n========== JOB TITLE SELECTOR ==========")

    title_count = browser.page.locator("a.title").count()

    print(f"a.title -> {title_count}")

    print("\n========== SAMPLE HTML ==========")

    cards = browser.page.locator("div.srp-jobtuple-wrapper")

    if cards.count() > 0:
        print(cards.first.inner_html()[:5000])
    else:
        print("No elements found for div.srp-jobtuple-wrapper")

finally:
    browser.close()

print("\n========== TEST COMPLETED ==========")