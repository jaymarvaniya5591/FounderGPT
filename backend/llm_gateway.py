"""
LLM Gateway Module
Orchestrates model-based routing for LLM requests.
Routes to OpenAI GPT-4o (primary) or Claude Sonnet based on user selection.
Default: OpenAI GPT-4o
"""

import os
import sys
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class LLMGateway:
    """Manages LLM routing and fallback chain."""
    
    _openai_client = None
    _claude_client = None
    
    def __init__(self):
        """Initialize gateway."""
        pass
    
    @property
    def openai(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None:
            try:
                from backend.openai_client import OpenAIClient
                self._openai_client = OpenAIClient()
            except Exception as e:
                print(f"Failed to load OpenAI client: {e}")
        return self._openai_client
        
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
    
    def generate_response(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Generate response. Routes based on model selection:
        - 'gpt-4o' or default -> OpenAI GPT-4o (fast + smart)
        - 'claude-sonnet' -> Claude Sonnet (fallback to OpenAI)
        """
        errors = []
        
        self._log("\n" + "="*60)
        self._log("[GATEWAY] LLM GATEWAY: Starting request")
        self._log("="*60)
        
        # Determine if user explicitly chose Claude Sonnet
        use_claude_first = (model == "claude-sonnet")
        
        if use_claude_first:
            # User chose Sonnet: try Claude first, fallback to OpenAI
            result = self._try_claude(query, chunks, system_prompt, errors)
            if result:
                return result
            result = self._try_openai(query, chunks, system_prompt, errors)
            if result:
                return result
        else:
            # Default (GPT-4o): try OpenAI first, fallback to Claude
            result = self._try_openai(query, chunks, system_prompt, errors)
            if result:
                return result
            result = self._try_claude(query, chunks, system_prompt, errors)
            if result:
                return result
            
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
    
    def _try_openai(self, query, chunks, system_prompt, errors):
        """Try OpenAI provider."""
        try:
            self._log("\n[OPENAI] Attempting GPT-4o...")
            if self.openai and self.openai.client:
                result = self.openai.generate_response(query, chunks, system_prompt=system_prompt)
                if result.get("success"):
                    self._log_provider_success("OPENAI GPT-4o")
                    result["llm_provider"] = "OpenAI"
                    return result
                else:
                    error_msg = f"OpenAI returned unsuccessful: {result.get('error', 'Unknown')}"
                    self._log(f"[WARN] {error_msg}")
                    errors.append(error_msg)
            else:
                msg = "OpenAI client not initialized"
                self._log(f"[WARN] {msg}")
                errors.append(msg)
        except Exception as e:
            error_msg = f"OpenAI Exception: {str(e)}"
            self._log(f"[ERROR] {error_msg}")
            errors.append(error_msg)
        return None
    
    def _try_claude(self, query, chunks, system_prompt, errors):
        """Try Claude provider."""
        try:
            self._log("\n[CLAUDE] Attempting Claude Sonnet...")
            if self.claude and self.claude.client:
                result = self.claude.generate_response(query, chunks, system_prompt=system_prompt)
                if result.get("success"):
                    self._log_provider_success("CLAUDE SONNET")
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
        return None
    
    def _log(self, message: str):
        """Log directly to stdout."""
        try:
            sys.stdout.write(message + "\n")
            sys.stdout.flush()
        except Exception:
            print(message, flush=True)
    
    def _log_provider_success(self, provider: str):
        """Log which provider succeeded."""
        self._log("\n" + "="*60)
        self._log(f">>> LLM SOURCE: {provider} <<<")
        self._log("="*60 + "\n")

# Global gateway instance
llm_gateway = LLMGateway()

def get_founder_advice(query: str, chunks: List[Dict[str, Any]], system_prompt: str = None) -> Dict[str, Any]:
    """Convenience function."""
    return llm_gateway.generate_response(query, chunks, system_prompt=system_prompt)
