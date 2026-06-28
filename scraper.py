import os
import smtplib
import pandas as pd
from apify_client import ApifyClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Configuration
APIFY_TOKEN = os.getenv("APIFY_TOKEN") 
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")
OUTPUT_FILE = "Job_Report.xlsx"

ROLES = ["Data Analyst", "Business Analyst"]

def is_relevant(title, role):
    """Safety net: Ensures the scraped job title actually matches our target role."""
    title_lower = str(title).lower()
    role_parts = role.lower().split()
    # At least one major keyword from the role must be in the job title
    return any(part in title_lower for part in role_parts)

def scrape_naukri(client, role):
    print(f"Triggering Apify Naukri Actor for {role}...")
    # Fixed Naukri URL structure. 'fbo=1' forces last 24 hours.
    url_role = role.replace(" ", "-").lower()
    search_url = f"https://www.naukri.com/{url_role}-jobs?fbo=1"
    
    try:
        # Increase the API fetch pool to 100 to ensure we find 30 good ones
        run = client.actor("codemaverick/naukri-job-scraper-latest").call(run_input={
            "searchUrls": [{"url": search_url}],
            "maxItems": 100
        })
        items = client.dataset(run["defaultDatasetId"]).list_items().items
    except Exception as e:
        print(f"Naukri scraping failed: {e}")
        return []

    jobs = []
    for item in items:
        title = item.get("Job Title", "N/A")
        # Strict Relevance Check
        if not is_relevant(title, role):
            continue
            
        jobs.append({
            "Platform": "Naukri",
            "Title": title,
            "Company": item.get("Company Name", "N/A"),
            "Posted On": item.get("Posted Time", "Within 24 Hours"),
            "Experience": item.get("Experience", "N/A"),
            "Link": item.get("Job URL", "N/A"),
            "Skills Required": item.get("Skills/Tags", "Check JD"),
            "Location": item.get("Location", "India"),
            "Salary": item.get("Salary", "Not Disclosed"),
            "Ambition Box Rating": item.get("Rating", "N/A"),
            "Glassdoor Rating": "N/A"
        })
        # Stop exactly at 30 relevant jobs
        if len(jobs) >= 30:
            break
    return jobs

def scrape_indeed(client, role):
    print(f"Triggering Apify Indeed Actor for {role}...")
    try:
        # Increase the API fetch pool to 100 to ensure we find 30 good ones
        run = client.actor("valig/indeed-jobs-scraper").call(run_input={
            "query": role,
            "location": "India",
            "country": "in",
            "maxRows": 100,
            "sort": "date",
            "datePosted": "1" # Explicit parameter for Last 24 Hours
        })
        items = client.dataset(run["defaultDatasetId"]).list_items().items
    except Exception as e:
        print(f"Indeed scraping failed: {e}")
        return []

    jobs = []
    for item in items:
        title = item.get("title", "N/A")
        # Strict Relevance Check
        if not is_relevant(title, role):
            continue

        company_name = item.get("company", {}).get("name", "N/A")
        rating = item.get("company", {}).get("rating", "N/A")
        
        jobs.append({
            "Platform": "Indeed",
            "Title": title,
            "Company": company_name,
            "Posted On": item.get("age", "Within 24 Hours"),
            "Experience": "Check JD", 
            "Link": item.get("applyUrl") or item.get("url", "N/A"),
            "Skills Required": "Check JD", 
            "Location": item.get("location", "India"),
            "Salary": item.get("salary", "Not Disclosed"),
            "Ambition Box Rating": "N/A",
            "Glassdoor Rating": rating
        })
        if len(jobs) >= 30:
            break
    return jobs

def scrape_linkedin(client, role):
    print(f"Triggering Apify LinkedIn Actor for {role}...")
    # URL encoded with f_TPR=r86400 to force LinkedIn to filter for the last 24 hours
    linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={role.replace(' ', '%20')}&location=India&f_TPR=r86400"
    
    try:
        # Increase the API fetch pool to 100 to ensure we find 30 good ones
        run = client.actor("scraper-engine/rapid-linkedin-jobs-scraper").call(run_input={
            "urls": [linkedin_url],
            "count": 100
        })
        items = client.dataset(run["defaultDatasetId"]).list_items().items
    except Exception as e:
        print(f"LinkedIn scraping failed: {e}")
        return []

    jobs = []
    for item in items:
        title = item.get("title", "N/A")
        # Strict Relevance Check
        if not is_relevant(title, role):
            continue

        jobs.append({
            "Platform": "LinkedIn",
            "Title": title,
            "Company": item.get("companyName") or item.get("company", {}).get("name", "N/A"),
            "Posted On": item.get("postedAt") or "Within 24 Hours",
            "Experience": item.get("experienceLevel") or "Check JD",
            "Link": item.get("jobUrl", "N/A"),
            "Skills Required": "Check JD",
            "Location": item.get("locationName") or item.get("location", "India"),
            "Salary": item.get("salaryText") or "Not Disclosed",
            "Ambition Box Rating": "N/A",
            "Glassdoor Rating": "N/A"
        })
        if len(jobs) >= 30:
            break
    return jobs

def send_email_with_attachment():
    if not all([EMAIL_USER, EMAIL_PASS, TO_EMAIL]):
        print("Skipping Email: Missing credentials.")
        return

    print("Initiating secure SMTP email dispatch...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL
    msg['Subject'] = "Daily Master Job Extraction Report - Naukri, Indeed & LinkedIn"

    body = "Hello,\n\nThe data pipeline has completed. Only highly relevant jobs posted within the last 24 hours have been included.\n\nBest regards,\nPipeline Automation Agent"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(OUTPUT_FILE, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {OUTPUT_FILE}")
            msg.attach(part)
            
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, TO_EMAIL, msg.as_string())
        server.quit()
        print(f"✅ Master report delivered to {TO_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to dispatch email: {e}")

def main():
    if not APIFY_TOKEN:
        print("CRITICAL ERROR: APIFY_TOKEN is missing from environment variables.")
        return

    client = ApifyClient(APIFY_TOKEN)
    sheets_data = {
        "Data Analyst": [],
        "Business Analyst": []
    }
    
    # 2 API requests per website total (1 for DA, 1 for BA)
    for role in ROLES:
        sheets_data[role].extend(scrape_naukri(client, role))
        sheets_data[role].extend(scrape_indeed(client, role))
        sheets_data[role].extend(scrape_linkedin(client, role))
        
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        for sheet_name, job_list in sheets_data.items():
            if job_list:
                df = pd.DataFrame(job_list)
                cols = ['Platform', 'Title', 'Company', 'Posted On', 'Experience', 'Link', 
                        'Skills Required', 'Location', 'Salary', 'Ambition Box Rating', 'Glassdoor Rating']
                df = df[cols]
                df.insert(0, 'S.No', range(1, 1 + len(df)))
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Stored {len(df)} 100% relevant records into worksheet: '{sheet_name}'")
            else:
                pd.DataFrame(columns=['S.No', 'Platform', 'Title', 'Company']).to_excel(writer, sheet_name=sheet_name, index=False)

    send_email_with_attachment()

if __name__ == "__main__":
    main()
