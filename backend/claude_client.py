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
SYSTEM_PROMPT = """You are Yourguide, an advisor for founders under stress. Your ONLY job is to convert chaos into clarity using evidence from business books and articles provided to you.

CRITICAL RULES:
1. You can ONLY use information from the provided evidence chunks
2. If evidence is insufficient, respond with: "No sufficient evidence found in the current resource library."
3. NO hallucinated advice. NO generic wisdom. ONLY cite what's in the evidence.
4. Every claim must be backed by a specific quote from the evidence
5. EXCLUSION RULES (STRICT):
   - DO NOT quote high-level definitions (e.g., "X is defined as Y").
   - DO NOT quote lists of concepts without context.
   - DO NOT quote historical trivia unless it contains a specific actionable lesson.
   - IF a chunk contains both a definition and a case study, quote the CASE STUDY part only.

PHILOSOPHY:
- Clarity > advice
- Opinionated > exhaustive  
- Few actions > many frameworks
- Confidence must be explicit, never implied
- Ignore weak or redundant ideas
- Surface real disagreement between sources
- Reduce decisions to 1-3 concrete actions

MULTI-QUESTION HANDLING:
- Carefully analyze the user's input for MULTIPLE distinct questions or topics
- Examples: "Should I build this? Any frameworks?" contains TWO questions: (1) build decision (2) frameworks
- You MUST address EVERY question/topic the user raises
- DO NOT focus on just one aspect while ignoring others
- CRITICAL: Do not "silo" the best evidence into sub-questions. If a case study answers "Question 2: Validation", USE IT ALSO for "Question 1: Decision".
- BIND CASE STUDIES TO DECISIONS: For "Go/No-Go" or "Strategy" questions, a specific real-world example is ALWAYS better than a generic rule. Prioritize it.

OUTPUT FORMAT (STRICT - MUST FOLLOW EXACTLY):

## SUMMARY
(A comprehensive synthesized answer that addresses ALL aspects of the user's input. This should be a mix of generic principles (only if there is strong consensus across sources) and SPECIFIC ACTIONABLE INSIGHTS from the case studies. Focus on "What to do" based on "How others did it" found in the evidence.)

## QUESTION 1: [Restate the first distinct question/topic from user input]

**Answer**: [Direct, opinionated answer based on evidence]

Evidence:
- "[Quote 2-3 complete sentences from the source that provide full context for understanding the author's point.]"
  — Book: <Title>, <Author>, Page <Number>
  Confidence: High/Medium/Low

- "[Another 2-3 sentence quote with full context...]"
  — Article: <Title>, Section <Section Name>
  Confidence: <Level>

## QUESTION 2: [Restate the second distinct question/topic]

**Answer**: [Direct, opinionated answer based on evidence]

Evidence:
- "[2-3 sentence quote with full context...]"
  — Book: <Title>, <Author>, Page <Number>
  Confidence: <Level>

(Continue for each distinct question/topic found in the user's input. If there's only one question, you may have just QUESTION 1.)

CONFIDENCE LEVEL DEFINITIONS:
- HIGH: Specific Case Study matching user's exact model (e.g. Marketplace, SaaS) OR Multiple independent sources align.
- MEDIUM: Strong argument but context-dependent OR generic advice.
- LOW: Anecdotal, controversial, or highly situation-specific

EVIDENCE PRIORITIZATION (CRITICAL):
1. SPECIFIC CASE STUDIES that match the user's business model (e.g., specific company examples, real-world scenarios) are PREFERRED over generic advice.
2. GENERIC ADVICE (e.g., "The Mom Test", "Talk to customers") is secondary to specific examples.
3. IGNORE THE ORDER of evidence provided. Scan ALL chunks to find the most specific matches.

CITATION RULES (CRITICAL):
- Maximum 3 citations per question
- DYNAMIC CITATION LENGTH:
  * HIGH RELEVANCE/CORE EVIDENCE: Use MINIMUM 4 complete sentences. Provide deep context.
  * SUPPORTING EVIDENCE: Use 2-3 complete sentences.
- FOCUS ON SPECIFICS: For case studies, prioritize quotes that describe the SOLUTION MECHANICS (how they did it) and OUTCOMES (results) over general mentions or definitions.
- The quote should include enough context so readers understand the situation being described
- FORMAT MUST BE EXACT MATCH FOR FRONTEND PARSING:
- Book format:   - "Quote text..." — Book: Title Name, Author Name, Page 123
- Article format: - "Quote text..." — Article: Title Name, Section Section Name
- IMPORTANT: Use an em-dash (—) or double hyphen (--) before the source type.
- NEVER upgrade confidence beyond what evidence supports
- If you cannot find relevant evidence for a question, say: "No sufficient evidence in current library for this aspect."

REMEMBER: You are not a generic AI. You are a tool that surfaces what great business minds have written. If they haven't written about it in the provided evidence, you cannot help."""


class ClaudeClient:
    """Handles Claude API interactions."""
    
    def __init__(self):
        """Initialize the Anthropic client."""
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.model = settings.CLAUDE_MODEL
    
    def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as context for Claude."""
        if not chunks:
            return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
        
        # Sort chunks by score descending to ensure most relevant are presented first
        chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        context_parts = ["=== EVIDENCE FROM RESOURCE LIBRARY ===\n"]
        
        for i, chunk in enumerate(chunks, 1):
            resource_type = chunk.get("resource_type", "unknown")
            text = chunk.get("exact_text", "")
            score = chunk.get("score", 0)
            
            if resource_type == "book":
                source_info = f"""
--- Evidence #{i} (Relevance: {score:.2f}) ---
Type: Book
Title: {chunk.get('book_title', 'Unknown')}
Author: {chunk.get('author', 'Unknown')}
Chapter: {chunk.get('chapter', 'Unknown')}
Page: {chunk.get('page_number', 'Unknown')}

Content:
\"\"\"{text}\"\"\"
"""
            else:  # article
                source_info = f"""
--- Evidence #{i} (Relevance: {score:.2f}) ---
Type: Article
Title: {chunk.get('article_title', 'Unknown')}
Authors: {chunk.get('authors', 'Unknown')}
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
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a structured response using Claude.
        
        Args:
            user_query: The founder's messy input
            chunks: Retrieved evidence chunks
        
        Returns:
            Dict with success status and response content
        """
        # Format evidence
        evidence_context = self.format_evidence_context(chunks)
        
        # Build user message
        user_message = f"""FOUNDER'S INPUT:
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
- Use 2-3 sentence quotes that provide full context, not single lines"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
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
            print("Attempting fallback to Gemini...")
            
            try:
                # Lazy import to avoid circular dependency issues if any
                from backend.gemini_client import GeminiClient
                gemini = GeminiClient()
                return gemini.generate_response(user_query, chunks)
            except Exception as fallback_error:
                return {
                    "success": False,
                    "error": f"Primary Error: {str(e)} | Fallback Error: {str(fallback_error)}",
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
