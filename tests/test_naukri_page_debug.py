from src.ingestion.naukri_browser import NaukriBrowser


print("\n========== NAUKRI PAGE DEBUG ==========")

browser = NaukriBrowser()

try:
    browser.start()

    print("\nBrowser started.")

    browser.search_jobs(
        role="Data Analyst",
        location="Remote"
    )

    print("\nSearch completed.")

    print("\nCurrent URL:")
    print(browser.get_current_url())

    print("\nPage title:")
    print(browser.get_page_title())

    print("\nSecurity challenge detected:")
    print(browser.detect_security_challenge())

    page_text = browser.get_visible_text()

    print("\n========== PAGE TEXT ==========")
    print(page_text[:5000])
    print("========== END PAGE TEXT ==========")

    print("\nPage HTML length:")
    print(len(browser.page.content()))

finally:
    browser.close()

print("\n========== TEST COMPLETED ==========")