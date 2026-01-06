"""
BD24Live English RSS scraper
Runs every 6 minutes
"""
import feedparser
from typing import List, Dict
from app.logger import setup_logger
from app.utils import (
    fetch_with_requests,
    parse_html,
    extract_og_image,
    save_json,
    check_article_exists_in_directus,
    create_article_in_directus,
    sleep_random
)
from app.utils.gemini import generate_summary_with_gemini

logger = setup_logger(__name__)

# Configuration
RSS_URL = "https://www.bd24live.com/feed/"
OUTPUT_FILE = "output/bd24live_articles.json"
SOURCE_NAME = "bd24live"
MAX_ARTICLES = 5


def get_main_image(article_url: str) -> str:
    """
    Extract main image from article page
    
    Args:
        article_url: URL of the article
        
    Returns:
        Image URL
    """
    try:
        response = fetch_with_requests(article_url)
        soup = parse_html(response.text)
        
        # Method 1: Check Open Graph Meta Tags
        image_url = extract_og_image(soup)
        if image_url:
            return image_url
        
        # Method 2: Check for featured image containers
        featured_div = soup.find("div", class_="post-image") or soup.find("div", class_="post-thumbnail")
        if featured_div:
            img_tag = featured_div.find("img")
            if img_tag and img_tag.get("src"):
                return img_tag["src"]
        
        return "No image found"
        
    except Exception as e:
        logger.error(f"Failed to extract image from {article_url}: {str(e)}")
        return f"Error: {e}"


def scrape_bd24live() -> List[Dict]:
    """
    Scrape articles from BD24Live English RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting BD24Live English scraper - fetching RSS feed from {RSS_URL}")
    
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
            
            article_data = {
                "title": title,
                "keywords": [],
                "link": entry_link,
                "image": "",
                "full_text": entry.get("description", ""),
                "source": SOURCE_NAME,
                "summary": "",
                "published": entry.get("published", "")
            }
            
            # Fetch main image
            try:
                image_url = get_main_image(entry_link)
                article_data["image"] = image_url
            except Exception as e:
                logger.error(f"Error fetching image for {entry_link}: {str(e)}")
                article_data["image"] = "No image found"
            
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
            
            sleep_random(2, 5)
        
        logger.info(f"Scraped and synced {len(articles)} new articles from BD24Live English")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape BD24Live English: {str(e)}")
        raise


def run():
    """Main entry point for BD24Live English scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_bd24live()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"BD24Live English scraper completed successfully - {len(articles)} articles processed")
    except Exception as e:
        logger.error(f"BD24Live English scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
