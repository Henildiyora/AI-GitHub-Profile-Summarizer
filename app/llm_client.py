import os
import google.generativeai as genai
import json
from typing import Dict, Any

class LLMClient:
    """
    A client for interacting with the Google Gemini API.

    Handles the generation of candidate fit reports by formatting
    prompts and parsing JSON responses.

    Attributes:
        model: The configured Gemini GenerativeModel instance.
        SYSTEM_PROMPT (str): The master prompt defining the AI's role
            and the desired JSON output structure.
    """
    
    SYSTEM_PROMPT = """
        You are an expert technical recruiter and senior engineering manager.
        Your task is to analyze a candidate's GitHub profile AND their resume
        against a specific job description (JD).
        
        You must provide a ruthless, objective, and concise analysis by
        comparing the candidate's *claimed* experience (from the resume)
        with their *proven* experience (from their GitHub projects).

        The user will provide:
        1. A Job Description.
        2. The candidate's Resume text.
        3. The candidate's GitHub profile data (bio, top repos, READMEs).

        You MUST return a JSON object with the following exact structure:
        {
          "fit_score": <int, a percentage score from 0 to 100 representing how well the GitHub profile AND resume match the JD>,
          "summary": "<string, a 5-6 sentence summary of the candidate's fit. Highlight any matches or mismatches between the resume and GitHub.>",
          "role_strengths": [<string, a list of strengths specific to the JD, citing evidence from both resume and GitHub>],
          "role_weaknesses": [<string, a list of weaknesses or gaps based on the JD>],
          "red_flags": [<string, a list of any potential red flags (e.g., 'Claims 5 years of Python on resume but GitHub shows no Python projects')>],
          "interview_questions": [<string, a list of 3-5 sharp, targeted interview questions. (e.g., 'Your resume lists proficiency in AWS, but your GitHub projects don't seem to use it. Can you describe your experience there?')>]
    }
    """

    def __init__(self):
        """
        Initializes the LLMClient and configures the Gemini API.
        """
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json"
            )
            self.model = genai.GenerativeModel(
                'gemini-2.5-pro', # 'gemini-2.5-pro'
                generation_config=generation_config
            )
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.model = None

    async def generate_summary_from_github_data(
            self, 
            profile: dict, 
            repos: list, 
            readmes: dict,
            job_description: str,
            resume_text: str
        ) -> Dict[str, Any]:
        """
        Generates a structured JSON fit report using the Gemini API.

        Args:
            profile (dict): The candidate's GitHub profile data.
            repos (list): A list of the candidate's top repositories.
            readmes (dict): A dictionary mapping repo names to their README content.
            job_description (str): The job description to compare against.
            resume_text (str): The extracted text from the candidate's resume.

        Returns:
            Dict[str, Any]: A dictionary containing the structured fit report
                or an error message.
        """
        if not self.model:
            return {"error": "Gemini API is not configured. Please check your API key."}

        # 1. Construct the user's prompt (the context)
        github_context = f"GitHub Profile Bio: {profile.get('bio', 'Not provided.')}\n\n"
        github_context += "Top Repositories (by stars):\n"

        # Analyze top 5 repos
        for repo in repos[:5]: 
            repo_name = repo.get('name', 'N/A')
            description = repo.get('description', 'No description.')
            language = repo.get('language', 'N/A')
            stars = repo.get('stargazers_count', 0)
            readme = readmes.get(repo_name, "No README found.")

            github_context += f"\n---\n"
            github_context += f"Repo: {repo_name}\n"
            github_context += f"Primary Language: {language}\n"
            github_context += f"Stars: {stars}\n"
            github_context += f"Description: {description}\n"
            github_context += f"README Summary (first 1500 chars): {readme[:1500]}\n"
            github_context += f"---\n"

        user_message = f"""
          JOB DESCRIPTION
          {job_description}

          CANDIDATE RESUME DATA
          {resume_text}
          
          CANDIDATE GITHUB DATA
          {github_context}
          
          --- ANALYSIS ---
          Please generate the JSON fit report based on the rules.
        """

        # 2. Call the Gemini API
        try:
            response = await self.model.generate_content_async(
                [self.SYSTEM_PROMPT, user_message]
            )
            return json.loads(response.text)
            
        except Exception as e:
            print(f"An error occurred while calling the Gemini API: {e}")
            return {"error": f"Error: Could not generate a summary from the AI model. {e}"}