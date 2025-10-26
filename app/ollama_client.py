import ollama
import json
from typing import Dict, Any, Optional

from app.llm_client import SYSTEM_PROMPT 

class OllamaClient:
    """
    A client for interacting with a local Ollama instance.
    """

    def __init__(self):
        """
        Initializes the OllamaClient.
        """
        try:
            # Connects to http://localhost:11434 by default
            self.client = ollama.AsyncClient()
            self.model = "mistral:latest"
        except Exception as e:
            print(f"Error configuring Ollama client: {e}")
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
        Generates a structured JSON fit report using the local Ollama API.
        """
        if not self.client:
            return {"error": "Ollama client is not configured."}

        # 1. Build the user message (same logic as llm_client.py)
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
        
        try:
            response = await self.client.chat(
                model=self.model,
                format="json", 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
            )
            report = json.loads(response['message']['content'])
            report['model_source'] = 'Ollama (Mistral)' 
            return report
            
        except Exception as e:
            if "connection refused" in str(e).lower():
                 return {"error": "Ollama is not running. Please start the Ollama application on your computer."}
            print(f"An error occurred while calling the Ollama API: {e}")
            return {"error": f"Error: Could not generate a summary from Ollama. {e}"}