import os
import csv
import smtplib
from email.message import EmailMessage
from datetime import datetime
from urllib.parse import quote_plus
import pandas as pd
from playwright.sync_api import sync_playwright

ROLES = ["Business Analyst", "Data Analyst"]
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def scrape_linkedin(page, role):
    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(role)}&f_TPR=r86400" # Last 24 hours
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(3000) # Let dynamic content load
    
    jobs = []
    cards = page.query_selector_all("div.base-card")[:10]
    for i, card in enumerate(cards, start=1):
        title_el = card.query_selector("h3")
        company_el = card.query_selector("h4")
        link_el = card.query_selector("a.base-card__full-link")
        loc_el = card.query_selector(".job-search-card__location")
        
        jobs.append({
            "s.no": i,
            "job_post_date": datetime.now().strftime("%Y-%m-%d"),
            "title": title_el.inner_text().strip() if title_el else "",
            "company": company_el.inner_text().strip() if company_el else "",
            "link": link_el.get_attribute("href") if link_el else "",
            "location": loc_el.inner_text().strip() if loc_el else "",
            "platform": "LinkedIn",
            "role": role
        })
    return jobs

# Add similar Playwright functions for Indeed, Naukri, and HiringCafe here...

def send_email(files):
    msg = EmailMessage()
    msg['Subject'] = f"Daily Job Matches - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = os.environ.get("EMAIL_USER")
    msg['To'] = os.environ.get("TO_EMAIL")
    msg.set_content("Attached are the latest job listings for today.")

    for file in files:
        with open(file, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype='text', subtype='csv', filename=os.path.basename(file))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
        smtp.send_message(msg)

def main():
    all_files = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        for role in ROLES:
            print(f"Scraping LinkedIn for {role}...")
            linkedin_jobs = scrape_linkedin(page, role)
            
            df = pd.DataFrame(linkedin_jobs)
            if not df.empty:
                filename = os.path.join(OUTPUT_DIR, f"{role.replace(' ', '_')}_Jobs.csv")
                df.to_csv(filename, index=False)
                all_files.append(filename)
                
        browser.close()
        
    if all_files and os.environ.get("EMAIL_USER"):
        send_email(all_files)
        print("Email dispatched successfully.")

if __name__ == "__main__":
    main()
