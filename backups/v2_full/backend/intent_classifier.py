"""
Intent Classifier Module
Classifies user queries into specific categories to route to the correct answering logic.
"""

from typing import Dict, Any, List
from backend.claude_client import ClaudeClient
from backend.gemini_client import GeminiClient
from config.settings import settings

class IntentClassifier:
    """Classifies user intent using LLM."""
    
    def __init__(self):
        """Initialize with fallback clients."""
        try:
            self.claude = ClaudeClient()
        except:
            self.claude = None
            
        try:
            self.gemini = GeminiClient()
        except:
            self.gemini = None
            
    def classify(self, query: str) -> str:
        """
        Classify the query into one of the known categories.
        Returns: category_id (str) or "other"
        """
        # Fetch categories dynamically
        from backend.categories import category_manager
        categories = category_manager.list_categories()
        
        # Build prompt dynamically
        categories_text = ""
        for i, cat in enumerate(categories, 1):
            categories_text += f'{i}. "{cat.id}" (Full Name: {cat.name})\n'
            categories_text += f'   - Description: {cat.description}\n\n'
            
        # Add "other" category
        categories_text += f'{len(categories) + 1}. "other"\n'
        categories_text += '   - Topics: Anything else (e.g. legal, finance, coding, life advice, or complete gibberish).'

        system_prompt = f"""You are a classification system for a startup founder advisor tool.
Your job is to categorize the USER QUERY into exactly one of the following categories:

{categories_text}

OUTPUT RULES:
- Return ONLY the category ID (e.g. "idea-validation").
- No explanation, no JSON, just the string.
- If the query covers multiple topics, choose the DOMINANT one.
"""
        
        user_message = f"""USER QUERY: "{query}"
        
CATEGORY:"""

        # Try Claude first
        if self.claude and self.claude.client:
            try:
                response = self.claude.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=50,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                category = response.content[0].text.strip().lower().replace('"', '')
                return self._sanitize_category(category, categories)
            except Exception as e:
                print(f"Classifier (Claude) failed: {e}")
        
        # Fallback to Gemini
        if self.gemini and self.gemini.model:
            try:
                # For Gemini, we pass system prompt in the message or configure it
                # Using the refactored generate_response-like logic but simpler
                prompt = f"""SYSTEM: {system_prompt}
                
                {user_message}"""
                
                response = self.gemini.model.generate_content(prompt)
                category = response.text.strip().lower().replace('"', '')
                return self._sanitize_category(category, categories)
            except Exception as e:
                print(f"Classifier (Gemini) failed: {e}")
                
        # Default fallback
        return "idea-validation"

    def _sanitize_category(self, category: str, available_categories: List[Any]) -> str:
        """Ensure returned category is valid."""
        valid_ids = [cat.id for cat in available_categories] + ["other"]
        
        # direct match
        if category in valid_ids:
            return category
            
        # heuristic match (search in IDs and names)
        for cat in available_categories:
            if cat.id in category or category in cat.id:
                return cat.id
            if cat.name.lower() in category or category in cat.name.lower():
                return cat.id
            
        return "other"

# Global instance
intent_classifier = IntentClassifier()
