"""
Main application entry point
Orchestrates all scrapers with scheduling
Each scraper runs every 10 minutes with 1-minute stagger
"""
import time
from datetime import datetime
import schedule
from app.logger import setup_logger
from app.scrapers import (
    prothomalo_bangla,
    # prothomalo_english,
    # dailystar,
    # dailystar_bangla,
    # bd_pratidin,
    # bangla_tribune,
    # bbc_world,
    # bbc_topnews,
    # bd24live,
    # bd24live_bangla,
    # dailycampus_bangla,
    jagonews24,
    # tbs_top,
    # tbs_bangladesh
)

logger = setup_logger(__name__)


# Scraper wrapper functions
def run_prothomalo_bangla_scraper():
    try:
        logger.info("=" * 50)
        logger.info("Running Prothom Alo Bangla scraper")
        logger.info("=" * 50)
        prothomalo_bangla.run()
    except Exception as e:
        logger.error(f"Prothom Alo Bangla scraper failed: {str(e)}")


# def run_prothomalo_english_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running Prothom Alo English scraper")
#         logger.info("=" * 50)
#         prothomalo_english.run()
#     except Exception as e:
#         logger.error(f"Prothom Alo English scraper failed: {str(e)}")


# def run_dailystar_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running Daily Star English scraper")
#         logger.info("=" * 50)
#         dailystar.run()
#     except Exception as e:
#         logger.error(f"Daily Star English scraper failed: {str(e)}")


# def run_dailystar_bangla_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running Daily Star Bangla scraper")
#         logger.info("=" * 50)
#         dailystar_bangla.run()
#     except Exception as e:
#         logger.error(f"Daily Star Bangla scraper failed: {str(e)}")


# def run_bd_pratidin_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running BD Pratidin scraper")
#         logger.info("=" * 50)
#         bd_pratidin.run()
#     except Exception as e:
#         logger.error(f"BD Pratidin scraper failed: {str(e)}")


# def run_bangla_tribune_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running Bangla Tribune scraper")
#         logger.info("=" * 50)
#         bangla_tribune.run()
#     except Exception as e:
#         logger.error(f"Bangla Tribune scraper failed: {str(e)}")


# def run_bbc_world_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running BBC World scraper")
#         logger.info("=" * 50)
#         bbc_world.run()
#     except Exception as e:
#         logger.error(f"BBC World scraper failed: {str(e)}")


# def run_bbc_topnews_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running BBC Top News scraper")
#         logger.info("=" * 50)
#         bbc_topnews.run()
#     except Exception as e:
#         logger.error(f"BBC Top News scraper failed: {str(e)}")


# def run_bd24live_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running BD24Live English scraper")
#         logger.info("=" * 50)
#         bd24live.run()
#     except Exception as e:
#         logger.error(f"BD24Live English scraper failed: {str(e)}")


# def run_bd24live_bangla_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running BD24Live Bangla scraper")
#         logger.info("=" * 50)
#         bd24live_bangla.run()
#     except Exception as e:
#         logger.error(f"BD24Live Bangla scraper failed: {str(e)}")


# def run_dailycampus_bangla_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running Daily Campus Bangla scraper")
#         logger.info("=" * 50)
#         dailycampus_bangla.run()
#     except Exception as e:
#         logger.error(f"Daily Campus Bangla scraper failed: {str(e)}")


def run_jagonews24_scraper():
    try:
        logger.info("=" * 50)
        logger.info("Running Jago News 24 scraper")
        logger.info("=" * 50)
        jagonews24.run()
    except Exception as e:
        logger.error(f"Jago News 24 scraper failed: {str(e)}")


# def run_tbs_top_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running TBS Top News scraper")
#         logger.info("=" * 50)
#         tbs_top.run()
#     except Exception as e:
#         logger.error(f"TBS Top News scraper failed: {str(e)}")


# def run_tbs_bangladesh_scraper():
#     try:
#         logger.info("=" * 50)
#         logger.info("Running TBS Bangladesh scraper")
#         logger.info("=" * 50)
#         tbs_bangladesh.run()
#     except Exception as e:
#         logger.error(f"TBS Bangladesh scraper failed: {str(e)}")


def main():
    """Main application loop with scheduling - 10 minute intervals with 1-minute stagger"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting News Scraper Application")
        logger.info(f"📅 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🌍 Timezone: Asia/Dhaka")
        logger.info("⏰ Schedule: Every 10 minutes with 1-minute stagger between scrapers")
        logger.info("=" * 60)
        
        # Define all scrapers with their stagger minutes (0-13)
        scrapers = [
            (0, run_prothomalo_bangla_scraper, "Prothom Alo Bangla"),
            (1, run_jagonews24_scraper, "Jago News 24"),
            # Uncomment to enable more scrapers
            # (2, run_prothomalo_english_scraper, "Prothom Alo English"),
            # (3, run_dailystar_scraper, "Daily Star English"),
            # (4, run_dailystar_bangla_scraper, "Daily Star Bangla"),
            # (5, run_bd_pratidin_scraper, "BD Pratidin"),
            # (6, run_bangla_tribune_scraper, "Bangla Tribune"),
            # (7, run_bbc_world_scraper, "BBC World"),
            # (8, run_bbc_topnews_scraper, "BBC Top News"),
            # (9, run_bd24live_scraper, "BD24Live English"),
            # (10, run_bd24live_bangla_scraper, "BD24Live Bangla"),
            # (11, run_dailycampus_bangla_scraper, "Daily Campus Bangla"),
            # (12, run_tbs_top_scraper, "TBS Top News"),
            # (13, run_tbs_bangladesh_scraper, "TBS Bangladesh"),
        ]
        
        logger.info(f"📊 Active Scrapers: {len(scrapers)}")
        logger.info("")
        
        # Schedule each scraper with 1-minute stagger
        # Format: At :00, :01, :02... past every 10 minutes (X:00, X:10, X:20, X:30, X:40, X:50)
        for stagger_min, scraper_func, scraper_name in scrapers:
            # Schedule at specific minutes of each hour
            for minute_mark in [0, 10, 20, 30, 40, 50]:
                target_minute = (minute_mark + stagger_min) % 60
                schedule.every().hour.at(f":{target_minute:02d}").do(scraper_func)
            
            logger.info(f"✅ Scheduled: {scraper_name} at :{stagger_min:02d} past X:00, X:10, X:20, X:30, X:40, X:50")
        
        # Run initial scrape for all active scrapers with stagger
        logger.info("\n" + "=" * 60)
        logger.info("🔄 Running initial scrape with stagger...")
        logger.info("=" * 60 + "\n")
        
        for idx, (stagger_min, scraper_func, scraper_name) in enumerate(scrapers, 1):
            logger.info(f"▶️  [{idx}/{len(scrapers)}] Starting {scraper_name}...")
            try:
                scraper_func()
                logger.info(f"✅ {scraper_name} completed successfully\n")
            except Exception as e:
                logger.error(f"❌ {scraper_name} failed: {str(e)}\n")
            
            # Sleep for 1 minute between scrapers (except after last one)
            if idx < len(scrapers):
                logger.info(f"⏳ Waiting 60 seconds before next scraper...\n")
                time.sleep(60)
        
        # Keep running scheduled tasks
        logger.info("\n" + "=" * 60)
        logger.info("♻️  Entering main loop - scrapers will run on schedule")
        logger.info(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
            
    except Exception as e:
        logger.error(f"💥 Application crashed: {str(e)}")
        logger.exception("Full traceback:")
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {str(e)}")
        raise
