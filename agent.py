import os
from dotenv import load_dotenv
import pandas
import json
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from playwright.sync_api import sync_playwright


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

extraction_prompt = PromptTemplate.from_template(
    """Extract the following information from this job posting and format it as JSON:
    {{
        "title": "job title here",
        "companyName": "company name here",
        "location": "location here",
        "description": "full job description on the page"
    }}
    
    Job Content: {content}
    """
)

def scrape_job_page(url: str):
    """Scrape a single job URL using Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until='networkidle',timeout=30000)
            page.wait_for_timeout(200)
            html_content = page.content()
            return html_content
        finally:
            browser.close()

def extract_job_info(content):
    """Extract structured job info using Gemini"""
    chain = extraction_prompt | llm
    result = chain.invoke({"content": content[:10000]})

    response = result.content.strip()
    if response.startswith("```json"):
        response = response[7:]  # Remove ```json
    if response.startswith("```"):
        response = response[3:]  # Remove ```
    if response.endswith("```"):
        response = response[:-3]  
    return response.strip()

def main():
    # read the job urls from txt file

    with open('job_links.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print("Processing the urls from the file")
    rows = []
    for url in urls:
        try:
            content = scrape_job_page(url)
            job_info = extract_job_info(content)
            try:
                data = json.loads(str(job_info))
                rows.append([
                    data.get("title", ""),
                    data.get("companyName", ""),
                    data.get("location", ""),
                    data.get("description", ""),
                    url
                ])  
            except Exception as ex:
                print(f"JSON parse error: {ex}")
        except Exception as e:
            print(f"Error occured {e}")
    
    df = pandas.DataFrame(rows, columns=["Title", "Company Name", "Location", "Description", "Job Link"])
    df.to_excel("extracted_jobs.xlsx", index=False)

if __name__ == "__main__":
    main()
