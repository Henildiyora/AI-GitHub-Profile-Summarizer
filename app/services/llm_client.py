import os
import google.generativeai as genai
import json
from typing import Dict, Any, Optional, List
from app.constants import SYSTEM_PROMPT

class LLMClient:
    def __init__(self):
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-2.5-pro', generation_config={"response_mime_type": "application/json"})
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.model = None

    async def generate_summary_from_github_data(
            self, 
            profile: dict, 
            repos: list, 
            readmes: dict,
            job_description: str,
            resume_text: str,
            linkedin_text: Optional[str] = None,
            quantitative_scores: Optional[Dict[str, Any]] = None # <-- NEW INPUT
        ) -> Dict[str, Any]:

        """
        Generates a structured JSON fit report using the Gemini API.
        Args:
            profile (dict): GitHub user profile data.
            repos (list): List of GitHub repository data.
            readmes (dict): Dictionary of README contents keyed by repo name.
            job_description (str): Job description text.
            resume_text (str): Candidate resume text.
            linkedin_text (Optional[str]): Candidate LinkedIn profile text.
            quantitative_scores (Optional[Dict[str, Any]]): Pre-calculated quantitative scores.
        Returns:
            Dict[str, Any]: Generated fit report as a dictionary.
        """
        
        if not self.model: return {"error": "Gemini API is not configured."}

        # 1. Build GitHub Context
        github_context = f"Bio: {profile.get('bio', 'N/A')}, Public Repos: {profile.get('public_repos', 0)}\n"
        for repo in repos[:5]:
            github_context += f"- Repo: {repo.get('name')} | Lang: {repo.get('language')} | Stars: {repo.get('stargazers_count')} | Desc: {repo.get('description')}\n"

        # 2. Build User Message
        user_message_segments = [
            f"--- JOB DESCRIPTION ---\n{job_description}",
            f"--- RESUME ---\n{resume_text}",
            f"--- LINKEDIN ---\n{linkedin_text or 'Not provided'}",
            f"--- GITHUB SUMMARY ---\n{github_context}"
        ]

        # --- Pass the Math to the AI ---
        if quantitative_scores:
            user_message_segments.append(f"--- QUANTITATIVE SCORES ---\n{json.dumps(quantitative_scores, indent=2)}")
            user_message_segments.append("\nTASK: Analyze the evidence above. Does the candidate deserve a higher or lower score than the math suggests? Provide your 'llm_adjustment' and evidence breakdown.")
        
        user_message = "\n\n".join(user_message_segments)

        # 3. Call AI
        try:
            response = await self.model.generate_content_async([SYSTEM_PROMPT, user_message])
            return json.loads(response.text)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {"error": f"AI analysis failed: {e}"}