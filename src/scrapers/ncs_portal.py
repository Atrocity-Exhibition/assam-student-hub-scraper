import requests
from typing import List, Dict, Any

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import clean_text, parse_date, classify_category

class NCSPortalScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="ncs_portal",
            institution="National Career Service",
            source="NCS Portal"
        )
        self.api_endpoints = [
            "https://www.ncs.gov.in/_vti_bin/NCS/JobSearch.svc/SearchJobs",
            "https://www.ncs.gov.in/api/jobs/search"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for api_url in self.api_endpoints:
            try:
                self.logger.info(f"Querying NCS API endpoint: {api_url}")
                payload = {
                    "StateName": "Assam",
                    "PageIndex": 1,
                    "PageSize": 20,
                    "SortBy": "PostedDate",
                    "SortOrder": "DESC"
                }
                # NCS API requests usually require JSON header
                headers = self.headers.copy()
                headers["Content-Type"] = "application/json"
                
                response = requests.post(
                    api_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=10, 
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Resolve differences in API return formats
                    jobs_list = (
                        data.get("d", {}).get("Jobs") or 
                        data.get("Jobs") or 
                        data.get("data") or 
                        []
                    )
                    
                    if jobs_list:
                        self.logger.info(f"NCS API successfully returned {len(jobs_list)} records")
                        for idx, job in enumerate(jobs_list[:15]):
                            title = clean_text(job.get("JobTitle") or job.get("Title") or "")
                            if not title:
                                continue
                            org = clean_text(job.get("OrganizationName") or job.get("Employer") or "NCS Employer")
                            jid = str(job.get("JobId") or job.get("Id") or idx + 1)
                            location = clean_text(job.get("Location") or "Assam")
                            salary = clean_text(job.get("SalaryRange") or "Varies")
                            
                            posted_str = job.get("PostedDate") or job.get("CreatedDate") or ""
                            posted_at = parse_date(posted_str)

                            items.append({
                                "title": title,
                                "description": f"{title} vacancy at {org}. Location: {location}. Salary: {salary}. Apply on National Career Service.",
                                "source_url": f"https://www.ncs.gov.in/job-seeker/Pages/JobDetail.aspx?JobId={jid}",
                                "category": "recruitment",
                                "content_type": "recruitment",
                                "posted_at": posted_at,
                                "tags": ["NCS", "Government Jobs", "Assam Recruitment"],
                                "metadata": {
                                    "job_id": jid,
                                    "employer": org,
                                    "salary": salary,
                                    "location": location
                                },
                                "raw_html": f"NCS API Item: {title} | Employer: {org}"
                            })
                        
                        return items
            except Exception as e:
                self.logger.warning(f"Error checking NCS endpoint {api_url}: {e}")

        # Fallback browse card if API call fails
        self.logger.info("NCS API endpoints returned nothing. Registering default NCS Browse Card.")
        items.append({
            "title": "Browse All Assam Jobs — NCS Portal",
            "description": "National Career Service portal lists government, PSU, and private jobs across Assam. Free registration is required to apply.",
            "source_url": "https://www.ncs.gov.in/jobs-in-assam",
            "category": "recruitment",
            "content_type": "recruitment",
            "posted_at": None,
            "tags": ["NCS Portal", "Assam Recruitment", "Job Search"],
            "metadata": {
                "employer": "National Career Service",
                "location": "Assam, India"
            },
            "raw_html": "NCS Fallback Link to portal search"
        })

        return items
