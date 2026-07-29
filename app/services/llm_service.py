"""
LLM Validation service using Google Gemini Flash.
Validates and normalizes extracted doctor registration data.
"""

import os
import json
from typing import Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """Service for validating and normalizing extracted data using Gemini Flash."""

    _instance = None
    _model = None

    @classmethod
    def get_instance(cls) -> "LLMService":
        """Singleton pattern for model reuse."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize Gemini model."""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            genai.configure(api_key=api_key)
            LLMService._model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            LLMService._model = None

    async def validate_and_normalize(
        self,
        transcript: str,
        regex_data: Dict[str, Optional[str]],
        ner_data: Dict[str, Optional[str]],
    ) -> Dict[str, str]:
        """
        Use Gemini Flash to validate and normalize extracted data.

        Args:
            transcript: Original transcript text
            regex_data: Data extracted by regex (phone, email)
            ner_data: Data extracted by NER (name, hospital, department)

        Returns:
            Validated and normalized doctor registration data
        """
        if LLMService._model is None:
            # Fallback: combine regex and NER data without LLM validation
            return self._fallback_merge(regex_data, ner_data)

        prompt = self._build_prompt(transcript, regex_data, ner_data)

        try:
            response = LLMService._model.generate_content(prompt)
            result = self._parse_response(response.text)
            return result
        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to merged data
            return self._fallback_merge(regex_data, ner_data)

    def _build_prompt(
        self,
        transcript: str,
        regex_data: Dict[str, Optional[str]],
        ner_data: Dict[str, Optional[str]],
    ) -> str:
        """Build the validation prompt for Gemini."""
        return f"""You are a medical data extraction assistant for a doctor registration system.

Given the following transcript from a doctor's voice registration, along with pre-extracted data,
validate and normalize the information. Return ONLY a valid JSON object.

TRANSCRIPT:
"{transcript}"

PRE-EXTRACTED DATA (from regex):
- Phone: {regex_data.get('phone', 'not found')}
- Email: {regex_data.get('email', 'not found')}

PRE-EXTRACTED DATA (from NER):
- Name: {ner_data.get('PERSON_NAME', 'not found')}
- Hospital: {ner_data.get('HOSPITAL', 'not found')}
- Department: {ner_data.get('DEPARTMENT', 'not found')}

INSTRUCTIONS:
1. Validate all extracted fields against the transcript
2. Normalize hospital names (e.g., "apollo" → "Apollo Hospital")
3. Normalize department names (e.g., "cardiology" → "Cardiology")
4. Ensure doctor name has proper title (Dr.) and capitalization
5. Validate email format
6. Validate Indian phone number (10 digits, starts with 6-9)
7. If a field cannot be determined, use empty string ""

Return ONLY this JSON structure (no markdown, no explanation):
{{
    "name": "",
    "email": "",
    "phone": "",
    "hospital": "",
    "department": ""
}}"""

    def _parse_response(self, response_text: str) -> Dict[str, str]:
        """Parse Gemini's response to extract JSON."""
        # Try direct JSON parse
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first and last lines (```json and ```)
                cleaned = "\n".join(lines[1:-1])

            result = json.loads(cleaned)

            # Ensure all required fields exist
            required_fields = ["name", "email", "phone", "hospital", "department"]
            for field in required_fields:
                if field not in result:
                    result[field] = ""

            return result

        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Return empty structure
            return {
                "name": "",
                "email": "",
                "phone": "",
                "hospital": "",
                "department": "",
            }

    def _fallback_merge(
        self,
        regex_data: Dict[str, Optional[str]],
        ner_data: Dict[str, Optional[str]],
    ) -> Dict[str, str]:
        """Merge regex and NER data without LLM validation."""
        return {
            "name": ner_data.get("PERSON_NAME") or "",
            "email": regex_data.get("email") or "",
            "phone": regex_data.get("phone") or "",
            "hospital": ner_data.get("HOSPITAL") or "",
            "department": ner_data.get("DEPARTMENT") or "",
        }
