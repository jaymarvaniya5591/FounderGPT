"""
Query Processor Module
Implements Perplexity-style query optimization techniques:
- Multi-query expansion
- Query decomposition for complex questions

Uses lightweight heuristics + optional LLM enhancement.
"""

import re
from typing import List, Set


class QueryProcessor:
    """Handles query expansion and optimization for better retrieval."""
    
    def __init__(self):
        """Initialize query processor."""
        # Business/startup related synonyms for query expansion
        self.synonym_map = {
            "validate": ["test", "verify", "check", "confirm", "prove"],
            "customer": ["user", "buyer", "client", "consumer", "market"],
            "product": ["solution", "offering", "service", "MVP", "prototype"],
            "startup": ["company", "business", "venture", "enterprise"],
            "founder": ["entrepreneur", "CEO", "leader", "owner"],
            "growth": ["scale", "expansion", "traction", "momentum"],
            "hire": ["recruit", "employ", "onboard", "team building"],
            "funding": ["investment", "capital", "financing", "raise money"],
            "pivot": ["change direction", "adapt", "shift strategy"],
            "market": ["segment", "audience", "niche", "vertical"],
            "feedback": ["input", "response", "reaction", "criticism"],
            "idea": ["concept", "hypothesis", "vision", "proposal"],
            "problem": ["pain point", "challenge", "issue", "obstacle"],
            "revenue": ["income", "sales", "monetization", "earnings"],
            "competition": ["competitors", "rivals", "alternatives"],
            "two-sided market": ["marketplace", "platform", "network effects", "chicken and egg"],
            "b2b": ["enterprise", "business to business", "sales"],
            "d2c": ["direct to consumer", "ecommerce", "brand"],
        }
        
        # Question patterns for decomposition
        self.compound_patterns = [
            (r'\band\b', ' '),  # "X and Y" -> split
            (r'\balso\b', ' '),
            (r'\bplus\b', ' '),
        ]
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand a single query into multiple semantic variations.
        
        Returns list of queries including:
        1. Original query
        2. Synonym-expanded version
        3. Key concept extraction
        4. Question reformulation
        """
        queries = set()
        queries.add(query)
        
        # 1. Add synonym-expanded versions
        expanded = self._expand_with_synonyms(query)
        queries.add(expanded)
        
        # 2. Extract key concepts
        concepts = self._extract_key_concepts(query)
        if concepts:
            queries.add(concepts)
        
        # 3. Reformulate as different question types
        reformulations = self._reformulate_query(query)
        queries.update(reformulations)
        
        # 4. Add decomposed sub-queries if complex
        sub_queries = self._decompose_complex_query(query)
        queries.update(sub_queries)
        
        # 5. Add Case Study / Real World Scenarios variations (CRITICAL for evidence)
        queries.add(f"{query} case study")
        queries.add(f"{query} real world example")
        queries.add(f"{query} how they did it")
        
        # Remove empty strings and duplicates
        result = [q.strip() for q in queries if q.strip()]
        
        # Limit to 8 queries max for performance (increased for case studies)
        return list(set(result))[:8]
    
    def _expand_with_synonyms(self, query: str) -> str:
        """Replace key terms with their synonyms."""
        expanded = query.lower()
        
        for term, synonyms in self.synonym_map.items():
            if term in expanded:
                # Add first synonym as alternative
                expanded = expanded.replace(term, f"{term} {synonyms[0]}")
                break  # Only expand one term to avoid over-expansion
        
        return expanded
    
    def _extract_key_concepts(self, query: str) -> str:
        """Extract the core concepts from a query."""
        # Remove common question words
        stop_patterns = [
            r'^how (do|can|should|would|to)\s+',
            r'^what (is|are|should|would)\s+',
            r'^why (do|does|is|are|should)\s+',
            r'^when (should|do|does|is)\s+',
            r'\bi\s+',
            r'\bmy\s+',
            r'\bwe\s+',
            r'\bour\s+',
            r'\bthe\s+',
            r'\ba\s+',
            r'\ban\s+',
        ]
        
        concepts = query.lower()
        for pattern in stop_patterns:
            concepts = re.sub(pattern, '', concepts, flags=re.IGNORECASE)
        
        return concepts.strip()
    
    def _reformulate_query(self, query: str) -> List[str]:
        """Create alternative phrasings of the query."""
        reformulations = []
        query_lower = query.lower()
        
        # If it's a "how to" question, create a statement version
        if query_lower.startswith("how"):
            # "How do I validate" -> "validating customers effectively"
            statement = re.sub(r'^how (do|can|should|would|to)\s+i?\s*', '', query_lower)
            if statement != query_lower:
                reformulations.append(f"best practices for {statement}")
        
        # If it's a "what" question, create action version
        if query_lower.startswith("what"):
            action = re.sub(r'^what (is|are|should|would)\s+(the\s+)?', '', query_lower)
            if action != query_lower:
                reformulations.append(action)
        
        # Add "startup" context if not present
        if "startup" not in query_lower and "founder" not in query_lower:
            reformulations.append(f"startup {query}")
        
        return reformulations
    
    def _decompose_complex_query(self, query: str) -> List[str]:
        """Break complex queries into simpler sub-questions."""
        sub_queries = []
        
        # Check for compound questions (contains "and", "also", etc.)
        if " and " in query.lower():
            parts = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if len(part) > 10:  # Meaningful sub-query
                    sub_queries.append(part)
        
        # Check for multiple question marks
        if query.count("?") > 1:
            questions = [q.strip() + "?" for q in query.split("?") if q.strip()]
            sub_queries.extend(questions[:-1])  # Last one might be empty
        
        return sub_queries


# Global instance
query_processor = QueryProcessor()


def expand_query(query: str) -> List[str]:
    """Convenience function for query expansion."""
    return query_processor.expand_query(query)
