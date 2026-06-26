import pandas as pd
from serpapi import GoogleSearch
import os

# Configuration
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OUTPUT_FILE = "Job_Report.xlsx"

def fetch_jobs(query, location="India"):
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("jobs_results", [])

def main():
    # Example: Scraping Data Analyst and Business Analyst jobs
    queries = ["Data Analyst", "Business Analyst"]
    all_data = []

    for q in queries:
        print(f"Fetching jobs for: {q}")
        jobs = fetch_jobs(q)
        for job in jobs:
            all_data.append({
                "Role": q,
                "Title": job.get("title"),
                "Company": job.get("company_name"),
                "Location": job.get("location"),
                "Link": job.get("job_id") # Or relevant URL
            })

    # Save to Excel in the root directory
    df = pd.DataFrame(all_data)
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Report saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
