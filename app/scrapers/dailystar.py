"""
The Daily Star English scraper
Runs every 5 minutes
"""
from typing import List, Dict
from app.logger import setup_logger
from app.utils import (
    fetch_with_curl_cffi,
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
BASE_URL = "https://www.thedailystar.net"
FEED_URL = "https://www.thedailystar.net/todays-news"
OUTPUT_FILE = "output/thedailystar_articles_english.json"
SOURCE_NAME = "The Daily Star"
MULTIMEDIA_URL = "multimedia/"


def get_list_articles(url: str) -> List[str]:
    """
    Get list of article URLs from the feed page
    
    Args:
        url: Feed URL
        
    Returns:
        List of article URLs
    """
    try:
        response = fetch_with_curl_cffi(url, impersonate='safari260')
        soup = parse_html(response.content)
        
        contents = soup.find_all("h3", class_='title')
        links = []
        
        for content in contents:
            link_tag = content.find("a")
            if link_tag and link_tag.get("href"):
                link = BASE_URL + link_tag["href"]
                
                # Skip multimedia links
                if MULTIMEDIA_URL in link:
                    logger.debug(f"Skipping multimedia link: {link}")
                    continue
                
                logger.debug(f"Found article: {link}")
                links.append(link)
        
        logger.info(f"Found {len(links)} article links")
        return links
        
    except Exception as e:
        logger.error(f"Failed to get article list from {url}: {str(e)}")
        raise


def get_article_details(article_url: str) -> Dict:
    """
    Extract article details from article page
    
    Args:
        article_url: URL of the article
        
    Returns:
        Dictionary with article details
    """
    try:
        response = fetch_with_curl_cffi(article_url, impersonate='chrome142')
        soup = parse_html(response.content)
        
        # Extract title
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "No Title"
        
        # Extract image
        image_url = extract_og_image(soup) or "No image found"
        
        # Extract content
        contents = soup.find_all('p', class_=False)
        # print(contents)
        article_text = []
        for p in contents:
            article_text.append(p.text)

        # print(article_text)
        full_text = "\n\n".join(article_text)
        if not full_text:
            full_text = "No content found"
        
        article_data = {
            "title": title,
            "link": article_url,
            "image": image_url,
            "full_text": full_text,
            "source": SOURCE_NAME,
            "keywords": [],
            "summary": "",
            "published": ""
        }
        
        return article_data
        
    except Exception as e:
        logger.error(f"Failed to extract details from {article_url}: {str(e)}")
        return {
            "title": "Error",
            "link": article_url,
            "error": str(e),
            "source": SOURCE_NAME
        }


def scrape_dailystar() -> List[Dict]:
    """
    Scrape articles from The Daily Star
    
    Returns:
        List of article dictionaries
    """
    logger.info(f"Starting Daily Star scraper - fetching from {FEED_URL}")
    
    try:
        # Get article URLs
        article_urls = get_list_articles(FEED_URL)
        articles = []
        processed_count = 0
        
        # Fetch details for each article
        for url in article_urls:
            if processed_count >= 5:
                break
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(url):
                logger.info(f"Skipping existing article: {url}")
                continue
            
            logger.info(f"Processing new article: {url}")
            article = get_article_details(url)
            
            if article.get("error"):
                logger.error(f"Error fetching article, skipping: {url}")
                continue
            
            try:
                # Generate AI summary and analysis
                logger.info(f"Generating AI summary for: {article['title'][:50]}...")
                ai_analysis = generate_summary_with_gemini(
                    title=article["title"],
                    full_text=article["full_text"]
                )
                
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
                
                # Create article in Directus
                create_article_in_directus(article)
                logger.info(f"✓ Successfully processed and synced: {article['title'][:50]}...")
                
                articles.append(article)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process article '{article['title']}': {str(e)}")
                continue
            
            # Random delay
            sleep_random(2, 5)
        
        logger.info(f"Scraped and synced {len(articles)} new articles from Daily Star")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape Daily Star: {str(e)}")
        raise


def run():
    """Main entry point for Daily Star scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_dailystar()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"Daily Star scraper completed successfully - {len(articles)} articles processed")
        
    except Exception as e:
        logger.error(f"Daily Star scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
