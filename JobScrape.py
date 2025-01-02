import requests
from bs4 import BeautifulSoup
import openai
import time
import json
import pypdf2   

# Set up OpenAI API
openai.api_key = "your_openai_api_key"

# Function to classify job categories
def classify_job(description):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Classify the job description into a category like 'Software Engineering,' 'Marketing,' or 'Data Science.'"},
            {"role": "user", "content": description},
        ]
    )
    return response["choices"][0]["message"]["content"].strip()

# Function to determine selectors for a job board using ChatGPT
def get_selectors(url):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Based on the HTML content of the given job board, determine the CSS selectors to extract job title, company, description, and application link."},
            {"role": "user", "content": f"HTML content from {url}"},
        ]
    )
    selectors = response["choices"][0]["message"]["content"].strip()
    try:
        return json.loads(selectors)
    except json.JSONDecodeError:
        print("Error decoding selectors. Please check the response.")
        return {}

# Function to determine relevant job categories based on user input and uploaded resume
def determine_categories(user_input, resume_text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Identify relevant job categories based on the user's input about their skills and experience as well as the provided resume text."},
            {"role": "user", "content": f"Input: {user_input}\nResume: {resume_text}"},
        ]
    )
    categories = response["choices"][0]["message"]["content"].strip()
    return categories.split(",")  # Assuming GPT returns a comma-separated list

# Function to extract text from an uploaded PDF resume
def extract_text_from_pdf(pdf_path):
    from PyPDF2 import PdfReader
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() for page in reader.pages)
    return text

# Function to generate a job boards list for selected categories
def generate_job_boards(categories):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Provide a list of popular job boards and company websites for each given job category."},
            {"role": "user", "content": f"Categories: {', '.join(categories)}"},
        ]
    )
    job_boards = response["choices"][0]["message"]["content"].strip()
    try:
        return json.loads(job_boards)  # Assuming GPT returns JSON-formatted job board data
    except json.JSONDecodeError:
        print("Error decoding job boards list. Please check the response.")
        return []

# Function to scrape job listings from a job board
def scrape_job_board(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            print(f"Failed to fetch URL: {url} | Status Code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Get selectors dynamically
        selectors = get_selectors(url)
        if not selectors:
            print(f"Failed to determine selectors for: {url}")
            return []

        # Extract job postings based on determined selectors
        jobs = []
        for job_card in soup.select(selectors.get("job_card", "div.job-card")):
            title = job_card.select_one(selectors.get("title", "h2.job-title")).text.strip()
            company = job_card.select_one(selectors.get("company", "div.company-name")).text.strip()
            description = job_card.select_one(selectors.get("description", "p.job-description")).text.strip()
            link = job_card.select_one(selectors.get("link", "a.apply-link"))["href"]

            category = classify_job(description)

            jobs.append({
                "title": title,
                "company": company,
                "description": description,
                "category": category,
                "link": link,
            })
        return jobs

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

# Function to save jobs to a JSON file
def save_jobs_to_file(jobs, filename):
    with open(filename, "w") as file:
        json.dump(jobs, file, indent=4)

# Function to generate a cover letter using GPT
def generate_cover_letter(job):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Generate a personalized cover letter for a job application based on the job title, company, and description."},
            {"role": "user", "content": f"Job Title: {job['title']}\nCompany: {job['company']}\nDescription: {job['description']}"},
        ]
    )
    return response["choices"][0]["message"]["content"].strip()

# Function to apply to jobs
def apply_to_job(job, resume_path, user_name, user_email):
    try:
        print(f"Applying to {job['title']} at {job['company']}...")

        # Generate a cover letter dynamically
        cover_letter = generate_cover_letter(job)

        # Simulated application process (customize this for actual implementation)
        response = requests.post(job["link"], files={
            "resume": open(resume_path, "rb")
        }, data={
            "name": user_name
            "email": user_email
            "cover_letter": cover_letter,
        })

        if response.status_code == 200:
            print(f"Successfully applied to {job['title']} at {job['company']}.")
        else:
            print(f"Failed to apply to {job['title']} at {job['company']} | Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error applying to {job['title']} at {job['company']}: {e}")

# Main function
def main():
    # Prompt user for input to determine relevant categories
    name = input( "First and Last Name?")
    email = input ("E-mail Address")
    user_input = input("Describe your skills and experience: ")
    resume_path = input("Enter the path to your resume (PDF format):")

    resume_text = extract_text_from_pdf(resume_path)
    categories = determine_categories(user_input, resume_text)
    print(f"Determined Categories: {categories}")

    # Generate job boards list based on categories
    job_boards = generate_job_boards(categories)
    print(f"Generated Job Boards: {job_boards}")

    all_jobs = []

    for url in job_boards:
        print(f"Scraping jobs from: {url}")
        jobs = scrape_job_board(url)
        all_jobs.extend(jobs)

        # Respect the site's rate limits
        time.sleep(5)

    # Save jobs to a file
    save_jobs_to_file(all_jobs, "scraped_jobs.json")
    print(f"Saved {len(all_jobs)} jobs to scraped_jobs.json")

    # Apply to jobs
    for job in all_jobs:
        apply_to_job(job, resume_path, name, email)

if __name__ == "__main__":
    main()
