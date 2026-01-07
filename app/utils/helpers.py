"""
Utility helper functions for scrapers
"""
import json
import random
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import requests
import cloudscraper
from app.config import config
from app.logger import setup_logger
from app.retry import retry_on_exception

logger = setup_logger(__name__)


def get_random_delay(min_seconds: float = 1, max_seconds: float = 3) -> float:
    """
    Generate a random delay to avoid detection
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
        
    Returns:
        Random delay in seconds
    """
    return random.uniform(min_seconds, max_seconds)


def sleep_random(min_seconds: float = 1, max_seconds: float = 3) -> None:
    """
    Sleep for a random duration
    
    Args:
        min_seconds: Minimum sleep duration
        max_seconds: Maximum sleep duration
    """
    delay = get_random_delay(min_seconds, max_seconds)
    time.sleep(delay)


@retry_on_exception(max_retries=3, delay=2)
def fetch_with_requests(url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    """
    Fetch URL using standard requests library with retry logic
    
    Args:
        url: URL to fetch
        headers: Optional HTTP headers
        
    Returns:
        Response object
    """
    if headers is None:
        headers = {'User-Agent': config.USER_AGENT}
    
    logger.debug(f"Fetching URL with requests: {url}")
    response = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


@retry_on_exception(max_retries=3, delay=2)
def fetch_with_curl_cffi(
    url: str, 
    impersonate: str = "chrome142"
) -> curl_requests.Response:
    """
    Fetch URL using curl_cffi library with retry logic and enhanced headers
    
    Args:
        url: URL to fetch
        impersonate: Browser to impersonate
        
    Returns:
        Response object
    """
    # Enhanced headers to bypass bot detection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    logger.debug(f"Fetching URL with curl_cffi ({impersonate}): {url}")
    
    # Add random delay to mimic human behavior
    time.sleep(random.uniform(0.5, 1.5))
    
    response = curl_requests.get(
        url, 
        impersonate=impersonate, 
        headers=headers,
        timeout=config.REQUEST_TIMEOUT,
        allow_redirects=True
    )
    response.raise_for_status()
    return response


@retry_on_exception(max_retries=3, delay=2)
def fetch_with_cloudscraper(url: str) -> requests.Response:
    """
    Fetch URL using cloudscraper to bypass Cloudflare and anti-bot protection
    
    Args:
        url: URL to fetch
        
    Returns:
        Response object
    """
    logger.debug(f"Fetching URL with cloudscraper: {url}")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    response = scraper.get(url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def fetch_with_fallback(url: str) -> requests.Response:
    """
    Fetch URL with multiple fallback methods to bypass anti-bot protection
    1. Try curl_cffi with chrome impersonation
    2. Try cloudscraper (bypasses Cloudflare)
    3. Try curl_cffi with safari impersonation
    4. Try standard requests as last resort
    
    Args:
        url: URL to fetch
        
    Returns:
        Response object
        
    Raises:
        Exception: If all methods fail
    """
    methods = [
        ("curl_cffi (chrome)", lambda: fetch_with_curl_cffi(url, "chrome142")),
        ("cloudscraper", lambda: fetch_with_cloudscraper(url)),
        ("curl_cffi (safari)", lambda: fetch_with_curl_cffi(url, "safari17_0")),
        ("requests", lambda: fetch_with_requests(url))
    ]
    
    last_error = None
    for method_name, fetch_func in methods:
        try:
            logger.info(f"🔄 Trying {method_name} for: {url[:60]}...")
            response = fetch_func()
            logger.info(f"✅ Success with {method_name}")
            return response
        except Exception as e:
            last_error = e
            error_msg = str(e)[:100]
            logger.warning(f"⚠️ {method_name} failed: {error_msg}")
            time.sleep(1)  # Small delay before trying next method
            continue
    
    logger.error(f"❌ All fetch methods failed for {url[:60]}")
    raise last_error


def parse_html(html_content: str) -> BeautifulSoup:
    """
    Parse HTML content with BeautifulSoup
    
    Args:
        html_content: HTML string to parse
        
    Returns:
        BeautifulSoup object
    """
    return BeautifulSoup(html_content, 'html.parser')


def extract_og_image(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract Open Graph image from parsed HTML
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Image URL or None
    """
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return og_image["content"]
    return None


def extract_paragraphs(soup: BeautifulSoup, selector: str = "p") -> str:
    """
    Extract and join all paragraph text from HTML
    
    Args:
        soup: BeautifulSoup object
        selector: CSS selector for paragraphs (default: "p")
        
    Returns:
        Joined paragraph text
    """
    paragraphs = soup.find_all(selector)
    text_array = [p.text.strip() for p in paragraphs if p.text.strip()]
    return "\n\n".join(text_array)


def save_json(data: Any, filename: str) -> None:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        filename: Output filename
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved data to {filename}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {filename}: {str(e)}")
        raise


def load_json(filename: str) -> Any:
    """
    Load data from JSON file
    
    Args:
        filename: Input filename
        
    Returns:
        Loaded data
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded data from {filename}")
        return data
    except Exception as e:
        logger.error(f"Failed to load JSON from {filename}: {str(e)}")
        raise


def check_article_exists_in_directus(source_url: str) -> bool:
    """
    Check if an article with the given source URL already exists in Directus
    
    Args:
        source_url: The article's source URL to check
        
    Returns:
        True if article exists, False otherwise
    """
    if not config.DIRECTUS_URL or not config.DIRECTUS_TOKEN:
        logger.warning("Directus not configured, skipping existence check")
        return False
    
    try:
        from urllib.parse import quote
        encoded_url = quote(source_url.strip(), safe='')
        check_url = f"{config.DIRECTUS_URL}/items/b60_articles?filter[source_url][_eq]={encoded_url}"
        
        headers = {
            "Authorization": f"Bearer {config.DIRECTUS_TOKEN}"
        }
        
        logger.debug(f"Checking if article exists: {source_url}")
        response = requests.get(check_url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        exists = data.get("data") and len(data.get("data", [])) > 0
        
        if exists:
            logger.info(f"Article already exists in Directus: {source_url}")
        
        return exists
        
    except Exception as e:
        logger.error(f"Error checking article existence: {str(e)}")
        return False


def convert_to_utc_plus_6(published_date: str) -> str:
    """
    Convert published date string to UTC+6 timezone
    
    Args:
        published_date: Date string to convert
        
    Returns:
        ISO formatted datetime string in UTC+6
    """
    try:
        # Try parsing ISO format first (for Prothom Alo)
        if 'T' in published_date and 'Z' in published_date:
            # ISO format: 2026-01-03T09:50:48.198Z
            date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        else:
            # RFC 2822 format: Fri, 03 Jan 2026 10:30:00 +0600
            date = datetime.strptime(published_date, "%a, %d %b %Y %H:%M:%S %z")
        
        # Add 6 hours for UTC+6 if not already in UTC+6
        if date.utcoffset().total_seconds() != 6 * 3600:
            utc_plus_6 = date + timedelta(hours=6)
        else:
            utc_plus_6 = date
        
        # Return ISO format
        return utc_plus_6.isoformat()
        
    except Exception as e:
        logger.error(f"Failed to convert date '{published_date}': {str(e)}")
        # Return current time as fallback
        return datetime.now().isoformat()


@retry_on_exception(max_retries=3, delay=2)
def create_article_in_directus(article_data: Dict) -> Dict:
    """
    Create a new article in Directus b60_articles collection
    
    Args:
        article_data: Article data dictionary with all required fields
        
    Returns:
        Response from Directus API
    """
    if not config.DIRECTUS_URL or not config.DIRECTUS_TOKEN:
        raise ValueError("Directus not configured")
    
    url = f"{config.DIRECTUS_URL}/items/b60_articles"
    
    headers = {
        "Authorization": f"Bearer {config.DIRECTUS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Prepare payload
    payload = {
        "status": "published",
        "title": article_data.get("title", ""),
        "source_url": article_data.get("link", ""),
        "banner": article_data.get("image", ""),
        "source_name": article_data.get("source", ""),
        "published_at": convert_to_utc_plus_6(article_data.get("published", "")),
        "content": article_data.get("full_text", ""),
        "category": article_data.get("category", ""),
        "summary_60_bn": article_data.get("summary_60_bn", ""),
        "summary_60_en": article_data.get("summary_60_en", ""),
        "importance": article_data.get("importance", 5),
        "clickbait_score": article_data.get("clickbait_score", 0),
        "clickbait_reason": article_data.get("clickbait_reason", ""),
        "corrected_title": article_data.get("corrected_title", ""),
        "keywords": article_data.get("keywords", []),
        "mcqs": article_data.get("mcqs", []),
    }
    
    logger.info(f"Creating article in Directus: {payload['title'][:50]}...")
    
    response = requests.post(url, json=payload, headers=headers, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    
    result = response.json()
    logger.info(f"Successfully created article in Directus (ID: {result.get('data', {}).get('id', 'Unknown')})")
    
    return result


@retry_on_exception(max_retries=3, delay=2, exceptions=(requests.exceptions.RequestException,))
def send_to_webhook(data: Any, webhook_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Send data to webhook/API endpoint
    
    Args:
        data: Data to send (will be JSON serialized)
        webhook_url: Webhook URL (default: from config)
        
    Returns:
        Response JSON
    """
    if webhook_url is None:
        webhook_url = config.WEB_APP_URL
    
    if not webhook_url:
        logger.warning("No webhook URL configured, skipping send")
        return {"success": False, "message": "No webhook URL configured"}
    
    headers = {"Content-Type": "application/json"}
    
    logger.info(f"Sending data to webhook: {webhook_url}")
    response = requests.post(webhook_url, json=data, headers=headers, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    
    result = response.json()
    
    if result.get("success"):
        logger.info(f"Webhook success: {result.get('message', 'OK')}")
    else:
        logger.error(f"Webhook error: {result.get('message', 'Unknown error')}")
    
    return result
