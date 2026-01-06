"""
BD Pratidin RSS scraper
Runs every 5 minutes
"""
import feedparser
from typing import List, Dict, Optional
from app.logger import setup_logger
from app.utils import (
    fetch_with_curl_cffi,
    parse_html,
    save_json,
    check_article_exists_in_directus,
    create_article_in_directus,
    sleep_random
)
from app.utils.gemini import generate_summary_with_gemini

logger = setup_logger(__name__)

# Configuration
RSS_URL = "https://www.bd-pratidin.com/rss.xml"
OUTPUT_FILE = "output/bdpratidin_articles.json"
SOURCE_NAME = "BD Pratidin"
MAX_ARTICLES = 5


def get_article_content(article_url: str) -> str:
    """
    Extract full article content
    
    Args:
        article_url: URL of the article
        
    Returns:
        Full article text
    """
    try:
        response = fetch_with_curl_cffi(article_url, impersonate="chrome142")
        soup = parse_html(response.text)
        
        content = soup.find("article")
        if content is not None:
            content_array = content.find_all("p")
            text_array = [p.text.strip() for p in content_array if p.text.strip()]
            full_text = "\n\n".join(text_array)
            return full_text if full_text else "No content found"
        
        return "No content found"
        
    except Exception as e:
        logger.error(f"Failed to extract content from {article_url}: {str(e)}")
        return f"Error: {e}"


def scrape_bd_pratidin() -> List[Dict]:
    """
    Scrape articles from BD Pratidin RSS feed
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting BD Pratidin scraper - fetching RSS feed from {RSS_URL}")
    
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
                "link": entry_link,
                "image": "",
                "full_text": entry.get("summary", entry.get("description", "")),
                "source": SOURCE_NAME,
                "keywords": [],
                "summary": "",
                "published": entry.get("published", "")
            }
            
            # Fetch full content
            try:
                full_text = get_article_content(entry_link)
                article_data["full_text"] = full_text
            except Exception as e:
                logger.error(f"Error fetching content from {entry_link}: {str(e)}")
                # Use RSS summary as fallback
            
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
            
            # Random delay to avoid rate limiting
            sleep_random(2, 5)
        
        logger.info(f"Scraped and synced {len(articles)} new articles from BD Pratidin")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape BD Pratidin: {str(e)}")
        raise


def run():
    """Main entry point for BD Pratidin scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_bd_pratidin()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"BD Pratidin scraper completed successfully - {len(articles)} articles processed")
        
    except Exception as e:
        logger.error(f"BD Pratidin scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
