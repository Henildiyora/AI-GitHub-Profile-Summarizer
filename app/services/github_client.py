import httpx
import os
from typing import List, Dict, Any, Optional

class GitHubClient:
    """
    A client for interacting with the GitHub REST API.
    """
    
    GITHUB_API_URL = "https://api.github.com"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Candidate-Screener/1.0",
    }
    
    if GITHUB_TOKEN:
        HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"
    else:
        print("Warning: GITHUB_TOKEN not set. Requests may be rate-limited or blocked.")

    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the public profile information for a given GitHub username.
        Args:
            username (str): GitHub username.
        Returns:
            Optional[Dict[str, Any]]: User profile data or None if not found.
        """
        url = f"{self.GITHUB_API_URL}/users/{username}"
        print(f"DEBUG: Fetching profile for '{username}' at {url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.HEADERS)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # --- NEW: Print the actual error message from GitHub ---
                print(f"GitHub API Error (Profile): {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                print(f"Unexpected Error (Profile): {e}")
                return None
        
    async def get_user_repos(self, username: str) -> List[Dict[str, Any]]:
        """
        Fetches the repositories for a given GitHub username.
        Args:
            username (str): GitHub username.
        Returns:
            List[Dict[str, Any]]: List of repository data.
        """
        url = f"{self.GITHUB_API_URL}/users/{username}/repos"
        params = {'sort': 'stargazers_count', 'per_page': 10, 'direction': 'desc'}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.HEADERS, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"GitHub API Error (Repos): {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                print(f"Unexpected Error (Repos): {e}")
                return []

    async def get_readme_content(self, username: str, repo_name: str) -> Optional[str]:
        """
        Fetches the decoded content of the README.md file for a repository.
        Args:
            username (str): GitHub username.
            repo_name (str): Repository name.
        Returns:
            Optional[str]: README content as a string, or None if not found.
        """
        url = f"{self.GITHUB_API_URL}/repos/{username}/{repo_name}/readme"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.HEADERS)
                response.raise_for_status()
                readme_data = response.json()
                download_url = readme_data.get('download_url')
                
                if not download_url:
                    return None

                # Fetch raw content
                content_response = await client.get(download_url)
                return content_response.text
            
            except (httpx.HTTPStatusError, KeyError):
                # 404s are common for missing READMEs, so we don't need to spam logs here
                return None
            except Exception as e:
                print(f"Unexpected Error (Readme): {e}")
                return None
                
    async def get_repo_details(self, username: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed information about a specific repository.
        Args:
            username (str): GitHub username.
            repo_name (str): Repository name.
        Returns:
            Optional[Dict[str, Any]]: Repository details or None if not found.
        """
        url = f"{self.GITHUB_API_URL}/repos/{username}/{repo_name}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.HEADERS)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"GitHub API Error (Repo Details): {e.response.status_code}")
                return None
            except Exception as e:
                 print(f"Unexpected Error (Repo Details): {e}")
                 return None

    async def get_repo_commits(self, username: str, repo_name: str, max_commits: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches recent commit history.
        Args:
            username (str): GitHub username.
            repo_name (str): Repository name.
            max_commits (int): Maximum number of commits to fetch.
        Returns:
            List[Dict[str, Any]]: List of commit data.
        """
        # First get default branch
        repo_info = await self.get_repo_details(username, repo_name)
        if not repo_info or 'default_branch' not in repo_info:
            return []
        default_branch = repo_info['default_branch']

        url = f"{self.GITHUB_API_URL}/repos/{username}/{repo_name}/commits"
        params = {'sha': default_branch, 'per_page': min(max_commits, 100)}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.HEADERS, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"GitHub API Error (Commits): {e.response.status_code}")
                return []
            except Exception as e:
                 print(f"Unexpected Error (Commits): {e}")
                 return []