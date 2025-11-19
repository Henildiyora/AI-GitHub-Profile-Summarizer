import re
from typing import List, Set, Tuple

# A basic set of common tech keywords to help extraction accuracy
# In a real prod env, this would be a database or an NLP model (Spacy)
COMMON_SKILLS = {
    "python", "java", "c++", "javascript", "typescript", "react", "angular", "vue",
    "fastapi", "django", "flask", "spring", "node.js", "express",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn",
    "git", "ci/cd", "linux", "agile", "scrum", "rest api", "graphql"
}

def extract_skills(text: str) -> Set[str]:
    """
    Extracts unique skills from text using a keyword list and basic cleanup.

    Args:
        text (str): Input text from which to extract skills.
    Returns:
        Set[str]: A set of extracted skill keywords.
    """
    if not text:
        return set()
    
    text = text.lower()
    # Replace non-alphanumeric chars (except + and .) with space
    text = re.sub(r'[^a-z0-9+.]', ' ', text)
    
    found_skills = set()
    
    # check for multi-word skills first (simple implementation)
    for skill in ["machine learning", "deep learning", "ci/cd", "rest api"]:
        if skill in text:
            found_skills.add(skill)
            
    # Check individual words
    words = set(text.split())
    for word in words:
        if word in COMMON_SKILLS:
            found_skills.add(word)
            
    return found_skills

def calculate_technical_match(candidate_text: str, jd_text: str) -> Tuple[int, List[str], List[str]]:
    """
    Returns: (Score 0-100, Matches List, Missing List)
    Calculates technical skills match score based on extracted skills.
    Args:
        candidate_text (str): Candidate profile text.
        jd_text (str): Job description text.
    Returns:
        Tuple[int, List[str], List[str]]: Match score, list of matched skills, list of missing skills.
    """
    jd_skills = extract_skills(jd_text)
    candidate_skills = extract_skills(candidate_text)
    
    if not jd_skills:
        return 0, [], []

    matches = jd_skills.intersection(candidate_skills)
    missing = jd_skills.difference(candidate_skills)
    
    # Score calculation: (Matches / Required) * 100
    score = int((len(matches) / len(jd_skills)) * 100)
    
    return score, list(matches), list(missing)