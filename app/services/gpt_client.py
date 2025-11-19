import os
import openai
import json
from typing import Dict, Any, Optional

from app.services.llm_client import SYSTEM_PROMPT 

class GPTClient:
    """
    A client for interacting with the OpenAI API (GPT models).
    """

    def __init__(self):
        """
        Initializes the GPTClient and configures the OpenAI API.
        """
        try:
            # Use the Async client for FastAPI
            self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-3.5-turbo" # gpt-3.5-turbo if 4o isn't on free tier
        except Exception as e:
            print(f"Error configuring OpenAI API: {e}")
            self.client = None

    async def generate_summary_from_github_data(
            self, 
            profile: dict, 
            repos: list, 
            readmes: dict,
            job_description: str,
            resume_text: str,
            linkedin_text: Optional[str] = None
        ) -> Dict[str, Any]:
        """
        Generates a structured JSON fit report using the OpenAI API.
        Args:
            profile (dict): GitHub user profile data.
            repos (list): List of GitHub repository data.
            readmes (dict): Dictionary of README contents keyed by repo name.
            job_description (str): Job description text.
            resume_text (str): Candidate resume text.
            linkedin_text (Optional[str]): Candidate LinkedIn profile text.
        Returns:
            Dict[str, Any]: Generated fit report as a dictionary.
        """
        if not self.client:
            return {"error": "OpenAI API is not configured. Check your OPENAI_API_KEY."}

        # Build the user message
        github_context = f"GitHub Profile Bio: {profile.get('bio', 'Not provided.')}\n\n"
        github_context += "Top Repositories (by stars):\n"
        for repo in repos[:5]:
            repo_name = repo.get('name', 'N/A')
            description = repo.get('description', 'No description.')
            language = repo.get('language', 'N/A')
            stars = repo.get('stargazers_count', 0)
            readme = readmes.get(repo_name, "No README found.")
            github_context += f"\n---\nRepo: {repo_name}\nPrimary Language: {language}\nStars: {stars}\nDescription: {description}\nREADME Summary (first 1500 chars): {readme[:1500]}\n---\n"
        
        user_message_segments = [
            "--- JOB DESCRIPTION ---", job_description,
            "--- CANDIDATE RESUME TEXT ---", resume_text
        ]
        if linkedin_text:
            user_message_segments.extend(["--- CANDIDATE LINKEDIN TEXT ---", linkedin_text])
        user_message_segments.extend([
            "--- CANDIDATE GITHUB DATA ---", github_context,
            "--- ANALYSIS ---", "Please generate the JSON fit report based on the rules. Start your response with {."
        ])
        user_message = "\n\n".join(user_message_segments)

        # Call the OpenAI API
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
            )
            report = json.loads(response.choices[0].message.content)
            report['model_source'] = 'OpenAI (GPT-3.5 turbo)'
            return report
            
        except Exception as e:
            print(f"An error occurred while calling the OpenAI API: {e}")
            return {"error": f"Error: Could not generate a summary from OpenAI. {e}"}