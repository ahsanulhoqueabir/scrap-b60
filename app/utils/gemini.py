"""
Gemini AI integration for generating article summaries and analysis
"""
import json
import requests
from typing import Dict, Optional, List
from app.config import config
from app.logger import setup_logger
from app.retry import retry_on_exception

logger = setup_logger(__name__)


class GeminiAPIManager:
    """Manages multiple Gemini API keys and models with rotation for efficient usage"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        # Using stable model names that actually work
        self.models = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3-flash",
        ]
        self.current_index = 0
        
        if not self.api_keys:
            logger.warning("No Gemini API keys configured")
    
    def get_next_key(self) -> Optional[str]:
        """Get next API key in rotation"""
        if not self.api_keys:
            return None
        
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key
    
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
    api_keys = [api_key] if api_key else gemini_manager.get_all_keys()
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
    
    # Try each API key with all models before moving to next key
    for key in api_keys:
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                
                headers = {
                    "x-goog-api-key": key,
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Generating summary for: {title[:50]}... (Model: {model})")
                
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract text from response
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Clean up markdown code blocks if present
                clean_text = text.replace("```json", "").replace("```", "").strip()
                
                # Parse JSON
                result = json.loads(clean_text)
                
                logger.info(f"Successfully generated summary (Model: {model}, Category: {result.get('category', 'N/A')})")
                return result
                
            except (KeyError, IndexError, json.JSONDecodeError, requests.RequestException) as e:
                last_error = e
                logger.warning(f"Failed with model {model}: {str(e)}. Trying next model...")
                continue
    
    # If all models and keys failed, raise the last error
    logger.error(f"All models and API keys failed. Last error: {str(last_error)}")
    raise ValueError(f"Failed to generate summary after trying all models and keys: {str(last_error)}")


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
