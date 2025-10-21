import os
import google.generativeai as genai
import json
from typing import Dict, Any

# Configure the Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    generation_config = genai.GenerationConfig(response_mime_type="application/json")
    model = genai.GenerativeModel(
        'gemini-2.5-pro',
        generation_config=generation_config
    )
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

SYSTEM_PROMPT = """
You are a Staff-level Software Engineer and expert technical recruiter. Your task is to analyze a developer's GitHub profile data and provide a professional, in-depth technical assessment for a non-technical hiring manager.

The user will provide a context string containing the developer's bio, top repositories, and README excerpts.

You MUST return your analysis in a valid JSON object with the following exact structure:
{
  "summary": "A 2-3 sentence executive summary of the developer's profile, including their inferred experience level (e.g., Junior, Mid-level, Senior) and primary domain (e.g., Frontend, Backend, Data Science, DevOps).",
  "technologies": [
    "A list of key technologies, frameworks, and programming languages explicitly mentioned or heavily implied in the projects.",
    "e.g., Python (FastAPI)",
    "e.g., PyTorch",
    "e.g., React (Next.js)",
    "e.g., AWS (S3, EC2)"
  ],
  "strengths": [
    "A bullet-point list of 2-3 notable strengths.",
    "Focus on project quality, documentation, use of modern tools, or clear focus in a high-demand area."
  ],
  "growth_areas": [
    "A bullet-point list of 1-2 potential gaps or areas for growth, framed constructively.",
    "e.g., 'Lack of visible unit testing in projects.'",
    "e.g., 'Projects appear to be solo-efforts; no visible open-source collaboration.'",
    "e.g., 'Focus is heavily on scripting; could benefit from building a full-stack application.'"
  ],
  "interview_questions": [
    "A list of 2-3 specific, non-generic interview questions a non-technical person could ask, based on their projects.",
    "e.g., 'Can you explain the trade-offs of using Streamlit for your 'Face-Mask-Detector' project?'",
    "e.g., 'What was the most challenging part of integrating the Twitter API for your sentiment analysis tool?'"
  ]
}
"""

async def generate_summary_from_github_data(profile: dict, repos: list, readmes: dict) -> Dict[str, Any]:
    """
    Generates a structured JSON summary using the Gemini API.
    """
    if not model:
        return {"error": "Gemini API is not configured. Please check your API key."}

    # 1. Construct the user's prompt (the context)
    context = f"GitHub Profile Bio: {profile.get('bio', 'Not provided.')}\n\n"
    context += "Top Repositories (by stars):\n"

    for repo in repos[:5]: # Analyze top 5 repos
        repo_name = repo.get('name', 'N/A')
        description = repo.get('description', 'No description.')
        language = repo.get('language', 'N/A')
        stars = repo.get('stargazers_count', 0)
        readme = readmes.get(repo_name, "No README found.")

        context += f"\n---\n"
        context += f"Repo: {repo_name}\n"
        context += f"Primary Language: {language}\n"
        context += f"Stars: {stars}\n"
        context += f"Description: {description}\n"
        context += f"README Summary (first 1500 chars): {readme[:1500]}\n"
        context += f"---\n"

    # 2. Call the Gemini API with the two-part prompt
    try:
        # We send the system prompt (our instructions) and the user prompt (the data)
        response = await model.generate_content_async([SYSTEM_PROMPT, context])
        
        # Parse the JSON response text
        return json.loads(response.text)
        
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return {"error": f"Error: Could not generate a summary from the AI model. {e}"}