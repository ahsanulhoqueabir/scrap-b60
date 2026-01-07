"""
The Business Standard (TBS) Top News RSS scraper
Runs every 6 minutes
"""
import feedparser
from typing import List, Dict
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
RSS_URL = "https://www.tbsnews.net/top-news/rss.xml"
OUTPUT_FILE = "output/tbsnews_top_articles.json"
SOURCE_NAME = "The Business Standard"
MAX_ARTICLES = 10


def get_text(url: str) -> str:
    """
    Extract full text from article page
    
    Args:
        url: Article URL
        
    Returns:
        Full article text
    """
    try:
        response = fetch_with_fallback(url)
        soup = parse_html(response.content)
        
        # TBS uses specific classes for content
        selector = "p.rtejustify, li.rtejustify"
        raw_text = soup.select(selector)
        
        article_text = [data.text.strip() for data in raw_text if data.text.strip()]
        full_text = '\n\n'.join(article_text)
        
        return full_text if full_text else "No content found"
        
    except Exception as e:
        logger.error(f"Failed to extract text from {url}: {str(e)}")
        return f"Error: {e}"


def scrape_tbs_top() -> List[Dict]:
    """
    Scrape articles from TBS Top News RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting TBS Top News scraper - fetching RSS feed from {RSS_URL}")
    
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        processed_count = 0
        
        for entry in feed.entries:
            if processed_count >= MAX_ARTICLES:
                break
            
            title = entry.get("title", "")
            entry_link = entry.link
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(entry_link):
                logger.info(f"Skipping existing article: {title}")
                continue
            
            logger.info(f"Processing new article: {title}")
            
            # Extract image from media_content
            image_details = entry.get("media_content", "")
            image_url = image_details[0].get("url", "") if image_details else "No image"
            
            article_data = {
                "title": title,
                "keywords": [],
                "link": entry_link,
                "image": image_url,
                "full_text": "",
                "source": SOURCE_NAME,
                "summary": "",
                "published": entry.get("published", "")
            }
            
            # Fetch full text
            try:
                full_text = get_text(entry_link)
                article_data["full_text"] = full_text
            except Exception as e:
                logger.error(f"Error fetching content from {entry_link}: {str(e)}")
                # Use empty content as fallback
            
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
            
            sleep_random(3, 8)
        
        logger.info(f"Scraped and synced {len(articles)} new articles from TBS Top News")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape TBS Top News: {str(e)}")
        raise


def run():
    """Main entry point for TBS Top News scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_tbs_top()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"TBS Top News scraper completed successfully - {len(articles)} articles processed")
    except Exception as e:
        logger.error(f"TBS Top News scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
