"""
Daily Campus Bangla scraper
Scrapes from daily archive page
Runs every 6 minutes
"""
import json
import datetime
from typing import List, Dict, Tuple
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
OUTPUT_FILE = "output/dailycampus_bangla_articles.json"
SOURCE_NAME = "Daily Campus"
MAX_ARTICLES = 5


def get_todays_archive() -> str:
    """
    Generate today's archive URL
    
    Returns:
        Archive URL for today
    """
    url = 'https://thedailycampus.com/archive/'
    today = datetime.date.today()
    url = url + today.strftime('%Y-%m-%d')
    logger.debug(f"Archive URL: {url}")
    return url


def get_list_articles(url: str) -> List[str]:
    """
    Get list of article URLs from archive page
    
    Args:
        url: Archive URL
        
    Returns:
        List of article URLs
    """
    try:
        response = fetch_with_curl_cffi(url, impersonate='chrome131')
        soup = parse_html(response.content)
        
        contents = soup.find_all("h6", class_='card-title')
        links = [content.find("a")["href"] for content in contents if content.find("a")]
        
        logger.info(f"Found {len(links)} articles")
        return links
        
    except Exception as e:
        logger.error(f"Failed to get article list from {url}: {str(e)}")
        return []


def get_article(url: str) -> Tuple[str, str, str, str]:
    """
    Extract article details
    
    Args:
        url: Article URL
        
    Returns:
        Tuple of (title, image_url, full_text, published_date)
    """
    try:
        response = fetch_with_curl_cffi(url, impersonate='firefox144')
        soup = parse_html(response.content)
        
        # Get title
        titlesection = soup.find('meta', property='og:title')
        title = titlesection['content'] if titlesection else "No title"
        
        # Get image URL
        imagesection = soup.find('meta', property='og:image')
        image_url = imagesection['content'] if imagesection else "No image"
        
        # Get article content
        contents = soup.find('div', class_='news-content')
        if contents:
            content_paragraphs = contents.find_all('p')
            article_text = []
            skip_string = 'আরও পড়ুন'
            
            for p in content_paragraphs:
                if skip_string in p.text:
                    continue
                article_text.append(p.text.strip())
            
            full_text = "\n\n".join(article_text)
        else:
            full_text = "No content found"
        
        # Get published date
        pubdate = ""
        data = soup.find_all("script", type="application/ld+json")
        if len(data) > 1:
            try:
                jsonlist = json.loads(data[1].text)
                pubdate = jsonlist.get('datePublished', '')
            except Exception as e:
                logger.warning(f"Failed to parse publication date: {str(e)}")
        
        return title, image_url, full_text, pubdate
        
    except Exception as e:
        logger.error(f"Failed to extract article from {url}: {str(e)}")
        return f"Error: {e}", f"Error: {e}", f"Error: {e}", ""


def scrape_dailycampus_bangla() -> List[Dict]:
    """
    Scrape articles from Daily Campus Bangla
    
    Returns:
        List of article dictionaries
    """
    logger.info("Starting Daily Campus Bangla scraper")
    
    try:
        # Get today's article list
        archive_url = get_todays_archive()
        article_urls = get_list_articles(archive_url)
        
        articles = []
        processed_count = 0
        
        for url in article_urls:
            if processed_count >= MAX_ARTICLES:
                break
            
            # Check if article already exists in Directus
            if check_article_exists_in_directus(url):
                logger.info(f"Skipping existing article: {url}")
                continue
            
            logger.info(f"Processing new article: {url}")
            
            title, image_url, full_text, pubdate = get_article(url)
            
            if title.startswith("Error") or full_text.startswith("Error"):
                logger.error(f"Error fetching article, skipping: {url}")
                continue
            
            article_data = {
                "title": title,
                "keywords": [],
                "link": url,
                "image": image_url,
                "full_text": full_text,
                "source": SOURCE_NAME,
                "summary": "",
                "published": pubdate
            }
            
            try:
                # Generate AI summary and analysis
                logger.info(f"Generating AI summary for: {title[:50]}...")
                ai_analysis = generate_summary_with_gemini(
                    title=title,
                    full_text=full_text
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
        
        logger.info(f"Scraped and synced {len(articles)} new articles from Daily Campus Bangla")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to scrape Daily Campus Bangla: {str(e)}")
        raise


def run():
    """Main entry point for Daily Campus Bangla scraper"""
    try:
        # Scrape articles (now syncs to Directus automatically)
        articles = scrape_dailycampus_bangla()
        
        # Save to file for backup
        if articles:
            save_json(articles, OUTPUT_FILE)
        
        logger.info(f"Daily Campus Bangla scraper completed successfully - {len(articles)} articles processed")
    except Exception as e:
        logger.error(f"Daily Campus Bangla scraper failed: {str(e)}")
        raise


if __name__ == "__main__":
    run()
