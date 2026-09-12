import argparse
import csv
import json
import os
import random
import re
import sys
import time
from bs4 import BeautifulSoup


def parse_submission_count(count_str):
    """
    Parses submission count string such as '51/500', '15', 'N/A' into an integer.
    Returns integer value of submitted ideas.
    """
    if not count_str:
        return 0
    clean = count_str.strip()
    match = re.search(r"(\d+)\s*/", clean)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return 0
    match_num = re.search(r"\b(\d+)\b", clean)
    if match_num:
        try:
            return int(match_num.group(1))
        except ValueError:
            return 0
    return 0


def parse_html_content(html):
    """
    Parses HTML content and extracts all problem statements from dataTablePS.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="dataTablePS")
    if not table:
        print("Error: Could not find table with id 'dataTablePS' in HTML.")
        return []

    tbody = table.find("tbody")
    rows = tbody.find_all("tr", recursive=False)
    results = []

    for row in rows:
        tds = row.find_all("td", recursive=False)
        if len(tds) < 8:
            continue

        s_no = tds[0].get_text(strip=True)
        organization = tds[1].get_text(strip=True)

        title_td = tds[2]
        title_link = title_td.find("a")
        title = title_link.get_text(strip=True) if title_link else title_td.get_text(strip=True)

        category = tds[3].get_text(strip=True)
        ps_number = tds[4].get_text(strip=True)
        raw_submission_count = tds[5].get_text(strip=True)
        theme = tds[6].get_text(strip=True)
        deadline = tds[7].get_text(strip=True)

        description = ""
        modal_id = ""
        if title_link and title_link.get("data-target"):
            modal_id = title_link.get("data-target").lstrip("#")
            modal_div = soup.find("div", id=modal_id)
            if modal_div:
                desc_td = modal_div.find("th", string=re.compile("Description", re.I))
                if desc_td and desc_td.find_next_sibling("td"):
                    description = desc_td.find_next_sibling("td").get_text(strip=True)

        total_submissions = parse_submission_count(raw_submission_count)

        results.append({
            "s_no": s_no,
            "ps_number": ps_number,
            "title": title,
            "organization": organization,
            "category": category,
            "theme": theme,
            "raw_submission_count": raw_submission_count,
            "total_submissions": total_submissions,
            "deadline": deadline,
            "description": description
        })

    return results


def parse_local_html(file_path):
    """
    Parses local HTML file and extracts all PS data.
    """
    if not os.path.exists(file_path):
        print(f"Error: Local file '{file_path}' not found.")
        sys.exit(1)

    print(f"Parsing local file: {file_path}")
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    return parse_html_content(html)


def setup_browser(headless=False):
    """
    Initializes a Chrome browser instance configured to bypass automated bot detection.
    Attempts to use undetected-chromedriver if available, otherwise configures
    Selenium with anti-detection flags and CDP navigator overrides.
    """
    try:
        import undetected_chromedriver as uc
        print("Initializing browser using undetected-chromedriver...")
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        driver = uc.Chrome(options=options)
        return driver
    except ImportError:
        pass

    print("undetected-chromedriver not found. Initializing browser using Selenium with stealth flags...")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    # Overwrite navigator.webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """
        }
    )
    return driver


def scrape_via_http(base_url="https://www.sih.gov.in/sih2026PS"):
    """
    Direct HTTP fallback using urllib and SSL bypass.
    Extracts all 240 problem statements from server-rendered HTML.
    """
    import urllib.request
    import ssl
    print(f"Attempting direct HTTP fetch from {base_url}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        base_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    records = parse_html_content(html)
    print(f"Direct HTTP fetch successful: {len(records)} problem statements extracted.")
    return records


def scrape_live_site(driver, base_url="https://www.sih.gov.in/sih2026PS", page_limit=None):
    """
    Navigates to the SIH Problem Statements page, iterates through pages and rows,
    opens each PS modal sequentially, extracts submission details, closes the modal,
    and returns all gathered records.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC

    print(f"Navigating to {base_url}...")
    driver.get(base_url)

    # Wait for the main table to load
    wait = WebDriverWait(driver, 20)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "dataTablePS")))
        print("Page loaded successfully. Table located.")
    except Exception as err:
        print(f"Selenium table wait timed out or failed ({err}). Falling back to direct HTTP fetch...")
        return scrape_via_http(base_url)

    # Optionally adjust page length to 100 entries per page if available
    try:
        length_select = driver.find_element(By.NAME, "dataTablePS_length")
        select_obj = Select(length_select)
        select_obj.select_by_value("100")
        print("Set page size to 100 entries per page.")
        time.sleep(2)
    except Exception as e:
        print(f"Could not change page size: {e}")

    results = []
    page_num = 1

    while True:
        print(f"\n--- Processing Page {page_num} ---")
        time.sleep(1.5)

        # Retrieve all table rows for current page
        table = driver.find_element(By.ID, "dataTablePS")
        tbody = table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.XPATH, "./tr")
        print(f"Found {len(rows)} rows on page {page_num}.")

        for i in range(len(rows)):
            try:
                # Re-fetch rows in case DOM references refreshed
                rows = driver.find_elements(By.XPATH, "//table[@id='dataTablePS']/tbody/tr")
                if i >= len(rows):
                    break
                row = rows[i]
                tds = row.find_elements(By.XPATH, "./td")
                if len(tds) < 8:
                    continue

                s_no = tds[0].text.strip()
                organization = tds[1].text.strip()
                category = tds[3].text.strip()
                ps_number = tds[4].text.strip()
                raw_submission_count = tds[5].text.strip()
                theme = tds[6].text.strip()
                deadline = tds[7].text.strip()

                # Locate title link that opens the modal
                title_link = None
                try:
                    title_link = tds[2].find_element(By.TAG_NAME, "a")
                    title = title_link.text.strip()
                except Exception:
                    title = tds[2].text.strip()

                print(f"[{s_no}] Opening PS {ps_number}: {title[:40]}... (Submissions: {raw_submission_count})")

                description = ""
                # Open modal by clicking link
                if title_link:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_link)
                    time.sleep(0.3)
                    try:
                        driver.execute_script("arguments[0].click();", title_link)
                    except Exception:
                        title_link.click()

                    # Wait briefly for modal to appear
                    time.sleep(random.uniform(0.4, 0.7))

                    # Extract modal details if present
                    try:
                        modal_target = title_link.get_attribute("data-target")
                        if modal_target:
                            modal_id = modal_target.lstrip("#")
                            modal_elem = driver.find_element(By.ID, modal_id)
                            desc_cells = modal_elem.find_elements(
                                By.XPATH, ".//tr[th[contains(text(), 'Description')]]/td"
                            )
                            if desc_cells:
                                description = desc_cells[0].text.strip()
                    except Exception:
                        pass

                    # Close modal to prevent screen blockage
                    try:
                        close_btn = driver.find_elements(By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]//button[contains(@class,'close')]")
                        if not close_btn:
                            close_btn = driver.find_elements(By.XPATH, "//button[@data-dismiss='modal']")
                        if close_btn:
                            driver.execute_script("arguments[0].click();", close_btn[0])
                        else:
                            driver.execute_script("$('.modal').modal('hide');")
                    except Exception:
                        driver.execute_script("$('.modal').modal('hide');")

                    time.sleep(0.3)

                total_submissions = parse_submission_count(raw_submission_count)

                results.append({
                    "s_no": s_no,
                    "ps_number": ps_number,
                    "title": title,
                    "organization": organization,
                    "category": category,
                    "theme": theme,
                    "raw_submission_count": raw_submission_count,
                    "total_submissions": total_submissions,
                    "deadline": deadline,
                    "description": description
                })

            except Exception as row_err:
                print(f"Error processing row {i}: {row_err}")
                continue

        if page_limit and page_num >= page_limit:
            print(f"Reached page limit ({page_limit}). Stopping pagination.")
            break

        # Check if Next page button is available and active
        try:
            next_btn = driver.find_element(By.ID, "dataTablePS_next")
            btn_class = next_btn.get_attribute("class") or ""
            if "disabled" in btn_class:
                print("Reached last page. Pagination finished.")
                break

            next_link = next_btn.find_element(By.TAG_NAME, "a")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_link)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", next_link)
            page_num += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"No further pages or error finding next button: {e}")
            break

    if not results:
        print("Warning: No records gathered from browser traversal. Falling back to direct HTTP extraction...")
        return scrape_via_http(base_url)

    return results


def save_and_rank_results(records, csv_file="sih_ps_ranked.csv", json_file="sih_ps_ranked.json"):
    """
    Sorts records in descending order based on total_submissions,
    displays a ranked summary table in the console, and exports to CSV and JSON.
    """
    if not records:
        print("No problem statement records found to rank.")
        return

    # Sort descending based on total_submissions
    ranked = sorted(records, key=lambda x: x["total_submissions"], reverse=True)

    print("\n" + "=" * 95)
    print("RANKED PROBLEM STATEMENTS (DESCENDING ORDER OF TOTAL SUBMISSIONS)")
    print("=" * 95)
    print(f"{'Rank':<6} {'PS Number':<12} {'Submissions':<14} {'Category':<12} {'Theme':<25} {'Title'}")
    print("-" * 95)

    for rank, item in enumerate(ranked, 1):
        ps_no = item["ps_number"] or "N/A"
        subs = f"{item['total_submissions']} ({item['raw_submission_count']})"
        cat = (item["category"] or "")[:10]
        theme = (item["theme"] or "")[:23]
        title = (item["title"] or "")[:35]
        print(f"{rank:<6} {ps_no:<12} {subs:<14} {cat:<12} {theme:<25} {title}")

    print("=" * 95)
    print(f"Total Problem Statements Extracted: {len(ranked)}")

    # Save to CSV
    fieldnames = [
        "rank",
        "ps_number",
        "total_submissions",
        "raw_submission_count",
        "category",
        "theme",
        "organization",
        "title",
        "deadline",
        "description"
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, item in enumerate(ranked, 1):
            row_dict = {
                "rank": rank,
                "ps_number": item["ps_number"],
                "total_submissions": item["total_submissions"],
                "raw_submission_count": item["raw_submission_count"],
                "category": item["category"],
                "theme": item["theme"],
                "organization": item["organization"],
                "title": item["title"],
                "deadline": item["deadline"],
                "description": item["description"]
            }
            writer.writerow(row_dict)

    print(f"Ranked results saved to CSV: {os.path.abspath(csv_file)}")

    # Save to JSON
    json_data = []
    for rank, item in enumerate(ranked, 1):
        entry = dict(item)
        entry["rank"] = rank
        json_data.append(entry)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"Ranked results saved to JSON: {os.path.abspath(json_file)}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape SIH 2026 Problem Statements, open each one by one, and rank by total submissions."
    )
    parser.add_argument(
        "--url",
        default="https://www.sih.gov.in/sih2026PS",
        help="Target URL of the SIH Problem Statements page."
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Parse local HTML file (Smart India Hackathon.html) without launching a browser."
    )
    parser.add_argument(
        "--file",
        default="Smart India Hackathon.html",
        help="Path to local HTML file when using --local."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode."
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Limit number of pages to scrape (useful for quick testing)."
    )
    parser.add_argument(
        "--csv",
        default=os.path.join("data", "sih_ps_ranked.csv"),
        help="Output CSV file path."
    )
    parser.add_argument(
        "--json",
        default=os.path.join("data", "sih_ps_ranked.json"),
        help="Output JSON file path."
    )

    args = parser.parse_args()

    if args.local:
        records = parse_local_html(args.file)
        save_and_rank_results(records, csv_file=args.csv, json_file=args.json)
        return

    records = []
    try:
        driver = setup_browser(headless=args.headless)
        try:
            records = scrape_live_site(driver, base_url=args.url, page_limit=args.pages)
        finally:
            driver.quit()
            print("Browser closed.")
    except Exception as browser_err:
        print(f"Browser execution encountered an error: {browser_err}")
        print("Switching to direct HTTP extraction fallback...")
        records = scrape_via_http(base_url=args.url)

    if records:
        save_and_rank_results(records, csv_file=args.csv, json_file=args.json)
    else:
        print("Error: No records could be extracted from live portal or local fallback.")


if __name__ == "__main__":
    main()

