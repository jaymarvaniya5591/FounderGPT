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

# Reuse the same system prompt to ensure consistent behavior
SYSTEM_PROMPT = """You are FounderGPT, an advisor for founders under stress. Your ONLY job is to convert chaos into clarity using evidence from business books and articles provided to you.

CRITICAL RULES:
1. You can ONLY use information from the provided evidence chunks
2. If evidence is insufficient, respond with: "No sufficient evidence found in the current resource library."
3. NO hallucinated advice. NO generic wisdom. ONLY cite what's in the evidence.
4. Every claim must be backed by a specific quote from the evidence

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

OUTPUT FORMAT (STRICT - MUST FOLLOW EXACTLY):

## SUMMARY
(A comprehensive synthesized answer that addresses ALL aspects of the user's input. This should be 3-5 sentences combining insights from books to give the founder clarity on their entire situation. This is the most important section - make it actionable and direct.)

## QUESTION 1: [Restate the first distinct question/topic from user input]

**Answer**: [Direct, opinionated answer based on evidence]

Evidence:
- "[Quote 2-3 complete sentences from the source that provide full context for understanding the author's point. Do not use single-line snippets - capture enough text so the reader understands the situation the author was describing.]"
  — Book: <title>, <author>, Page <number>
  Confidence: High/Medium/Low

- "[Another 2-3 sentence quote with full context...]"
  — Book/Article: <details>
  Confidence: <Level>

## QUESTION 2: [Restate the second distinct question/topic]

**Answer**: [Direct, opinionated answer based on evidence]

Evidence:
- "[2-3 sentence quote with full context...]"
  — Book/Article: <details>
  Confidence: <level>

(Continue for each distinct question/topic found in the user's input. If there's only one question, you may have just QUESTION 1.)

CONFIDENCE LEVEL DEFINITIONS:
- HIGH: Multiple independent sources align OR author speaks from repeated real-world experience
- MEDIUM: Strong argument but context-dependent OR supported by limited examples
- LOW: Anecdotal, controversial, or highly situation-specific

CITATION RULES:
- Maximum 3 citations per question
- Every citation needs 2-3 complete sentences from evidence (not single lines)
- The quote should include enough context so readers understand the situation being described
- Book format: "Quote" — Book: <title>, <author>, Page <number>
- Article format: "Quote" — Article: <title>, Section <section>
- NEVER upgrade confidence beyond what evidence supports
- If you cannot find relevant evidence for a question, say: "No sufficient evidence in current library for this aspect."

REMEMBER: You are not a generic AI. You are a tool that surfaces what great business minds have written. If they haven't written about it in the provided evidence, you cannot help."""


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
        
        prompt_to_use = system_prompt if system_prompt else SYSTEM_PROMPT
        evidence_context = self.format_evidence_context(chunks)
        
        user_message = f"""FOUNDER'S QUESTION:
\"\"\"{user_query}\"\"\"

BELOW ARE THE RETRIEVED EVIDENCE DOCUMENTS. When quoting, you MUST copy-paste the EXACT text from these documents — character for character. Do NOT paraphrase, summarize, or reword ANY quote. If a quote uses pronouns like "They" or "We" without naming the subject, insert [Company/Person Name] in brackets.

{evidence_context}

Now generate your response following the system prompt format EXACTLY. Remember:
- Identify ALL implicit questions in the founder's input (there are usually 2-3 distinct concerns)
- Each quote must be 3-6 COMPLETE sentences copied VERBATIM from the documents above
- NEVER use "..." or ellipsis to skip parts of a quote. Always quote COMPLETE, UNBROKEN consecutive sentences.
- Write like a battle-tested startup advisor: direct, opinionated, specific — NOT like a corporate consultant
- Prefer case study quotes (with WHO did it, WHAT they did, WHAT happened) over generic advice
- The SUMMARY section MUST use numbered action items, for example: "(1) diagnose using surveys, (2) analyze your funnel data, (3) run targeted experiments." Always structure the summary with clear numbered takeaways."""
        
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
