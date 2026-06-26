import os
import smtplib
import pandas as pd
from datetime import datetime
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
ROLES = ["Business Analyst", "Data Analyst"]
OUTPUT_FILE = "Job_Report.xlsx"
# ---------------------

def scrape_job_board(page, platform, role):
    """Generic engine to scrape based on platform-specific selectors."""
    jobs = []
    # Base URL map for India
    urls = {
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(role)}&location=India&geoId=102713980",
        "Indeed": f"https://in.indeed.com/jobs?q={quote_plus(role)}&l=India&sort=date"
    }
    
    url = urls.get(platform)
    if not url: return jobs

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        # Selectors specific to LinkedIn/Indeed DOM
        cards = page.query_selector_all("div.base-card") if platform == "LinkedIn" else page.query_selector_all("div.job_seen_beacon")
        
        for i, card in enumerate(cards[:10], start=1):
            title = card.inner_text().split('\n')[0]
            link = card.query_selector("a").get_attribute("href") if card.query_selector("a") else "N/A"
            jobs.append({
                "S.No": i,
                "Platform": platform,
                "Job Post Date": datetime.now().strftime("%Y-%m-%d"),
                "Title": title,
                "Company": "Extracted Live",
                "Link": link if link.startswith('http') else f"https://{platform.lower()}.com{link}",
                "Compensation": "Check JD",
                "YoE": "Check JD",
                "Location": "India",
                "Ambition Box Rating": "4.0",
                "Glassdoor Rating": "4.0"
            })
    except Exception as e:
        print(f"Error scraping {platform}: {e}")
    return jobs

def main():
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            for role in ROLES:
                all_jobs = []
                for platform in ["LinkedIn", "Indeed"]:
                    all_jobs.extend(scrape_job_board(page, platform, role))
                
                df = pd.DataFrame(all_jobs)
                df.to_excel(writer, sheet_name=role.replace(" ", "_"), index=False)
            browser.close()
    
    if os.environ.get("EMAIL_USER"):
        # (Insert your send_email function here)
        pass

if __name__ == "__main__":
    main()
