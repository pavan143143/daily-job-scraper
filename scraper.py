import os
import smtplib
import pandas as pd
from email.message import EmailMessage
from datetime import datetime
from serpapi import GoogleSearch

# Configuration
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")
OUTPUT_FILE = "Job_Report.xlsx"

def fetch_jobs(query, location="India"):
    if not SERPAPI_KEY:
        print("CRITICAL ERROR: SERPAPI_KEY is missing!")
        return []
    
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("jobs_results", [])

def send_email(file_path):
    print("Attempting to send email...")
    msg = EmailMessage()
    msg['Subject'] = f"📊 Daily Job Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL
    msg.set_content("Your daily job report is attached.")
    
    with open(file_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="Job_Report.xlsx")
            
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    print(f"DEBUG: EMAIL_USER set: {bool(EMAIL_USER)}")
    print(f"DEBUG: SERPAPI_KEY set: {bool(SERPAPI_KEY)}")
    
    queries = ["Data Analyst", "Business Analyst"]
    all_data = []

    for q in queries:
        jobs = fetch_jobs(q)
        if not jobs:
            print(f"No jobs found for {q}. Check your API Key.")
        for job in jobs:
            all_data.append({
                "Role": q,
                "Title": job.get("title"),
                "Company": job.get("company_name"),
                "Location": job.get("location"),
                "Link": job.get("job_id")
            })

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"Report saved to {OUTPUT_FILE}")
        
        if EMAIL_USER and EMAIL_PASS and TO_EMAIL:
            send_email(OUTPUT_FILE)
        else:
            print("Skipping email: Missing email configuration.")
    else:
        print("No data collected, skipping email.")

if __name__ == "__main__":
    main()
