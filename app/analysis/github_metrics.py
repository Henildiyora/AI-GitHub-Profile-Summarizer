from typing import List, Dict, Any

def calculate_complexity_score(repos: List[Dict[str, Any]]) -> int:
    """
    Analyzes repo metadata to determine engineering complexity.
    Args:
        repos (List[Dict[str, Any]]): List of repository metadata dictionaries.
    Returns:
        int: Complexity score from 0 to 100.
    """
    if not repos:
        return 0

    total_score = 0
    valid_repos = 0

    for repo in repos:
        repo_score = 0
        
        # 1. Size (heuristic: larger codebases are more complex)
        size_kb = repo.get('size', 0)
        if size_kb > 10000: repo_score += 20 # > 10MB
        elif size_kb > 1000: repo_score += 10 # > 1MB
        
        # 2. Stars (Social Proof/Utility)
        stars = repo.get('stargazers_count', 0)
        if stars > 100: repo_score += 20
        elif stars > 10: repo_score += 10
        
        # 3. Language (Primary language exists?)
        if repo.get('language'):
            repo_score += 10
            
        # 4. Description exists? (Documentation effort)
        if repo.get('description'):
            repo_score += 10
            
        # 5. Has Wiki/Pages/Issues (Community/Docs)
        if repo.get('has_wiki') or repo.get('has_pages'):
            repo_score += 10

        # 6. Not a Fork (Originality)
        if not repo.get('fork'):
            repo_score += 30
        
        total_score += repo_score
        valid_repos += 1

    if valid_repos == 0:
        return 0

    # Average score across top repos, clamped at 100
    avg_score = int(total_score / valid_repos)
    return min(100, avg_score)