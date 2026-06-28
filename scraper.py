import os
import smtplib
import pandas as pd
from apify_client import ApifyClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Configuration 
APIFY_TOKEN = os.getenv("APIFY_TOKEN") # Replaced SERPAPI_KEY with APIFY_TOKEN
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")
OUTPUT_FILE = "Job_Report.xlsx"

ROLES = ["Data Analyst", "Business Analyst"]

def scrape_naukri(client, role):
    print(f"Triggering Apify Naukri Actor for {role}...")
    url_role = role.replace(" ", "-").lower()
    search_url = f"https://www.naukri.com/{url_role}-jobs-in-india?fbo=1"
    
    # Using the community Naukri scraper
    run = client.actor("codemaverick/naukri-job-scraper-latest").call(run_input={
        "searchUrls": [{"url": search_url}],
        "maxItems": 30
    })
    
    items = client.dataset(run["defaultDatasetId"]).list_items().items
    jobs = []
    for item in items:
        jobs.append({
            "Platform": "Naukri",
            "Role": role,
            "Title": item.get("Job Title", "N/A"),
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
    return jobs

def scrape_indeed(client, role):
    print(f"Triggering Apify Indeed Actor for {role}...")
    # Using the optimized Indeed scraper sorted by newest
    run = client.actor("valig/indeed-jobs-scraper").call(run_input={
        "query": role,
        "country": "in",
        "maxRows": 30,
        "sort": "date"
    })
    
    items = client.dataset(run["defaultDatasetId"]).list_items().items
    jobs = []
    for item in items:
        # Apify's Indeed actor nests some data differently
        company_name = item.get("company", {}).get("name", "N/A")
        rating = item.get("company", {}).get("rating", "N/A")
        
        jobs.append({
            "Platform": "Indeed",
            "Role": role,
            "Title": item.get("title", "N/A"),
            "Company": company_name,
            "Posted On": item.get("age", "Within 24 Hours"),
            "Experience": "Check JD", # Reserved for AI parsing
            "Link": item.get("applyUrl") or item.get("url", "N/A"),
            "Skills Required": "Check JD", # Reserved for AI parsing
            "Location": item.get("location", "India"),
            "Salary": item.get("salary", "Not Disclosed"),
            "Ambition Box Rating": "N/A",
            "Glassdoor Rating": rating
        })
    return jobs

def send_email_with_attachment():
    """Attaches the generated Excel file and dispatches via SMTP."""
    if not all([EMAIL_USER, EMAIL_PASS, TO_EMAIL]):
        print("Skipping Email: Missing email credentials in environment.")
        return

    print("Initiating SMTP email dispatch...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL
    msg['Subject'] = "Automated Daily Job Extraction - Apify Pipeline"

    body = "Hello,\n\nYour automated data engineering pipeline has completed successfully. Please find the latest listings for Data Analyst and Business Analyst roles attached.\n\nBest regards,\nAutomated Pipeline"
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
        print(f"✅ Email successfully delivered to {TO_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to dispatch email: {e}")

def main():
    if not APIFY_TOKEN:
        print("CRITICAL ERROR: APIFY_TOKEN is missing.")
        return

    client = ApifyClient(APIFY_TOKEN)
    sheets_data = {
        "Data Analyst": [],
        "Business Analyst": []
    }
    
    for role in ROLES:
        sheets_data[role].extend(scrape_naukri(client, role))
        sheets_data[role].extend(scrape_indeed(client, role))
        
    # Build a multi-sheet Excel file
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        for sheet_name, job_list in sheets_data.items():
            if job_list:
                df = pd.DataFrame(job_list)
                # Enforce Exact Column Order
                cols = ['Platform', 'Title', 'Company', 'Posted On', 'Experience', 'Link', 
                        'Skills Required', 'Location', 'Salary', 'Ambition Box Rating', 'Glassdoor Rating']
                df = df[cols]
                # Insert S.No
                df.insert(0, 'S.No', range(1, 1 + len(df)))
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Compiled {len(df)} jobs in sheet: '{sheet_name}'")
            else:
                pd.DataFrame(columns=['S.No', 'Platform', 'Title', 'Company']).to_excel(writer, sheet_name=sheet_name, index=False)

    send_email_with_attachment()

if __name__ == "__main__":
    main()
