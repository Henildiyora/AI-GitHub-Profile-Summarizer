import httpx
import os
from typing import List, Dict, Any, Optional

# Get the tockens from env file
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Set up headers for authentication. This increases the rate limit.
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {GITHUB_TOKEN}"
}

async def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the public profile information for a given GitHub username.
    Uses an async HTTP client for non-blocking network calls.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GITHUB_API_URL}/users/{username}", headers=HEADERS)
            response.raise_for_status()  
            return response.json()
        except httpx.HTTPStatusError:
            return None 
        
async def get_user_repos(username: str) -> List[Dict[str,any]]:
    """
    Fetches the repositories for a given GitHub username.
    Sorts repos by stars and returns the top ones.
    """
    async with httpx.AsyncClient() as client:
        # Fetch repos, sort by stars, get the top 10
        params = {'sort': 'stargazers_count', 'per_page': 10, 'direction': 'desc'}
        try:
            response = await client.get(f"{GITHUB_API_URL}/users/{username}/repos", headers=HEADERS, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return [] 

async def get_readme_content(username: str, repo_name: str) -> Optional[str]:
    """
    Fetches the content of the README.md file for a specific repository.
    The content is returned as a base64 encoded string, so we need to decode it.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GITHUB_API_URL}/repos/{username}/{repo_name}/readme", headers=HEADERS)
            response.raise_for_status()
            # The content is in base64, so we need to decode it
            readme_data = response.json()
            import base64
            # Use httpx to get the content from the download_url to handle large files
            content_response = await client.get(readme_data['download_url'])
            return content_response.text
        except (httpx.HTTPStatusError, KeyError):
            # If README doesn't exist or there's an error, return None
            return None
