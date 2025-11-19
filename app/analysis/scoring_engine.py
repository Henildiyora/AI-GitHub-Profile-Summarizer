from typing import Dict, Any, List

def calculate_hybrid_score(
    tech_score: int,
    exp_score: int,
    complexity_score: int,
    domain_score: int,
    llm_adjustment: int = 0
) -> Dict[str, Any]:
    """
    Aggregates sub-scores using the Weighted Formula (Plan 2).
    Weights: Tech(40%), Exp(25%), Complexity(20%), Domain(15%)

    Args:
        tech_score (int): Technical Skills Score (0-100).
        exp_score (int): Experience Level Score (0-100).
        complexity_score (int): Project Complexity Score (0-100).
        domain_score (int): Domain Relevance Score (0-100).
        llm_adjustment (int): Qualitative adjustment from LLM (-20 to +20).
    Returns:
        Dict[str, Any]: Dictionary with base_score, final_score, confidence_level, confidence_percentage
    """
    
    # Calculate Base Score (Quantitative)
    base_score = (
        (tech_score * 0.40) +
        (exp_score * 0.25) +
        (complexity_score * 0.20) +
        (domain_score * 0.15)
    )
    
    # Apply Qualitative Adjustment (from Gemini)
    # adjustment is +/- 20
    final_score = base_score + llm_adjustment
    
    # Clamp and Round
    final_score = max(0, min(100, final_score))
    
    # Calculate Confidence
    # High confidence if base score and final score are close
    # Low confidence if AI drastically changed the math result
    variance = abs(final_score - base_score)
    if variance < 10:
        confidence = "High"
        conf_percent = 0.95
    elif variance < 20:
        confidence = "Medium"
        conf_percent = 0.75
    else:
        confidence = "Low"
        conf_percent = 0.50

    return {
        "base_score": int(base_score),
        "final_score": int(final_score),
        "confidence_level": confidence,
        "confidence_percentage": conf_percent
    }

def generate_audit_trail(
    scores: Dict[str, int], 
    evidence: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Creates the Explainable AI (XAI) breakdown JSON.

    Args:
        scores (Dict[str, int]): Dictionary of individual scores.
        evidence (Dict[str, List[str]]): Evidence lists for strengths, weaknesses, etc.
    Returns:
        Dict[str, Any]: Audit trail with math breakdown and evidence log.
    """
    return {
        "math_breakdown": {
            "technical_skills": f"{scores['tech']}/100 (Weight: 40%)",
            "experience_level": f"{scores['exp']}/100 (Weight: 25%)",
            "project_complexity": f"{scores['comp']}/100 (Weight: 20%)",
            "domain_relevance": f"{scores['dom']}/100 (Weight: 15%)",
        },
        "evidence_log": evidence
    }