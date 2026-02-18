"""
Claude Client Module
Handles all interactions with Claude API for generating structured responses.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from anthropic import Anthropic

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings


# System prompt that enforces the strict output format
from backend.prompts import IDEA_VALIDATION_PROMPT


class ClaudeClient:
    """Handles Claude API interactions."""
    
    def __init__(self):
        """Initialize the Anthropic client."""
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.model = settings.CLAUDE_MODEL
    
    def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks with explicit document labels for precise referencing."""
        if not chunks:
            return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
        
        # Sort chunks by score descending to ensure most relevant are presented first
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
        system_prompt: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Generate a structured response using Claude.
        
        Args:
            user_query: The founder's messy input
            chunks: Retrieved evidence chunks
            system_prompt: Optional override for system prompt
        
        Returns:
            Dict with success status and response content
        """
        # Use provided prompt or default to generic validation logic
        prompt_to_use = system_prompt if system_prompt else IDEA_VALIDATION_PROMPT

        # Format evidence
        evidence_context = self.format_evidence_context(chunks)
        
        # Build user message
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
            # Map frontend aliases to actual model IDs
            MODEL_MAP = {
                "claude-sonnet": self.model,  # Use server-configured model
            }
            target_model = MODEL_MAP.get(model, self.model) if model else self.model
            
            response = self.client.messages.create(
                model=target_model,
                max_tokens=1500,
                system=prompt_to_use,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Extract the text response
            response_text = response.content[0].text
            
            # Parse sections (basic parsing)
            sections = self._parse_sections(response_text)
            
            return {
                "success": True,
                "full_response": response_text,
                "sections": sections,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            
        except Exception as e:
            print(f"Claude API Error: {e}")
            return {
                "success": False,
                "error": str(e),
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
        
        # Simple section markers to look for
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


# Global client instance
claude_client = ClaudeClient()


def get_founder_advice(query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for getting advice."""
    return claude_client.generate_response(query, chunks)
