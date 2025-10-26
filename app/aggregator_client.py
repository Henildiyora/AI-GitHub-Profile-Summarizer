import os
import google.generativeai as genai
import json
from typing import Dict, Any, List

AGGREGATOR_SYSTEM_PROMPT = """
You are a world-class hiring manager and senior technical lead.
Your job is to synthesize multiple AI-generated reports about a job candidate
into one single, authoritative JSON report.

The user will provide a list of JSON reports.
You must analyze all of them and produce a single, final JSON object
that represents a consensus.

- For "fit_score", calculate the average.
- For "summary", write a new, synthesized summary based on all reports.
- For "role_strengths", "role_weaknesses", and "red_flags",
  combine the lists, remove duplicates, and consolidate similar points.
- For "interview_questions", select the top 5 most insightful
  and unique questions from all reports.

The final JSON structure MUST match this:
{
  "fit_score": <int>,
  "summary": "<string>",
  "role_strengths": [<string>],
  "role_weaknesses": [<string>],
  "red_flags": [<string>],
  "interview_questions": [<string>]
}
"""


class AggregatorClient:
    """
    Synthesizes multiple LLM reports into a single, final report
    using a "meta-analysis" LLM call.
    """
    def __init__(self):
        """
        Initializes the AggregatorClient, using Gemini as the synthesizer.
        """
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json"
            )
            self.model = genai.GenerativeModel(
                'gemini-2.5-pro',
                generation_config=generation_config
            )
        except Exception as e:
            print(f"Error configuring Aggregator (Gemini) API: {e}")
            self.model = None

    async def synthesize_reports(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a list of report dictionaries and synthesizes them.
        """
        if not self.model:
            return {"error": "Aggregator client is not configured."}

        if not reports:
            return {"error": "No valid reports to synthesize."}

        # Manually calculate average fit_score
        total_score = 0
        valid_reports_count = 0
        for report in reports:
            if "fit_score" in report:
                total_score += report.get("fit_score", 0)
                valid_reports_count += 1
        
        avg_fit_score = round(total_score / valid_reports_count) if valid_reports_count > 0 else 0

        # Build a dynamic prompt
        # Build the user message for the synthesizer
        reports_str_list = []
        for i, report in enumerate(reports):
            model_name = report.pop('model_source', f'Model {i+1}') # Get source and remove it
            reports_str_list.append(f"--- REPORT {i+1} (from {model_name}) ---\n{json.dumps(report, indent=2)}")
        
        reports_str = "\n\n".join(reports_str_list)

        user_message = f"""
        Here are the {len(reports)} AI reports to synthesize:

        {reports_str}

        --- ANALYSIS ---
        Please synthesize these into a single, final JSON report.
        Use a "fit_score" of {avg_fit_score}.
        """

        # Call the Gemini API to synthesize
        try:
            response = await self.model.generate_content_async(
                [AGGREGATOR_SYSTEM_PROMPT, user_message]
            )
            final_report = json.loads(response.text)
            
            # Override the LLM's fit_score with our pre-calculated average
            final_report["fit_score"] = avg_fit_score
            
            return final_report
            
        except Exception as e:
            print(f"An error occurred while synthesizing reports: {e}")
            return {"error": f"Error: Could not synthesize the final report. {e}"}