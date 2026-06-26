import os
import re
import csv
from datetime import datetime
from urllib.parse import quote_plus

import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

ROLES = ["Business Analyst", "Data Analyst"]
PLATFORMS = ["linkedin", "indeed", "instahyre", "hiringcafe", "naukri"]
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(x):
    return re.sub(r"\s+", " ", x).strip() if x else ""


def safe_get(url, params=None, timeout=30):
    r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    r.raise_for_status()
    return r.text


def normalize_job(row, role, platform):
    return {
        "s.no": row.get("s.no", ""),
        "job_post_date": row.get("job_post_date", ""),
        "title": row.get("title", ""),
        "company": row.get("company", ""),
        "link": row.get("link", ""),
        "compensation": row.get("compensation", ""),
        "yoe": row.get("yoe", ""),
        "location": row.get("location", ""),
        "ambition_box_rating": row.get("ambition_box_rating", ""),
        "glassdoor_rating": row.get("glassdoor_rating", ""),
        "role": role,
        "platform": platform,
    }


def limit_10(rows):
    seen = set()
    out = []
    for row in rows:
        key = (row.get("title", ""), row.get("company", ""), row.get("link", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) == 10:
            break
    return out


def scrape_linkedin(role):
    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(role)}"
    html = safe_get(url)
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.select("div.base-card"):
        title = clean_text(card.select_one("h3").get_text()) if card.select_one("h3") else ""
        company = clean_text(card.select_one("h4").get_text()) if card.select_one("h4") else ""
        link_tag = card.select_one("a.base-card__full-link")
        link = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
        loc = clean_text(card.select_one(".job-search-card__location").get_text()) if card.select_one(".job-search-card__location") else ""
        date = clean_text(card.select_one("time").get_text()) if card.select_one("time") else ""
        salary = ""
        yoe = ""
        jobs.append({
            "job_post_date": date,
            "title": title,
            "company": company,
            "link": link,
            "compensation": salary,
            "yoe": yoe,
            "location": loc,
            "ambition_box_rating": "",
            "glassdoor_rating": "",
        })

    return limit_10(jobs)


def scrape_indeed(role):
    url = f"https://www.indeed.com/jobs?q={quote_plus(role)}"
    html = safe_get(url)
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.select("div.job_seen_beacon"):
        title_tag = card.select_one("h2 a")
        title = clean_text(title_tag.get_text()) if title_tag else ""
        link = "https://www.indeed.com" + title_tag["href"] if title_tag and title_tag.has_attr("href") else ""
        company = clean_text(card.select_one("[data-testid='company-name']").get_text()) if card.select_one("[data-testid='company-name']") else ""
        loc = clean_text(card.select_one("[data-testid='text-location']").get_text()) if card.select_one("[data-testid='text-location']") else ""
        salary = clean_text(card.select_one("[data-testid='attribute_snippet_testid']").get_text()) if card.select_one("[data-testid='attribute_snippet_testid']") else ""
        date = clean_text(card.select_one("span.date").get_text()) if card.select_one("span.date") else ""
        jobs.append({
            "job_post_date": date,
            "title": title,
            "company": company,
            "link": link,
            "compensation": salary,
            "yoe": "",
            "location": loc,
            "ambition_box_rating": "",
            "glassdoor_rating": "",
        })

    return limit_10(jobs)


def scrape_instahyre(role):
    url = f"https://www.instahyre.com/search-jobs/?q={quote_plus(role)}"
    html = safe_get(url)
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.select(".job-title"):
        pass

    return limit_10(jobs)


def scrape_hiringcafe(role):
    url = f"https://hiring.cafe/?q={quote_plus(role)}"
    html = safe_get(url)
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    return limit_10(jobs)


def scrape_naukri(role):
    url = f"https://www.naukri.com/{quote_plus(role).replace('%20', '-')}-jobs"
    html = safe_get(url)
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    return limit_10(jobs)


def collect_for_role(role):
    all_rows = []
    scrapers = {
        "linkedin": scrape_linkedin,
        "indeed": scrape_indeed,
        "instahyre": scrape_instahyre,
        "hiringcafe": scrape_hiringcafe,
        "naukri": scrape_naukri,
    }

    for platform, fn in scrapers.items():
        try:
            rows = fn(role)
            for i, row in enumerate(rows, start=1):
                row["s.no"] = i
                all_rows.append(normalize_job(row, role, platform))
        except Exception as e:
            print(f"{platform} failed for {role}: {e}")

    return all_rows


def save_csv(df, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False)
    return path


def main():
    combined = []

    for role in ROLES:
        rows = collect_for_role(role)
        df_role = pd.DataFrame(rows)
        if not df_role.empty:
            save_csv(df_role, f"{role.lower().replace(' ', '_')}.csv")
            combined.extend(rows)

    df_all = pd.DataFrame(combined)
    if not df_all.empty:
        save_csv(df_all, "all_jobs.csv")

    print("Done")


if __name__ == "__main__":
    main()