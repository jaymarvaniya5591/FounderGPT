"""
OpenAI Client Module
Prioritized LLM for generating structured responses.
"""

import os
import sys
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

# Import central prompts
from backend.prompts import IDEA_VALIDATION_PROMPT

class OpenAIClient:
    """Handles OpenAI API interactions."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        if not settings.OPENAI_API_KEY:
            print("WARNING: OPENAI_API_KEY not set. OpenAI integration will not work.")
            self.client = None
            return
            
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks with explicit document labels for precise referencing."""
        if not chunks:
            return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
        
        chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            resource_type = chunk.get("resource_type", "unknown")
            text = chunk.get("exact_text", "")
            
            if resource_type == "book":
                source = f"Book: {chunk.get('book_title', 'Unknown')}, {chunk.get('author', 'Unknown')}, Ch.{chunk.get('chapter', '?')}, P.{chunk.get('page_number', '?')}"
            else:
                source = f"Article: {chunk.get('article_title', 'Unknown')}, Section: {chunk.get('section_heading', '?')}"
                if chunk.get('url'):
                    source += f", URL: {chunk.get('url')}"
            
            context_parts.append(f"[DOCUMENT {i}] Source: {source}\n{text}\n[/DOCUMENT {i}]\n")
        
        return "\n".join(context_parts)
    
    def generate_response(
        self,
        user_query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using OpenAI.
        """
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "full_response": None,
                "sections": {}
            }
        
        # Use provided prompt or default to generic validation logic
        prompt_to_use = system_prompt if system_prompt else IDEA_VALIDATION_PROMPT
        
        # Format evidence
        evidence_context = self.format_evidence_context(chunks)
        
        # Build user message (MATCHING CLAUDE CLIENT EXACTLY)
        user_message = f"""FOUNDER'S INPUT:
\"\"\"{user_query}\"\"\"

CONTEXTUAL EVIDENCE:
{evidence_context}

Provide your structured response following the EXACT format specified in the system prompt.
- Create a SUMMARY section first that addresses the founder's complete situation
- Create a separate QUESTION section for EACH distinct question you identified
- Remember: ONLY use quotes from the evidence above
- Be opinionated but evidence-backed
- If evidence is insufficient for any question, say so explicitly
- Use 2-3 sentence quotes that provide full context, not single lines"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt_to_use},
                    {"role": "user", "content": user_message}
                ],
                temperature=0,
                max_tokens=2048
            )
            
            response_text = response.choices[0].message.content
            sections = self._parse_sections(response_text)
            
            return {
                "success": True,
                "full_response": response_text,
                "sections": sections,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "full_response": None,
                "sections": {}
            }
            
    def _parse_sections(self, response_text: str) -> Dict[str, str]:
        """Parse the response into individual sections (Shared logic)."""
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
        
        # Find positions of each section
        positions = []
        for marker, key in markers:
            pos = response_text.find(marker)
            if pos != -1:
                positions.append((pos, key, marker))
        
        # Sort by position
        positions.sort(key=lambda x: x[0])
        
        # Extract content between markers
        for i, (pos, key, marker) in enumerate(positions):
            start = pos
            if i + 1 < len(positions):
                end = positions[i + 1][0]
            else:
                end = len(response_text)
            
            sections[key] = response_text[start:end].strip()
        
        return sections
