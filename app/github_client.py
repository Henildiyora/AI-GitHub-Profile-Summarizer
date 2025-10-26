import httpx
import os
from typing import List, Dict, Any, Optional
import base64

class GitHubClient:
    """
    A client for interacting with the GitHub REST API.

    Handles fetching user profiles, repositories, and README files.
    
    Attributes:
        GITHUB_API_URL (str): The base URL for the GitHub API.
        HEADERS (dict): Authentication headers using the GITHUB_TOKEN.
    """
    
    GITHUB_API_URL = "https://api.github.com"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the public profile information for a given GitHub username.

        Args:
            username (str): The GitHub username to query.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the user's
                profile data, or None if the user is not found.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.GITHUB_API_URL}/users/{username}", 
                    headers=self.HEADERS
                )
                response.raise_for_status()  
                return response.json()
            except httpx.HTTPStatusError:
                return None 
        
    async def get_user_repos(self, username: str) -> List[Dict[str, Any]]:
        """
        Fetches the repositories for a given GitHub username.

        Sorts repos by stars and returns the top 10.

        Args:
            username (str): The GitHub username to query.

        Returns:
            List[Dict[str, Any]]: A list of repository data dictionaries.
                Returns an empty list if an error occurs.
        """
        async with httpx.AsyncClient() as client:
            params = {'sort': 'stargazers_count', 'per_page': 10, 'direction': 'desc'}
            try:
                response = await client.get(
                    f"{self.GITHUB_API_URL}/users/{username}/repos", 
                    headers=self.HEADERS, 
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                return [] 

    async def get_readme_content(self, username: str, repo_name: str) -> Optional[str]:
        """
        Fetches the decoded content of the README.md file for a repository.

        Args:
            username (str): The GitHub username (owner) of the repo.
            repo_name (str): The name of the repository.

        Returns:
            Optional[str]: The decoded (UTF-8) text content of the
                README file, or None if not found.
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get the README metadata which includes download_url
                response = await client.get(
                    f"{self.GITHUB_API_URL}/repos/{username}/{repo_name}/readme", 
                    headers=self.HEADERS
                )
                response.raise_for_status()
                readme_data = response.json()
                
                # Fetch the raw content from the download_url
                content_response = await client.get(readme_data['download_url'])
                return content_response.text
            
            except (httpx.HTTPStatusError, KeyError):
                return None