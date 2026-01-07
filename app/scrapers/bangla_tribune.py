"""
Bangla Tribune RSS scraper
Runs every 5 minutes
"""
import feedparser
from typing import List, Dict, Tuple
from app.logger import setup_logger
from app.utils import (
    fetch_with_fallback,
    parse_html,
    save_json,
    check_article_exists_in_directus,
    create_article_in_directus,
    sleep_random
)
from app.utils.gemini import generate_summary_with_gemini

logger = setup_logger(__name__)

# Configuration
RSS_URL = "https://www.banglatribune.com/feed/"
OUTPUT_FILE = "output/banglatribune_articles.json"
SOURCE_NAME = "Bangla Tribune"
MAX_ARTICLES = 5


def get_article_image_fulltext(url: str) -> Tuple[str, str]:
    """
    Extract image and full text from article page with fallback strategies
    
    Args:
        url: Article URL
        
    Returns:
        Tuple of (image_url, full_text)
    """
    try:
        # Try multiple impersonation strategies
        impersonate_options = ['safari260', 'chrome142', 'safari15_5']
        last_error = None
        
        for impersonate in impersonate_options:
            try:
                logger.debug(f"Attempting to fetch with curl_cffi ({impersonate}): {url}")
                response = fetch_with_fallback(url)
                soup = parse_html(response.content)
                
                # Extract image
                image = soup.find("meta", property="og:image")
                image_url = image["content"] if image else "No image found"
                logger.debug(f"Extracted image: {image_url}")
                
                # Extract content
                raw_text = soup.find_all('p', class_='alignfull')
                clean_text = [p.text.strip() for p in raw_text if p.text.strip()]
                full_text = '\n\n'.join(clean_text)
                logger.debug(f"Extracted {len(clean_text)} paragraphs with {impersonate}")
                
                return image_url, full_text
                
            except Exception as e:
                last_error = e
                logger.warning(f"Impersonate {impersonate} failed: {str(e)[:100]}")
                continue
        
        # All impersonation options failed
        raise last_error
        
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {str(e)}")
        return "Error", f"Error: {e}"


def scrape_bangla_tribune() -> List[Dict]:
    """
    Scrape articles from Bangla Tribune RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting Bangla Tribune scraper - fetching RSS feed from {RSS_URL}")
    
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        processed_count = 0
        
        for entry in feed.entries:
            if processed_count >= MAX_ARTICLES:
                break
            
            title = entry.get("title", "")
            entry_link = entry.get("link", "")
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(entry_link):
                logger.info(f"Skipping existing article: {title}")
                continue
            
            logger.info(f"Processing new article: {title}")
            
            # Build article data structure
            article_data = {
                "title": title,
                "keywords": [],
                "link": entry_link,
                "image": "",
                "full_text": "",
                "source": SOURCE_NAME,
                "summary": "",
                "published": entry.get("published", "")
            }
            
            # Fetch full content and image
            try:
                image_url, full_text = get_article_image_fulltext(entry_link)
                
                # Skip articles with no content
                if not full_text or full_text.startswith("Error"):
                    logger.warning(f"Skipping article with no content: {title}")
                    continue
                    
                article_data["image"] = image_url
                article_data["full_text"] = full_text
            except Exception as e:
                logger.error(f"Error fetching content from {entry_link}: {str(e)}")
                continue
            
            try:
                # Generate AI summary and analysis
                logger.info(f"Generating AI summary for: {title[:50]}...")
                ai_analysis = generate_summary_with_gemini(
                    title=article_data["title"],
                    full_text=article_data["full_text"]
                )
                
                # Merge AI analysis into article
                article_data.update({
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
                
                # Create article in Directus
                create_article_in_directus(article_data)
                logger.info(f"✓ Successfully processed and synced: {title[:50]}...")
                
                articles.append(article_data)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process article '{title}': {str(e)}")
                continue
            
            sleep_random(4, 7)
        
        logger.info(f"Scraped and synced {len(articles)} new articles from Bangla Tribune")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape Bangla Tribune: {str(e)}")
        raise


def run():
    """Main entry point for Bangla Tribune scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_bangla_tribune()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"Bangla Tribune scraper completed successfully - {len(articles)} articles processed")
    except Exception as e:
        logger.error(f"Bangla Tribune scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
