"""
LLM Gateway Module
Orchestrates prioritized fallback chain for LLM requests.
Priorities:
1. Claude Sonnet 4.5 (Primary)
2. Gemini 3 Flash (Fallback)
"""

import os
import sys
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class LLMGateway:
    """Manages LLM fallback chain."""
    
    _claude_client = None
    _gemini_client = None
    
    def __init__(self):
        """Initialize gateway."""
        pass
        
    @property
    def claude(self):
        """Lazy load Claude client."""
        if self._claude_client is None:
            try:
                from backend.claude_client import ClaudeClient
                self._claude_client = ClaudeClient()
            except Exception as e:
                print(f"Failed to load Claude client: {e}")
        return self._claude_client
        
    @property
    def gemini(self):
        """Lazy load Gemini client."""
        if self._gemini_client is None:
            try:
                from backend.gemini_client import GeminiClient
                self._gemini_client = GeminiClient()
            except Exception as e:
                print(f"Failed to load Gemini client: {e}")
        return self._gemini_client
    
    def generate_response(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate response trying providers in order: Claude -> Gemini.
        """
        errors = []
        
        self._log("\n" + "="*60)
        self._log("[GATEWAY] LLM GATEWAY: Starting request with fallback chain")
        self._log("="*60)
        
        # 1. Try Claude (PRIORITY 1 - Primary)
        try:
            self._log("\n[P1-CLAUDE] Attempting Claude Sonnet 4.5...")
            if self.claude and self.claude.client:
                result = self.claude.generate_response(query, chunks, system_prompt=system_prompt)
                if result.get("success"):
                    self._log_provider_success("CLAUDE")
                    result["llm_provider"] = "Claude"
                    return result
                else:
                    error_msg = f"Claude returned unsuccessful: {result.get('error', 'Unknown')}"
                    self._log(f"[WARN] {error_msg}")
                    errors.append(error_msg)
            else:
                msg = "Claude client not initialized"
                self._log(f"[WARN] {msg}")
                errors.append(msg)
        except Exception as e:
            error_msg = f"Claude Exception: {str(e)}"
            self._log(f"[ERROR] {error_msg}")
            errors.append(error_msg)
            
        # 2. Try Gemini (PRIORITY 2 - Fallback)
        try:
            self._log("\n[P2-GEMINI] Falling back to Gemini 3 Flash...")
            if self.gemini and self.gemini.model:
                result = self.gemini.generate_response(query, chunks, system_prompt=system_prompt)
                if result.get("success"):
                    self._log_provider_success("GEMINI")
                    result["llm_provider"] = "Gemini"
                    return result
                else:
                    error_msg = f"Gemini returned unsuccessful: {result.get('error', 'Unknown')}"
                    self._log(f"[WARN] {error_msg}")
                    errors.append(error_msg)
            else:
                msg = "Gemini client not initialized"
                self._log(f"[WARN] {msg}")
                errors.append(msg)
        except Exception as e:
            error_msg = f"Gemini Exception: {str(e)}"
            self._log(f"[ERROR] {error_msg}")
            errors.append(error_msg)
            
        # All providers failed
        self._log("\n[FAILED] ALL PROVIDERS FAILED!")
        self._log("="*60 + "\n")
        return {
            "success": False,
            "error": "All LLM providers failed: " + " | ".join(errors),
            "full_response": None,
            "sections": {},
            "llm_provider": None
        }
    
    def _log(self, message: str):
        """Log directly to stdout."""
        try:
            sys.stdout.write(message + "\n")
            sys.stdout.flush()
        except Exception:
            print(message, flush=True)
    
    def _log_provider_success(self, provider: str):
        """Log which provider succeeded - prominent output with flush."""
        self._log("\n" + "="*60)
        self._log(f">>> LLM SOURCE: {provider} <<<")
        self._log("="*60 + "\n")

# Global gateway instance
llm_gateway = LLMGateway()

def get_founder_advice(query: str, chunks: List[Dict[str, Any]], system_prompt: str = None) -> Dict[str, Any]:
    """Convenience function."""
    return llm_gateway.generate_response(query, chunks, system_prompt=system_prompt)
