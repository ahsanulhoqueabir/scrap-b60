"""
BBC World RSS scraper
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
RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"
OUTPUT_FILE = "output/bbcworld_articles.json"
SOURCE_NAME = "BBC News"
MAX_ARTICLES = 5


def get_article_image_content(url: str) -> Tuple[str, str]:
    """
    Extract image and content from BBC article
    
    Args:
        url: Article URL
        
    Returns:
        Tuple of (image_url, full_text)
    """
    try:
        response = fetch_with_fallback(url)
        soup = parse_html(response.content)
        
        # Extract image
        image = soup.find('meta', property="og:image")
        image_url = image['content'] if image else "No image found"
        
        # Extract content from BBC's specific structure
        selector = "p.sc-9a00e533-0, h2.sc-f98b1ad2-0, li.sc-734a601e-0"
        raw_text = soup.select(selector)
        clean_text = [content.text.strip() for content in raw_text if content.text.strip()]
        full_text = "\n\n".join(clean_text)
        
        return image_url, full_text
        
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {str(e)}")
        return f"Error: {e}", f"Error: {e}"


def scrape_bbc_world() -> List[Dict]:
    """
    Scrape articles from BBC World RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting BBC World scraper - fetching RSS feed from {RSS_URL}")
    
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        processed_count = 0
        
        for entry in feed.entries:
            if processed_count >= MAX_ARTICLES:
                break
            
            # Skip video content
            if "/videos" in entry.link:
                logger.debug(f"Skipping video entry: {entry.link}")
                continue
            
            title = entry.get("title", "")
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(entry.link):
                logger.info(f"Skipping existing article: {title}")
                continue
            
            logger.info(f"Processing new article: {title}")
            
            # Fetch full content and image
            try:
                article_image, article_text = get_article_image_content(entry.link)
                
                # Build article data structure
                article_data = {
                    "title": title,
                    "keywords": [],
                    "link": entry.link,
                    "image": article_image,
                    "full_text": article_text,
                    "source": SOURCE_NAME,
                    "summary": "",
                    "published": entry.get("published", "")
                }
                
                # Generate AI summary and analysis
                logger.info(f"Generating AI summary for: {title[:50]}...")
                ai_analysis = generate_summary_with_gemini(
                    title=article_data["title"],
                    full_text=article_data["full_text"]
                )
                
                # Merge AI analysis into article
                article_data.update({
                    "status": "published",
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
                
                # Random delay to avoid rate limiting
                sleep_random(2, 6)
                
            except Exception as e:
                logger.error(f"Failed to process article '{title}': {str(e)}")
                continue
        
        logger.info(f"Scraped and synced {len(articles)} new articles from BBC World")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape BBC World: {str(e)}")
        raise


def run():
    """Main entry point for BBC World scraper"""
    try:
        articles = scrape_bbc_world()
        
        # Save to local JSON file for backup/reference
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"BBC World scraper completed successfully - {len(articles)} articles processed")
        
    except Exception as e:
        logger.error(f"BBC World scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
