from typing import Set, Tuple, List
import re

def extract_domain_keywords(text: str) -> Set[str]:
    """
    Simple extraction of capitalized words that aren't at start of sentences.
    (A naive but effective way to find proper nouns/domains without big NLP models)

    Args:
        text (str): Input text from which to extract domain keywords.
    Returns:
        Set[str]: A set of extracted domain keywords.
    """
    # Look for words starting with Capital letter inside sentences
    candidates = re.findall(r'(?<!^)(?<!\. )[A-Z][a-z]+', text)
    return set(candidates)

def calculate_domain_relevance(jd_text: str, candidate_text: str) -> int:
    """
    Checks overlap of domain-specific capitalized terms.

    Args:
        jd_text (str): Job description text.
        candidate_text (str): Candidate profile text.
    Returns:
        int: Relevance score from 0 to 100 based on domain keyword overlap.
    """
    if not jd_text or not candidate_text:
        return 0
        
    # We treat the JD as the source of truth for domain keywords
    # We focus on words that appear multiple times to filter noise
    jd_words = re.findall(r'\b\w+\b', jd_text.lower())
    word_counts = {}
    for w in jd_words:
        if len(w) > 4: # Skip small words
            word_counts[w] = word_counts.get(w, 0) + 1
            
    # Get top 20 frequent words from JD (proxy for domain topics)
    top_jd_keywords = sorted(word_counts, key=word_counts.get, reverse=True)[:20]
    
    if not top_jd_keywords:
        return 0
        
    candidate_text_lower = candidate_text.lower()
    matches = 0
    for keyword in top_jd_keywords:
        if keyword in candidate_text_lower:
            matches += 1
            
    # Score: Percentage of top JD keywords found in candidate profile
    score = int((matches / len(top_jd_keywords)) * 100)
    # Boost score slightly because matching ALL keywords is rare
    score = min(100, int(score * 1.5))
    
    return score