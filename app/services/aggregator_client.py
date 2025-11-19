import os
import google.generativeai as genai
import json
from typing import Dict, Any, List
from app.constants import AGGREGATOR_SYSTEM_PROMPT


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
        Args:
            reports (List[Dict[str, Any]]): List of individual AI-generated reports.
        Returns:
            Dict[str, Any]: The synthesized final report.
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
        
        if valid_reports_count > 0:
            avg_fit_score = round(total_score / valid_reports_count)
        else:
            avg_fit_score = 0

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