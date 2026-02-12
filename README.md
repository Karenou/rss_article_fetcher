# RSS Article Fetcher

A Python-based RSS article fetcher that automatically retrieves articles from subscribed RSS feeds, generates English summaries using Google Gemini AI, and pushes notifications to Enterprise WeChat.

## Features

- 📰 **RSS Feed Parsing**: Supports OPML and plain text RSS subscription formats
- 🕐 **Flexible Time Ranges**: Fetch articles from specific time periods
- 🌐 **Content Extraction**: Automatically extracts article content from web pages
- 🤖 **AI Summarization**: Generates English summaries using Google Gemini API
- 🌍 **Multi-language Support**: Automatically detects and translates non-English content
- 💬 **WeChat Integration**: Pushes formatted notifications to Enterprise WeChat
- 🔄 **Deduplication**: Prevents duplicate article processing
- ⏰ **Scheduled Execution**: Supports cron and interval-based scheduling
- 📊 **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Enterprise WeChat webhook URL (optional)

### Setup

1. Clone or download this repository:
```bash
git clone https://github.com/Karenou/rss_article_fetcher.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
```bash
cp config/config.yaml.example config/config.yaml
```

4. Edit `config/config.yaml` with your settings:
   - Add your Google Gemini API key
   - Add your Enterprise WeChat webhook URL
   - Adjust other settings as needed

## Configuration

### Configuration File

The main configuration file is `config/config.yaml`. Key settings include:

```yaml
# Enterprise WeChat Settings
wecom:
  webhook_url: 'YOUR_WEBHOOK_URL'

# RSS Settings
rss:
  file_path: './data/subscribe_rss.txt'

# AI Settings
ai:
  gemini_api_key: 'YOUR_API_KEY'
  gemini_model: 'gemini-2.5-flash'
  summary_min_length: 100
  summary_max_length: 300

# Scheduler Settings
scheduler:
  enabled: false
  interval_hours: 24
```

### Environment Variables

You can also set sensitive information via environment variables:

```bash
export GEMINI_API_KEY="your_api_key_here"
export WECOM_WEBHOOK_URL="your_webhook_url_here"
```

### RSS Subscription File

The RSS subscription file (`subscribe_rss.txt`) supports OPML format:

```xml
<outline type="rss" text="idiallo.com" title="idiallo.com" xmlUrl="https://idiallo.com/feed.rss" htmlUrl="https://idiallo.com"/>
<outline type="rss" text="pluralistic.net" title="pluralistic.net" xmlUrl="https://pluralistic.net/feed/" htmlUrl="https://pluralistic.net"/>
```

## Usage

### Basic Usage

Fetch articles from the last 24 hours:
```bash
python main.py
```

### Specify Time Range

Fetch articles from a specific date range:
```bash
python main.py --start "2024-01-01" --end "2024-01-02"
```

Fetch articles from the last 2 days:
```bash
python main.py --start "2 days ago"
```

### Advanced Options

```bash
# Force reprocess articles (ignore deduplication)
python main.py --force

# Dry run (don't push to WeChat)
python main.py --no-push

# Debug mode
python main.py --debug

# Custom configuration file
python main.py --config /path/to/config.yaml

# Specify time range in hours
python main.py --hours 48

# only want to push previously processed articles from database without scrapying again
python main.py --push_only --start "2026-02-08" --end "2026-02-10"
```

### Scheduled Mode

Enable scheduled execution in `config/config.yaml`:

```yaml
scheduler:
  enabled: true
  interval_hours: 24  # Run every 24 hours
```

Or use cron expression:

```yaml
scheduler:
  enabled: true
  cron: '0 9 * * *'  # Run daily at 9:00 AM
```

Then run:
```bash
python main.py
```

## Project Structure

```
rss_article_fetcher/
├── main.py                 # Main program entry
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── config/                # Configuration files
│   ├── config.yaml        # Main configuration
│   └── config.yaml.example # Configuration template
├── logs/                  # Log files
├── data/                  # Data storage
│   ├── rss.txt            # full RSS links file
│   ├── subscribe_rss.txt  # RSS subscription file
│   └── processed_articles.db  # SQLite database
└── src/                   # Source code
    ├── config_manager.py  # Configuration management
    ├── logger.py          # Logging system
    ├── rss_manager.py     # RSS subscription management
    ├── time_parser.py     # Time range parsing
    ├── rss_fetcher.py     # RSS feed fetching
    ├── content_fetcher.py # Article content extraction
    ├── summarizer.py      # AI summarization
    ├── storage.py         # Data persistence
    ├── wecom_pusher.py    # WeChat notifications
    └── scheduler.py       # Task scheduling
```

## How It Works

1. **Load RSS Sources**: Reads and parses RSS subscription file
2. **Parse Time Range**: Determines the time period for article fetching
3. **Fetch RSS Feeds**: Retrieves articles from all RSS sources
4. **Filter Duplicates**: Checks database to skip already processed articles
5. **Extract Content**: Fetches full article content from web pages
6. **Generate Summaries**: Uses Google Gemini to create English summaries
7. **Save to Database**: Stores processed articles for deduplication
8. **Push to WeChat**: Sends formatted notifications to Enterprise WeChat

## Troubleshooting

### No articles found

- Check that your RSS subscription file exists and is properly formatted
- Verify the time range includes the article publication dates
- Check logs in `logs/` directory for errors

### Gemini API errors

- Verify your API key is correct
- Check your API quota and rate limits
- Ensure you have internet connectivity

### WeChat push failures

- Verify your webhook URL is correct
- Check that the webhook is not rate-limited
- Review WeChat API error messages in logs

### Content extraction issues

- Some websites may block automated access
- Try adjusting the `User-Agent` header in the code
- Check if the website requires authentication

## Database Management

### View Statistics

```python
from src.storage import Storage
from src.logger import get_logger

logger = get_logger()
storage = Storage("/rss_article_fetcher/data", logger)
stats = storage.get_statistics()
print(stats)
```

### Clean Old Records

```python
# Remove records older than 90 days
storage.cleanup_old_records(days=90)
```

### Reset Database

```python
# Delete all records
storage.reset_database()
```

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [feedparser](https://github.com/kurtmckee/feedparser) - RSS/Atom feed parsing
- [newspaper3k](https://github.com/codelucas/newspaper) - Article extraction
- [Google Gemini](https://ai.google.dev/) - AI summarization
- [APScheduler](https://github.com/agronholm/apscheduler) - Task scheduling

## Support

For issues and questions, please check the logs in the `logs/` directory first. Most problems can be diagnosed from the detailed error messages there.
