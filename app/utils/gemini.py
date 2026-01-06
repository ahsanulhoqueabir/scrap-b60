"""
Gemini AI integration for generating article summaries and analysis
"""
import json
import os
import requests
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from app.config import config
from app.logger import setup_logger
from app.retry import retry_on_exception

logger = setup_logger(__name__)

# State file to track API key and model usage
STATE_FILE = Path("/app/logs/gemini_state.json")


class GeminiAPIManager:
    """Manages multiple Gemini API keys and models with rotation and persistent state tracking"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        # Using stable model names that actually work
        self.models = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3-flash",
        ]
        self.state = self._load_state()
        
        if not self.api_keys:
            logger.warning("No Gemini API keys configured")
    
    def _load_state(self) -> Dict:
        """Load persistent state from file"""
        default_state = {
            "current_key_index": 0,
            "current_model_index": 0,
            "failed_combinations": {},  # {key_index: [failed_model_indices]}
            "last_reset": datetime.now().isoformat()
        }
        
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    
                # Reset daily at midnight
                last_reset = datetime.fromisoformat(state.get("last_reset", datetime.now().isoformat()))
                if datetime.now().date() > last_reset.date():
                    logger.info("Daily reset: Clearing all failed combinations")
                    return default_state
                
                logger.info(f"Loaded state: Key #{state['current_key_index']}, Model #{state['current_model_index']}")
                return state
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}. Using defaults.")
        
        return default_state
    
    def _save_state(self):
        """Save state to file"""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved: Key #{self.state['current_key_index']}, Model #{self.state['current_model_index']}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def mark_combination_failed(self, key_index: int, model_index: int):
        """Mark a key+model combination as failed"""
        key_str = str(key_index)
        if key_str not in self.state["failed_combinations"]:
            self.state["failed_combinations"][key_str] = []
        
        if model_index not in self.state["failed_combinations"][key_str]:
            self.state["failed_combinations"][key_str].append(model_index)
            logger.info(f"Marked failed: Key #{key_index}, Model #{model_index} ({self.models[model_index]})")
        
        self._save_state()
    
    def is_combination_failed(self, key_index: int, model_index: int) -> bool:
        """Check if a key+model combination has previously failed"""
        key_str = str(key_index)
        return model_index in self.state["failed_combinations"].get(key_str, [])
    
    def get_next_combination(self) -> Tuple[Optional[str], Optional[str], int, int]:
        """Get next available key+model combination, skipping failed ones"""
        if not self.api_keys:
            return None, None, -1, -1
        
        current_key_idx = self.state["current_key_index"]
        current_model_idx = self.state["current_model_index"]
        
        # Try to find a working combination
        attempts = 0
        max_attempts = len(self.api_keys) * len(self.models)
        
        while attempts < max_attempts:
            # Skip if this combination has failed today
            if not self.is_combination_failed(current_key_idx, current_model_idx):
                key = self.api_keys[current_key_idx]
                model = self.models[current_model_idx]
                
                logger.info(f"Selected: Key #{current_key_idx} (...{key[-8:]}), Model #{current_model_idx} ({model})")
                return key, model, current_key_idx, current_model_idx
            
            # Move to next model for same key
            current_model_idx += 1
            if current_model_idx >= len(self.models):
                # All models for this key failed, move to next key
                current_model_idx = 0
                current_key_idx = (current_key_idx + 1) % len(self.api_keys)
                logger.info(f"All models failed for key, rotating to Key #{current_key_idx}")
            
            attempts += 1
        
        # All combinations failed
        logger.error("All key+model combinations have failed today!")
        return None, None, -1, -1
    
    def advance_to_next(self, success: bool = False):
        """Advance to next model (or key if all models tried)"""
        if success:
            # On success, just save current position
            self._save_state()
            return
        
        # On failure, advance to next model
        self.state["current_model_index"] += 1
        
        if self.state["current_model_index"] >= len(self.models):
            # All models exhausted for this key, move to next key
            self.state["current_model_index"] = 0
            self.state["current_key_index"] = (self.state["current_key_index"] + 1) % len(self.api_keys)
            logger.info(f"Rotating to next key: Key #{self.state['current_key_index']}")
        
        self._save_state()
    
    def get_next_key(self) -> Optional[str]:
        """Get next API key in rotation (legacy method for backward compatibility)"""
        if not self.api_keys:
            return None
        return self.api_keys[self.state["current_key_index"]]
    
    def get_all_keys(self) -> List[str]:
        """Get all available API keys"""
        return self.api_keys
    
    def get_all_models(self) -> List[str]:
        """Get all available models"""
        return self.models


# Global API manager instance
gemini_manager = GeminiAPIManager(config.GEMINI_API_KEYS)


def generate_summary_with_gemini(title: str, full_text: str, api_key: Optional[str] = None) -> Dict:
    """
    Generate AI-powered summary and analysis using Gemini API with model and key fallback
    
    Args:
        title: Article title
        full_text: Full article text
        api_key: Optional specific API key (if None, uses rotation)
        
    Returns:
        Dictionary containing:
        - category: Article category
        - summary_60_bn: 55-60 word Bangla summary
        - summary_60_en: 55-60 word English summary
        - importance: 1-10 importance score
        - clickbait_score: 0-5 clickbait score
        - clickbait_reason: Reason for clickbait score
        - corrected_title: Corrected title if clickbait_score >= 3
        - keywords: List of 2-4 keywords
        - mcqs: List of 3-4 MCQs
    """
    # Use rotation if no specific key provided, otherwise use all keys for fallback
    if api_key:
        api_keys = [api_key]
        start_key = api_key
    else:
        # Start with next key in rotation for load balancing
        start_key = gemini_manager.get_next_key()
        api_keys = gemini_manager.get_all_keys()
        # Reorder keys to start with rotated key
        start_index = api_keys.index(start_key)
        api_keys = api_keys[start_index:] + api_keys[:start_index]
    
    models = gemini_manager.get_all_models()
    
    if not api_keys:
        raise ValueError("No Gemini API key available")
    
    last_error = None
    
    prompt = f"""
You are a professional news analyst AI.

Analyze the following news and return ONLY a valid JSON object.
DO NOT add explanations, markdown, comments, or extra text.
STRICTLY follow the schema and rules.

General Rules:
- All summaries must be fact-based, neutral, and concise.
- If news language is Bangla, summary_60_bn must be Bangla and summary_60_en must be English.
- If news language is English, summary_60_en must be English and summary_60_bn must be Bangla.
- JSON must be valid and parsable.
- 3-4 MCQs must be relevant to the news content.

Fields Rules:
- category: one English word only (Politics, Sports, Tech, Crime, Economy, Entertainment, World, Health, Science, etc.)
- summary_60_bn: 55–60 words in  strictly Bangla language
- summary_60_en: 55–60 words in English language
- importance: integer from 1 to 10
  - 1–3 = low public impact
  - 4–6 = moderate relevance
  - 7–8 = high national relevance
  - 9–10 = critical or major public impact
- clickbait_score: integer from 0 to 5
  - 0 = title fully accurate
  - 5 = highly misleading or exaggerated
- clickbait_reason: 8–15 words, English
- corrected_title:
  - If clickbait_score >= 3, provide a proper, factual title
  - If clickbait_score < 3, return an empty string ""
- keywords:
  - 2–4 main keywords
  - lowercase
  - no punctuation
  - array of strings
- mcqs:
  - 3–4 MCQs generated from the news
  - Each MCQ must have 4 options
  - Only one correct answer

MCQ Structure:
{{
  "question": "",
  "options": ["", "", "", ""],
  "correct_answer": ""
}}

Title:
"{title}"

News:
"{full_text}"

Return JSON in this EXACT format:
{{
  "category": "",
  "summary_60_bn": "",
  "summary_60_en": "",
  "importance": 0,
  "clickbait_score": 0,
  "clickbait_reason": "",
  "corrected_title": "",
  "keywords": [],
  "mcqs": []
}}
"""
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    # Use persistent state tracking to get next working combination
    max_retries = len(api_keys) * len(models)
    
    for attempt in range(max_retries):
        key, model, key_idx, model_idx = gemini_manager.get_next_combination()
        
        if key is None or model is None:
            raise ValueError("All API key+model combinations have failed today. Try again tomorrow.")
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            
            headers = {
                "x-goog-api-key": key,
                "Content-Type": "application/json"
            }
            
            key_suffix = key[-8:] if len(key) > 8 else key
            logger.info(f"🔄 Attempting: {title[:50]}... (Key #{key_idx}: ...{key_suffix}, Model #{model_idx}: {model})")
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text from response
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Clean up markdown code blocks if present
            clean_text = text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            result = json.loads(clean_text)
            
            # Success! Save state without advancing (keep using this combination)
            gemini_manager.advance_to_next(success=True)
            
            logger.info(f"✅ SUCCESS: Key #{key_idx}, Model #{model_idx} ({model}) - Category: {result.get('category', 'N/A')}")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit
                logger.warning(f"⚠️ RATE LIMIT: Key #{key_idx}, Model #{model_idx} ({model}) - Marking as failed")
                gemini_manager.mark_combination_failed(key_idx, model_idx)
                gemini_manager.advance_to_next(success=False)
                continue
            else:
                logger.error(f"❌ HTTP ERROR {response.status_code}: Key #{key_idx}, Model #{model_idx}")
                gemini_manager.mark_combination_failed(key_idx, model_idx)
                gemini_manager.advance_to_next(success=False)
                continue
                
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️ PARSE ERROR: Key #{key_idx}, Model #{model_idx} - {str(e)[:100]}")
            # Don't mark as failed for parse errors (might be temporary)
            gemini_manager.advance_to_next(success=False)
            continue
            
        except Exception as e:
            logger.error(f"❌ UNEXPECTED ERROR: Key #{key_idx}, Model #{model_idx} - {str(e)[:100]}")
            gemini_manager.advance_to_next(success=False)
            continue
    
    # If all attempts failed
    raise ValueError(f"Failed to generate summary after {max_retries} attempts across all keys and models")


def batch_generate_summaries(articles: List[Dict], max_concurrent: int = 3) -> List[Dict]:
    """
    Generate summaries for multiple articles efficiently using multiple API keys
    
    Args:
        articles: List of article dictionaries
        max_concurrent: Maximum number of concurrent requests (default: 3)
        
    Returns:
        List of articles with added AI analysis
    """
    enriched_articles = []
    
    for article in articles:
        try:
            # Generate summary
            ai_analysis = generate_summary_with_gemini(
                title=article.get("title", ""),
                full_text=article.get("full_text", "")
            )

            logger.debug(f" {ai_analysis.get('mcqs',[])}")
            
            # Merge AI analysis into article
            article.update({
                "category": ai_analysis.get("category", ""),
                "summary_60_bn": ai_analysis.get("summary_60_bn", ""),
                "summary_60_en": ai_analysis.get("summary_60_en", ""),
                "importance": ai_analysis.get("importance", 5),
                "clickbait_score": ai_analysis.get("clickbait_score", 0),
                "clickbait_reason": ai_analysis.get("clickbait_reason", ""),
                "corrected_title": ai_analysis.get("corrected_title", ""),
                "keywords": ai_analysis.get("keywords", []),
                "mcqs": ai_analysis.get("mcqs", [])
            })
            
            enriched_articles.append(article)
            
        except Exception as e:
            logger.error(f"Failed to generate summary for article '{article.get('title', 'Unknown')}': {str(e)}")
            # Add article without AI analysis
            enriched_articles.append(article)
    
    return enriched_articles
