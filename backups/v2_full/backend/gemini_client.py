"""
Gemini Client Module (Fallback)
Handles interactions with Google Gemini API when Claude is unavailable.
"""

import os
import sys
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

# System prompt that enforces the strict output format (Now imported)
from backend.prompts import IDEA_VALIDATION_PROMPT


class GeminiClient:
    """Handles Gemini API interactions."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        if not settings.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY not set. Fallback will not work.")
            self.model = None
            return
            
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as context (same format as Claude)."""
        if not chunks:
            return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
        
        # Sort chunks by score descending to ensure most relevant are presented first
        chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        context_parts = ["=== EVIDENCE FROM RESOURCE LIBRARY ===\n"]
        
        for i, chunk in enumerate(chunks, 1):
            resource_type = chunk.get("resource_type", "unknown")
            text = chunk.get("exact_text", "")
            # Gemini handles large contexts well, but staying consistent with Claude format
            
            if resource_type == "book":
                source_info = f"""
--- Evidence #{i} ---
Type: Book
Title: {chunk.get('book_title', 'Unknown')}
Author: {chunk.get('author', 'Unknown')}
Page: {chunk.get('page_number', 'Unknown')}

Content:
\"\"\"{text}\"\"\"
"""
            else:  # article
                source_info = f"""
--- Evidence #{i} ---
Type: Article
Title: {chunk.get('article_title', 'Unknown')}
Section: {chunk.get('section_heading', 'Unknown')}
URL: {chunk.get('url', 'N/A')}

Content:
\"\"\"{text}\"\"\"
"""
            context_parts.append(source_info)
        
        context_parts.append("\n=== END OF EVIDENCE ===")
        return "\n".join(context_parts)
    
    def generate_response(
        self,
        user_query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using Gemini.
        
        Args:
            user_query: The founder's messy input
            chunks: Retrieved evidence chunks
            system_prompt: Optional override for system prompt
            
        Returns:
            Dict with success status and response content
        """
        if not self.model:
            return {
                "success": False,
                "error": "Gemini client not initialized (missing API key)",
                "full_response": None,
                "sections": {}
            }
            
        # Use provided prompt or default
        prompt_to_use = system_prompt if system_prompt else IDEA_VALIDATION_PROMPT

        # Format evidence
        evidence_context = self.format_evidence_context(chunks)
        
        # Build full prompt (Gemini often prefers system instructions in valid message or config)
        # We'll use the proper system_instruction if using 1.5 Pro/Flash, 
        # but for safety/simplicity we can prepend it to the user message or use the system_instruction param if supported by the lib version
        # The genai library usage: model = genai.GenerativeModel('model-name', system_instruction=...)
        # Since we initialize model in __init__, we might need to recreate it or just prepend.
        # Prepending is often safer across versions unless we are sure of the lib version.
        # But wait, we can pass system_instruction during generation or configure it.
        # Actually, for per-request system prompts, it's best to include it in the message content clearly.
        
        full_prompt = f"""SYSTEM INSTRUCTIONS:
{prompt_to_use}

USER TASK:
FOUNDER'S INPUT:
\"\"\"{user_query}\"\"\"

STEP 1 - ANALYZE THE INPUT:
Before responding, carefully analyze the founder's input:
- What is the CONTEXT? (e.g., user research results, specific numbers mentioned, stage of company)
- What are ALL the DISTINCT QUESTIONS being asked? List each one explicitly.
- Are there any emotional undertones or implicit concerns?

STEP 2 - SEARCH FOR EVIDENCE:
{evidence_context}

STEP 3 - RESPOND:
Now provide your structured response following the EXACT format specified:
- Create a SUMMARY section first that addresses the founder's complete situation
- Create a separate QUESTION section for EACH distinct question you identified
- Remember: ONLY use quotes from the evidence above
- Be opinionated but evidence-backed
- If evidence is insufficient for any question, say so explicitly
- Use 2-3 sentence quotes that provide full context, not single lines
"""
        
        try:
            # Generate content
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2, # Low temperature for factual RAG
                    max_output_tokens=4096
                )
            )
            
            response_text = response.text
            
            # Parse sections
            sections = self._parse_sections(response_text)
            
            return {
                "success": True,
                "full_response": response_text,
                "sections": sections,
                "usage": {
                    "input_tokens": 0,  # Gemini doesn't always return token counts easily in all versions
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
        """Parse the response into individual sections (Same as Claude client)."""
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
