"""
Gemini Client Module (PRIMARY)
Handles interactions with Google Gemini API for fast RAG response generation.
Uses Gemini 2.0 Flash for optimal speed with structured output.
"""

import os
import sys
import google.generativeai as genai
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

# System prompt import
from backend.prompts import IDEA_VALIDATION_PROMPT


class GeminiClient:
    """Handles Gemini API interactions."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        if not settings.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY not set.")
            self.model = None
            return
            
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        self.model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048
            )
        )
    
    def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as compact context."""
        if not chunks:
            return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
        
        chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        context_parts = ["EVIDENCE:\n"]
        
        for i, chunk in enumerate(chunks, 1):
            resource_type = chunk.get("resource_type", "unknown")
            text = chunk.get("exact_text", "")
            
            if resource_type == "book":
                source = f"Book: {chunk.get('book_title', 'Unknown')}, {chunk.get('author', 'Unknown')}, Ch.{chunk.get('chapter', '?')}, P.{chunk.get('page_number', '?')}"
            else:
                source = f"Article: {chunk.get('article_title', 'Unknown')}, Section: {chunk.get('section_heading', '?')}"
                if chunk.get('url'):
                    source += f", URL: {chunk.get('url')}"
            
            context_parts.append(f"[{i}] {source}\n\"\"\"{text}\"\"\"\n")
        
        return "\n".join(context_parts)
    
    def generate_response(
        self,
        user_query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using Gemini.
        """
        if not self.model:
            return {
                "success": False,
                "error": "Gemini client not initialized (missing API key)",
                "full_response": None,
                "sections": {}
            }
            
        prompt_to_use = system_prompt if system_prompt else IDEA_VALIDATION_PROMPT
        evidence_context = self.format_evidence_context(chunks)
        
        full_prompt = f"""{prompt_to_use}

FOUNDER'S INPUT:
\"\"\"{user_query}\"\"\"

CONTEXTUAL EVIDENCE:
{evidence_context}

Provide your structured response following the EXACT format specified.
- Create a SUMMARY section first that addresses the founder's complete situation
- Create a separate QUESTION section for EACH distinct question you identified
- Remember: ONLY use quotes from the evidence above
- Be opinionated but evidence-backed
- If evidence is insufficient for any question, say so explicitly
- Use 2-3 sentence quotes that provide full context, not single lines"""
        
        try:
            response = self.model.generate_content(full_prompt)
            
            response_text = response.text
            
            sections = self._parse_sections(response_text)
            
            return {
                "success": True,
                "full_response": response_text,
                "sections": sections,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini Error: {str(e)}",
                "full_response": None,
                "sections": {}
            }

    def _parse_sections(self, response_text: str) -> Dict[str, str]:
        """Parse the response into individual sections."""
        sections = {
            "section_a": "",
            "section_b": "",
            "section_c": "",
            "section_d": "",
            "section_e": ""
        }
        
        markers = [
            ("## A.", "section_a"),
            ("## B.", "section_b"),
            ("## C.", "section_c"),
            ("## D.", "section_d"),
            ("## E.", "section_e"),
        ]
        
        positions = []
        for marker, key in markers:
            pos = response_text.find(marker)
            if pos != -1:
                positions.append((pos, key, marker))
        
        positions.sort(key=lambda x: x[0])
        
        for i, (pos, key, marker) in enumerate(positions):
            start = pos
            if i + 1 < len(positions):
                end = positions[i + 1][0]
            else:
                end = len(response_text)
            
            sections[key] = response_text[start:end].strip()
        
        return sections
