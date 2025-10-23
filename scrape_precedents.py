import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

# --- Configuration ---
ipc_section = "392" # <-- Change this for other sections (e.g., "420", "376")
driver_path = "/Users/keerthana/Downloads/chromedriver"
num_pages_to_scrape = 3 # How many search result pages to scrape
max_cases_to_scrape = 20 # Limit the total number of cases saved
output_filename = f"ipc_{ipc_section}_cases.csv"
base_url = "https://indiankanoon.org"
search_query = f"IPC+{ipc_section}+murder" # Adjust keyword if needed for other sections
search_url = f"{base_url}/search/?formInput={search_query}"
# --- End Configuration ---

print(f"🚀 Starting scraper for IPC {ipc_section}...")
print(f"📂 Output file will be: {output_filename}")

# Initialize WebDriver
try:
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    print("✅ WebDriver initialized.")
except Exception as e:
    print(f"❌ Error initializing WebDriver: {e}")
    print("👉 Please ensure ChromeDriver is installed and the 'driver_path' is correct.")
    exit()

# 1. Open the initial search page
try:
    driver.get(search_url)
    print(f"🌐 Opened search URL: {search_url}")
    time.sleep(4) # Allow page to load fully
except Exception as e:
    print(f"❌ Error opening search URL: {e}")
    driver.quit()
    exit()

# 2. Collect case links from specified number of pages
case_links = set() # Use a set to avoid duplicate links automatically
print(f"🔎 Scraping links from {num_pages_to_scrape} pages...")

for page_num in range(1, num_pages_to_scrape + 1):
    print(f"   Scraping page {page_num}...")
    try:
        # Give page time to load dynamic content
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # Find links specifically within the search results area for better accuracy
        result_divs = soup.find_all('div', class_='result')
        page_links_found = 0
        for div in result_divs:
             link_tag = div.find('a', href=lambda href: href and href.startswith('/doc/'))
             if link_tag:
                 href = link_tag.get("href")
                 full_link = base_url + href
                 case_links.add(full_link)
                 page_links_found +=1

        print(f"   Found {page_links_found} links on page {page_num}. Total unique links: {len(case_links)}")

        # Go to the next page if it's not the last page we need
        if page_num < num_pages_to_scrape:
            try:
                # Find the link for the next page number
                next_button = driver.find_element(By.LINK_TEXT, str(page_num + 1))
                print(f"   Navigating to page {page_num + 1}...")
                next_button.click()
                time.sleep(4) # Wait for next page to load
            except NoSuchElementException:
                print(f"   ⚠️ Could not find link for page {page_num + 1}. Stopping pagination.")
                break # Stop if next page link isn't found
            except Exception as e:
                print(f"   ❌ Error clicking next page button: {e}")
                break # Stop on other errors during navigation
    except Exception as e:
        print(f"   ❌ Error scraping page {page_num}: {e}")
        time.sleep(2) # Wait a bit before potentially retrying/stopping

print(f"✅ Finished link collection. Found {len(case_links)} unique case links.")

# Convert set to list and limit if needed
case_links_list = list(case_links)[:max_cases_to_scrape]

if not case_links_list:
    print("❌ No case links found. Exiting.")
    driver.quit()
    exit()

print(f"🧑‍⚖️ Scraping details for the first {len(case_links_list)} cases...")
# 3. Visit each case page and extract information
data = []
for i, link in enumerate(case_links_list, 1):
    print(f"   Processing case {i}/{len(case_links_list)}: {link}")
    try:
        driver.get(link)
        time.sleep(3) # Wait for case page to load

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract Case Name from Title
        case_name = "N/A"
        title_tag = soup.find("title")
        if title_tag:
             # Clean up title often includes " | Indian Kanoon"
             case_name = title_tag.text.split('|')[0].strip()

        # Extract Citation (often in a div with class 'docsource_main')
        citation = "N/A"
        citation_tag = soup.find("div", class_="docsource_main")
        if citation_tag:
            citation = citation_tag.get_text(strip=True)

        # Extract Summary/Headnotes (Try finding common preface sections first)
        summary = "N/A"
        pre_tags = soup.find_all("pre", {"id": lambda x: x and x.startswith('pre_')}) # Common for judgment text
        judgment_text_div = soup.find("div", class_="judgments") # Fallback container

        if pre_tags:
            # Combine text from first few <pre> tags as a summary
            summary_parts = [tag.get_text(strip=True) for tag in pre_tags[:3]] # Take first 3 <pre> blocks
            summary = "\n\n".join(summary_parts).strip()
        elif judgment_text_div:
             # Fallback: take beginning text from the judgments div
             summary = judgment_text_div.get_text(strip=True)[:1500] # Get more characters

        # Limit summary length if too long (optional)
        max_summary_length = 2000
        if len(summary) > max_summary_length:
             summary = summary[:max_summary_length] + "..."

        data.append({
            "case_name": case_name,
            "citation": citation,
            "link": link,
            "summary_text": summary # Changed column name
        })
        print(f"      -> Extracted: {case_name}")
        time.sleep(2) # IMPORTANT: Pause between requests

    except Exception as e:
        print(f"   ❌ Error processing case {link}: {e}")
        time.sleep(2) # Wait even if there's an error

# 4. Save data to CSV
if data:
    df = pd.DataFrame(data)
    try:
        df.to_csv(output_filename, index=False, encoding="utf-8")
        print(f"✅ Successfully scraped {len(data)} cases.")
        print(f"📁 Saved data to {output_filename}")
    except Exception as e:
        print(f"❌ Error saving data to CSV: {e}")
else:
    print("🤷 No data was successfully scraped.")

# 5. Close the browser
driver.quit()
print("🚪 Browser closed. Script finished.")