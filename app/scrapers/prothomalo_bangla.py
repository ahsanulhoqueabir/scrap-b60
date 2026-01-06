"""
Prothom Alo Bangla RSS scraper
Runs every 5 minutes
"""
import feedparser
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.logger import setup_logger
from app.utils import (
    fetch_with_requests,
    parse_html,
    extract_og_image,
    extract_paragraphs,
    save_json,
    check_article_exists_in_directus,
    create_article_in_directus,
    sleep_random
)
from app.utils.gemini import generate_summary_with_gemini

logger = setup_logger(__name__)

# Configuration
RSS_URL = "https://prod-qt-images.s3.amazonaws.com/production/prothomalo-bangla/feed.xml"
OUTPUT_FILE = "output/prothomalo_bangla.json"
SOURCE_NAME = "Prothom Alo"
MAX_ARTICLES = 5
VIDEO_SUBSTRING = "https://www.prothomalo.com/video"
PHOTO_SUBSTRING = "https://www.prothomalo.com/photo"


def get_image_and_content(article_url: str) -> Tuple[str, str]:
    """
    Extract image and full content from article page
    
    Args:
        article_url: URL of the article
        
    Returns:
        Tuple of (image_url, full_content)
    """
    try:
        response = fetch_with_requests(article_url)
        soup = parse_html(response.text)
        
        # Extract image
        image_url = extract_og_image(soup)
        if not image_url:
            image_url = "NO IMAGE"
        
        # Extract content
        full_article = extract_paragraphs(soup)
        if not full_article:
            full_article = "NO CONTENT"
        
        return image_url, full_article
        
    except Exception as e:
        logger.error(f"Failed to extract content from {article_url}: {str(e)}")
        return f"Error: {e}", f"Error: {e}"


def scrape_prothomalo_bangla() -> List[Dict]:
    """
    Scrape articles from Prothom Alo Bangla RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting Prothom Alo Bangla scraper - fetching RSS feed from {RSS_URL}")
    
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        processed_count = 0
        
        for entry in feed.entries:
            if processed_count >= MAX_ARTICLES:
                break
            
            # Skip video and photo entries
            entry_link = entry.get("link", "")
            if VIDEO_SUBSTRING in entry_link or PHOTO_SUBSTRING in entry_link:
                logger.debug(f"Skipping video/photo entry: {entry_link}")
                continue
            
            title = entry.get("title", "")
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(entry_link):
                logger.info(f"Skipping existing article: {title}")
                continue
            
            logger.info(f"Processing new article: {title}")
            
            # Fetch full content and image
            try:
                image_url, full_text = get_image_and_content(entry_link)
                
                # Build article data structure
                article_data = {
                    "title": title,
                    "keywords": [],
                    "link": entry_link,
                    "image": image_url,
                    "full_text": full_text,
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
        
        logger.info(f"Scraped and synced {len(articles)} new articles from Prothom Alo Bangla")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape Prothom Alo Bangla: {str(e)}")
        raise


def run():
    """Main entry point for Prothom Alo Bangla scraper"""
    try:
        articles = scrape_prothomalo_bangla()
        
        # Save to local JSON file for backup/reference
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"Prothom Alo Bangla scraper completed successfully - {len(articles)} articles processed")
        
    except Exception as e:
        logger.error(f"Prothom Alo Bangla scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
