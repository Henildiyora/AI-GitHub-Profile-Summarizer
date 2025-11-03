# AI GitHub Profile & Resume Analyzer

This project is a web-based tool that analyzes a software developer's GitHub profile and resume against a specific job description to generate a comprehensive "Candidate Fit Report." It is designed to help recruiters and hiring managers quickly assess a candidate's technical skills, experience, and potential fit for a role.

## Features

*   **Web-Based Dashboard:** An intuitive single-page application to manage projects and analyze candidates.
*   **Project-Based Analysis:** Create "projects" for different job roles, each with its own job description.
*   **Multi-faceted Candidate Data:** Analyzes data from:
    *   GitHub user profiles
    *   Public repository details
    *   README content from top repositories
    *   Uploaded PDF resumes
    *   Uploaded PDF LinkedIn profiles (optional)
*   **AI-Powered Reporting:** Uses Large Language Models (LLMs) like Google's Gemini to generate a detailed report containing:
    *   **Fit Score:** A percentage indicating the candidate's match to the job description.
    *   **Overall Summary:** A narrative summary of the candidate's profile.
    *   **Role Strengths & Weaknesses:** Bulleted lists highlighting key alignments and gaps.
    *   **Red Flags:** Potential concerns or areas for further investigation.
    *   **Suggested Interview Questions:** Contextual questions based on the analysis.
*   **Extensible LLM Support:** Can be extended to use various models (includes commented-out examples for Ollama and OpenAI's GPT).
*   **Database & Caching:** Stores project/candidate data in a local SQLite database and caches analysis results to speed up repeated requests.

## How It Works

The application is built with a **FastAPI** backend and a vanilla **HTML/CSS/JavaScript** frontend.

1.  **Data Ingestion:** The user provides a GitHub username and uploads a resume via the web interface for a specific project.
2.  **GitHub Scraping:** The backend fetches the user's profile information and repository details from the GitHub API. It also retrieves the content of the README files from the user's top 5 most-starred repositories.
3.  **Document Parsing:** The uploaded PDF resume (and optional LinkedIn profile) is parsed to extract its text content.
4.  **LLM Prompting:** A detailed prompt is constructed containing the job description, the candidate's GitHub data, and the text from their documents.
5.  **Report Generation:** This prompt is sent to the configured LLM (e.g., Gemini). The model analyzes all the information and returns a structured JSON object representing the fit report.
6.  **Data Persistence:** The generated report is saved as a JSON file in the `generated_reports` directory. Metadata about the candidate and their association with the project is stored in a local SQLite database.

## Technologies Used

*   **Backend:** Python, FastAPI, SQLModel, Pydantic
*   **Frontend:** HTML, Tailwind CSS, Vanilla JavaScript
*   **LLM Integration:** Google Gemini (via `LLMClient`), with code structured for easy integration of others like Ollama or OpenAI.
*   **API Interaction:** `httpx` for asynchronous API calls to GitHub.
*   **PDF Parsing:** `pypdf`

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AI_GitHub_Profile_Summarizer
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv github_summarizer_venv
    source github_summarizer_venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a file named `.env` in the root directory of the project. This file should contain your API keys.

    ```env
    # .env file
    GITHUB_TOKEN="your_github_personal_access_token"
    GEMINI_API_KEY="your_gemini_api_key"
    ```

5.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```
    The application will be available at `http://127.0.0.1:8000`.

## Usage

1.  Open your web browser and navigate to `http://127.0.0.1:8000`.
2.  Click the "**New Project**" button.
3.  Enter a **Project Name** and paste the full **Job Description** into the text area, then click "**Save Project**".
4.  Your new project will appear in the left-hand sidebar. Click on it to select it.
5.  In the main content area, enter the candidate's **GitHub Username** and upload their **Resume (PDF)**. You can also optionally upload a PDF of their LinkedIn profile.
6.  Click the "**Analyze & Add Candidate**" button.
7.  The system will process the data and display the Candidate Fit Report on the screen. Previously analyzed candidates for the selected project will be listed below the input form.

## Example Output

Here is a sample `report.json` generated for a candidate:

```json
{
    "fit_score": 75,
    "summary": "The candidate is a strong technical fit for the prototyping aspects of this role. Their resume claims of proficiency in Python, PyTorch, LangChain, and Computer Vision are well-substantiated by their GitHub projects, particularly the 'Multi_Modal_Image_Analysis_Dashboard' and 'TwitterSentimentDashboard'. These projects demonstrate a clear ability to build functional AI applications. However, there is a significant domain mismatch. The candidate's entire professional experience and personal project portfolio are rooted in industrial IoT and general data analysis, showing no demonstrated interest or experience in the creative, real-time, and event-focused applications central to the job description. While technically capable, their passion for the specific mission of this role is unproven.",
    "role_strengths": [
        "Strong, Proven Python & AI Framework Skills: Resume lists PyTorch, Hugging Face, and LangChain, which is directly validated by GitHub projects like 'Multi_Modal_Image_Analysis_Dashboard' that use these exact technologies.",
        "Demonstrated Prototyping Ability: Built several end-to-end applications with interactive dashboards (Streamlit, Plotly) as seen on GitHub, aligning perfectly with the need to 'Prototype creative AI tools' and 'present creative demos'.",
        "Solid Foundation in CV and NLP: Projects in object detection, sentiment analysis, and image captioning provide the core technical skills needed for tasks like 'emotion detection' and 'recap-generation'.",
        "Experience with Modern AI Stacks: The 'AI-Powered Nutritional Label Analyzer' project on the resume claims use of serverless architecture, OCR, and LLMs (LangChain), showing comfort with contemporary AI development patterns."
    ],
    "role_weaknesses": [
        "Lack of Domain-Specific Experience: All listed experience is in industrial IoT and predictive maintenance, which has no direct relevance to live events, music technology, or creative media.",
        "No Demonstrated Passion for the Mission: The profile is entirely technical, lacking any mention of interest in art, emotion, or shared human experiences, a key trait listed in the 'Ideal Background'.",
        "No Evidence of Real-Time Systems Experience: The job requires tools for 'live-event use' and 'real-time' analysis. The candidate's projects analyze static datasets or single-file uploads, not continuous data streams.",
        "Zero Audio or Music Tech Background: The profile shows no experience with audio processing or music technology, a component mentioned in the job description."
    ],
    "red_flags": [
        "Significant Domain Mismatch: Candidate's entire portfolio is focused on analytical/industrial ML, indicating a potential lack of genuine interest in the creative and emotion-centric mission of this specific role.",
        "Unverified Cloud Deployment Claims: Resume heavily lists AWS deployment skills (EC2, Elastic Beanstalk, SageMaker), but public GitHub projects are primarily local dashboards with no visible cloud architecture or Infrastructure-as-Code to substantiate these production-level claims."
    ],
    "interview_questions": [
        "Your projects in sentiment analysis and computer vision are strong. How would you adapt these skills to prototype a system for 'real-time emotion detection' from live crowd footage, and what new technical challenges would you anticipate?",
        "This role is deeply focused on the intersection of technology, art, and human emotion. Can you describe a time you've explored this intersection, either in a project not on your resume or through personal interest?",
        "Your resume lists deploying a Flask API on AWS Elastic Beanstalk. Can you walk me through the architecture you used and describe how you managed the application's dependencies and environment from development to production?",
        "The role involves experimenting with AI-driven audio and lighting. Given your background is primarily in vision and text, how would you approach getting up to speed on processing audio data to, for example, visualize a crowd's energy?"
    ]
}
```
