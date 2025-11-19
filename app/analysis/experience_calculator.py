import re
from typing import Dict, Any

def extract_years_of_experience(text: str) -> int:
    """
    Regex to find patterns like '5 years experience', '3+ years', '2015-2020'

    Args:
        text (str): Input text to search for years of experience.
    Returns:
        int: Extracted years of experience, or 0 if none found.
    """
    if not text:
        return 0
        
    text = text.lower()
    
    # Look for "X+ years" or "X years"
    years_regex = r'(\d+)\+?\s*years?'
    matches = re.findall(years_regex, text)
    
    if matches:
        # Get the maximum number mentioned (heuristic)
        # e.g., "10 years exp" is better than "2 years"
        try:
            years = [int(m) for m in matches]
            return max(years)
        except:
            pass
            
    return 0

def calculate_experience_score(resume_text: str, jd_text: str) -> int:
    """
    Compares found years vs required years (heuristic).

    Args:
        resume_text (str): Candidate resume text.
        jd_text (str): Job description text.
    Returns:
        int: Experience score from 0 to 100.
    """
    candidate_years = extract_years_of_experience(resume_text)
    required_years = extract_years_of_experience(jd_text)
    
    # Default to 2 years if not found in JD
    if required_years == 0:
        required_years = 2
        
    if candidate_years == 0:
        return 20 # Baseline points for having a resume
        
    if candidate_years >= required_years:
        return 100
    
    # Partial credit
    return int((candidate_years / required_years) * 100)