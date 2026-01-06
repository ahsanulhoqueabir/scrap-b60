# Bangladeshi News Scraper - Docker Cron Edition

Automated news scraping system running on Docker with cron jobs. No API endpoints - purely scheduled scraping.

## 🎯 Features

- ✅ **Automated Cron Jobs** - Different intervals (10-15 min) for each scraper
- ✅ **Overlap Prevention** - File locking prevents concurrent runs
- ✅ **Docker-based** - Easy deployment
- ✅ **Coolify Ready** - Deploy on Hostinger Coolify
- ✅ **Multiple Sources** - Prothom Alo, Daily Star, BD Pratidin, TBS, Jagonews24, BBC
- ✅ **AI Analysis** - Gemini AI integration
- ✅ **Directus Sync** - Auto sync to Directus CMS
- ✅ **No Exposed Ports** - Purely cron-based

## 🚀 Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

Add your API keys:

```env
DIRECTUS_URL=https://your-directus.com
DIRECTUS_API_TOKEN=your-token
GEMINI_API_KEYS=AIzaSyXXX,AIzaSyYYY
```

### 2. Run with Docker Compose

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

### 3. Verify

```bash
# Check cron is running
docker exec news_scraper pgrep cron

# View logs
tail -f logs/cron.log
tail -f logs/app.log
```

## 📅 Scraper Schedule

| Scraper     | Interval | Offset | Lock File              |
| ----------- | -------- | ------ | ---------------------- |
| Prothom Alo | 10 min   | 0      | `/tmp/prothomalo.lock` |
| Daily Star  | 15 min   | 0      | `/tmp/dailystar.lock`  |
| BD Pratidin | 15 min   | 5 min  | `/tmp/bdpratidin.lock` |
| BD24Live    | 15 min   | 7 min  | `/tmp/bd24live.lock`   |
| Jagonews24  | 15 min   | 3 min  | `/tmp/jagonews.lock`   |
| TBS News    | 20 min   | 0      | `/tmp/tbs.lock`        |
| BBC World   | 30 min   | 0      | `/tmp/bbc.lock`        |

Time offsets prevent scrapers from running simultaneously.

## 🐳 Coolify Deployment (Hostinger)

### Step 1: Push to Git

```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### Step 2: Create Project in Coolify

1. Login to Coolify
2. **New Project** → **Docker Compose**
3. Connect Git repository
4. Select branch: `main`
5. Base directory: `/`

### Step 3: Add Environment Variables

In Coolify dashboard:

```
DIRECTUS_URL=https://your-directus.com
DIRECTUS_API_TOKEN=your-token
GEMINI_API_KEYS=AIzaSyXXX,AIzaSyYYY
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
MAX_RETRIES=3
RETRY_DELAY=2
REQUEST_TIMEOUT=30
```

### Step 4: Deploy

Click **"Deploy"** and wait for build.

### Step 5: Monitor

```bash
# Via Coolify dashboard logs
# Or SSH to server:
docker logs news_scraper -f
```

## 🔧 Customize Scraper Intervals

Edit `crontab`:

```bash
nano crontab
```

Cron syntax:

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ Day of week (0-7)
│ │ │ └─── Month (1-12)
│ │ └───── Day (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

Examples:

```bash
*/5 * * * *    # Every 5 minutes
*/10 * * * *   # Every 10 minutes
0 */2 * * *    # Every 2 hours
```

Rebuild after changes:

```bash
docker-compose restart
```

## 📊 Monitoring

### View Logs

```bash
# Cron logs
docker exec news_scraper tail -f /app/logs/cron.log

# Application logs
docker exec news_scraper tail -f /app/logs/app.log

# Docker logs
docker logs news_scraper --tail 100 -f
```

### Check Status

```bash
# Cron running?
docker exec news_scraper pgrep cron

# List cron jobs
docker exec news_scraper crontab -l

# Running processes
docker exec news_scraper ps aux | grep python
```

### Manual Run

```bash
# Test specific scraper
docker exec news_scraper python /app/app/scrapers/prothomalo_bangla.py
```

## 🐛 Troubleshooting

### Cron Not Running

```bash
docker exec news_scraper pgrep cron
docker-compose restart
```

### Scraper Failing

```bash
# Check logs
docker exec news_scraper tail -100 /app/logs/app.log

# Test manually
docker exec -it news_scraper python /app/app/scrapers/dailystar.py
```

### Lock Files Stuck

```bash
# Remove locks
docker exec news_scraper rm -f /tmp/*.lock
docker-compose restart
```

### Container Restarting

```bash
docker logs news_scraper --tail 50
docker inspect news_scraper | grep -A 10 Health
```

## 🔒 Security

1. Never commit `.env`
2. Rotate API tokens regularly
3. Monitor logs for errors
4. Keep Docker images updated

## 📦 Backup

```bash
# Backup output
tar -czf backup_$(date +%Y%m%d).tar.gz output/ logs/

# Download from server
scp user@server:~/backup_*.tar.gz ./
```

## 🎯 Architecture

```
Docker Container
    │
    ├── Cron Service (foreground)
    │   ├── Timer: Prothom Alo (10min)
    │   ├── Timer: Daily Star (15min)
    │   ├── Timer: BD Pratidin (15min+5)
    │   └── ...
    │
    ├── Python Scrapers
    │   ├── flock (overlap prevent)
    │   ├── Gemini AI
    │   └── Directus Sync
    │
    └── Logs & Output
```

## 💡 Tips

1. Start with 30min intervals, adjust as needed
2. Use multiple Gemini keys for better rate limits
3. Monitor logs regularly
4. Time offsets prevent simultaneous runs
5. `flock` ensures no overlap

## 📝 Project Structure

```
briefly60-scrapper/
├── app/
│   ├── scrapers/          # Scraper modules
│   ├── utils/             # Utilities (Gemini, helpers)
│   ├── config.py
│   ├── logger.py
│   └── retry.py
├── logs/                  # Application logs
├── output/                # Scraped data
├── Dockerfile
├── docker-compose.yml
├── crontab                # Cron schedule
├── entrypoint.sh          # Container startup
├── requirements.txt
├── .env.example
└── README.md
```

## 🎉 Done!

Your scraper runs 24/7 with:

- ✅ Automated scheduling
- ✅ No manual intervention
- ✅ No exposed endpoints
- ✅ Overlap prevention
- ✅ Docker containerized

**Deploy and forget!** 🚀

---

**License:** MIT
