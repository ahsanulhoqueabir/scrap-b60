"""
Jago News 24 RSS scraper
Runs every 5 minutes
"""
import feedparser
from typing import List, Dict
from app.logger import setup_logger
from app.utils import (
    save_json,
    check_article_exists_in_directus,
    create_article_in_directus
)
from app.utils.gemini import generate_summary_with_gemini

logger = setup_logger(__name__)

# Configuration
RSS_URL = "https://www.jagonews24.com/rss/rss.xml"
OUTPUT_FILE = "output/jagonews24_articles.json"
SOURCE_NAME = "Jago News 24"
MAX_ARTICLES = 5


def scrape_jagonews24() -> List[Dict]:
    """
    Scrape articles from Jago News 24 RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting Jago News 24 scraper - fetching RSS feed from {RSS_URL}")
    
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        processed_count = 0
        
        for entry in feed.entries:
            if processed_count >= MAX_ARTICLES:
                break
            
            title = entry.get("title", "")
            link = entry.get("link", "")
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(link):
                logger.info(f"Skipping existing article: {title}")
                continue
            
            logger.info(f"Processing new article: {title}")
            
            # Extract image from media_content
            imglist = entry.get("media_content", [])
            image_url = imglist[0].get("url") if imglist else "No image"
            
            # Create base article data
            article_data = {
                "title": title,
                "keywords": [],
                "link": link,
                "image": image_url,
                "full_text": entry.get("summary", entry.get("description", "")),
                "source": SOURCE_NAME,
                "summary": "",
                "published": entry.get("published", "")
            }
            
            try:
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
                
                logger.info(f"{article_data['mcqs']}")
                # Create article in Directus
                create_article_in_directus(article_data)
                logger.info(f"✓ Successfully processed and synced: {title[:50]}...")
                
                articles.append(article_data)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process article '{title}': {str(e)}")
                continue
        
        logger.info(f"Scraped and synced {len(articles)} new articles from Jago News 24")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape Jago News 24: {str(e)}")
        raise


def run():
    """Main entry point for Jago News 24 scraper"""
    try:
        articles = scrape_jagonews24()
        
        # Save to local JSON file for backup/reference
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"Jago News 24 scraper completed successfully - {len(articles)} articles processed")
        
    except Exception as e:
        logger.error(f"Jago News 24 scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
