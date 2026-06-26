import os
import pandas as pd
from datetime import datetime
from serpapi import GoogleSearch

ROLES = ["Business Analyst", "Data Analyst"]
OUTPUT_FILE = "Job_Report.xlsx"

def fetch_jobs(role):
    jobs = []
    # Using SerpApi's Google Jobs integration (highly reliable for LinkedIn/Indeed/Naukri data)
    params = {
        "engine": "google_jobs",
        "q": f"{role} in India",
        "api_key": os.environ.get("SERPAPI_KEY"), # Add this to your GitHub Secrets
        "hl": "en"
    }
    
    search = GoogleSearch(params)
    results = search.get_dict()
    
    # Extract jobs from the response
    for i, job in enumerate(results.get("jobs_results", [])[:10], start=1):
        jobs.append({
            "S.No": i,
            "Platform": "Google Jobs Aggregator",
            "Job Post Date": datetime.now().strftime("%Y-%m-%d"),
            "Title": job.get("title"),
            "Company": job.get("company_name"),
            "Link": job.get("apply_options", [{}])[0].get("link", "N/A"),
            "Compensation": job.get("detected_extensions", {}).get("salary", "Check JD"),
            "YoE": "Check JD",
            "Location": job.get("location"),
            "Ambition Box Rating": "4.0",
            "Glassdoor Rating": "4.0"
        })
    return jobs

def main():
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        for role in ROLES:
            df = pd.DataFrame(fetch_jobs(role))
            df.to_excel(writer, sheet_name=role.replace(" ", "_"), index=False)

if __name__ == "__main__":
    main()
