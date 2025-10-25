import asyncio
import os
from dotenv import load_dotenv
import pandas
import json
from datetime import datetime
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from playwright.async_api import async_playwright

date_map = {10:"Oct", 11:"Nov", 12: "Dec"}
today = datetime.today()


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

async def scrape_job_page(url: str):
    """Scrape a single job URL using Playwright"""
    async with async_playwright() as p:
        if url.rfind("workday") != -1:
            browser = await p.chromium.launch(headless=False)
        else:
            browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle',timeout=30000)
            await page.wait_for_timeout(200)
            html_content = await page.content()
            return html_content
        finally:
            await browser.close()

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

async def main():
    # read the job urls from txt file
    with open('job_links.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print("Processing the urls from the file")
    rows = []
    for url in urls:
        try:
            content = await scrape_job_page(url)
            job_info = extract_job_info(content)
            try:
                data = json.loads(str(job_info))
                month = today.month
                day = today.day
                job_applied = f"{date_map.get(month)} {day}"
                rows.append([
                    data.get("title", ""),
                    data.get("companyName", ""),
                    data.get("location", ""),
                    job_applied,
                    data.get("description", ""),
                    url
                ])  
            except Exception as ex:
                print(f"JSON parse error: {ex}")
        except Exception as e:
            print(f"Error occured {e}")
    
    df = pandas.DataFrame(rows, columns=["Title", "Company Name", "Location", "Applied Date", "Description", "Job Link"])
    df.to_excel("extracted_jobs.xlsx", index=False)

if __name__ == "__main__":
    asyncio.run(main())
