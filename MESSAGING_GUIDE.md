# Messaging Guide

## Overview

The messaging spider logs into your Gumtree account and automatically sends messages to sellers from your scraped listings. It tracks which listings you've already contacted to avoid duplicates and provides detailed progress reporting.

## Prerequisites

```bash
pip install scrapy-playwright
# Install both browsers (you can choose which one to use)
playwright install chromium firefox
```

## Setup

### 1. Create Configuration File

Copy the example and edit with your details:

```bash
cp config.json.example config.json
```

```json
{
  "email": "your-email@example.com",
  "password": "your-password",
  "input_json": "gumtree_listings.json",
  "message_template": "message_template.txt",
  "max_messages": 10,
  "message_delay": 5,
  "skip_contacted": true
}
```

**Configuration Options:**

- `email`: Your Gumtree email
- `password`: Your Gumtree password
- `input_json`: JSON file with scraped listings
- `message_template`: Path to your message template
- `max_messages`: Maximum messages to send (0 = unlimited)
- `message_delay`: Seconds to wait between messages
- `skip_contacted`: Whether to skip already contacted listings

### 2. Create Message Template

Copy the example and customize:

```bash
cp message_template.txt.example message_template.txt
```

Example template:

```text
Hi there,

I'm interested in your listing: {title}
Location: {location}
Price: {price}

Could you provide more information about:
- Availability
- Any additional costs
- Viewing arrangements

Thanks!
```

**Available Placeholders:**

- `{title}` - Listing title
- `{location}` - Location
- `{price}` - Price
- `{listing_id}` - Listing ID
- `{url}` - Listing URL
- `{description}` - Description

## Usage

### Basic Usage

```bash
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
```

The spider will:
1. Log into your Gumtree account
2. Read listings from the JSON file
3. Visit each listing
4. Send your customized message
5. Track contacted listings

### Test Mode

Always test with a few messages first:

```json
{
  "max_messages": 3,
  ...
}
```

### Debug Mode

To watch what's happening:

1. Edit `gumtree_scraper/settings_playwright.py`
2. Set `"headless": False`
3. Run the spider

### Browser Selection

The messaging spider supports both **Chromium** and **Firefox**. To switch browsers:

1. Edit `gumtree_scraper/spiders/gumtree_messenger.py`
2. Change the `BROWSER` variable at the top:
   ```python
   BROWSER = "firefox"  # Options: "chromium" or "firefox"
   ```
3. Run the spider normally

**When to use Firefox:**
- If Chromium is being detected/blocked by Gumtree
- If you prefer Firefox's rendering engine
- If Chromium has issues on your system

**When to use Chromium:**
- Default choice, more mature automation
- Better anti-detection features
- Faster startup time

**Note:** Each browser has different anti-bot detection methods:
- Chromium uses `--disable-blink-features=AutomationControlled`
- Firefox uses preferences like `dom.webdriver.enabled: false`
- User agents automatically match the selected browser

### Environment Variables

Instead of config.json, you can use:

```bash
export GUMTREE_EMAIL="your-email@example.com"
export GUMTREE_PASSWORD="your-password"
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
```

## Progress Tracking

The spider provides real-time feedback:

```
================================================================================
GUMTREE MESSENGER SPIDER INITIALIZED
================================================================================
Input file: gumtree_listings.json
Max messages: 10
Message delay: 5s
Already contacted: 5 listings
================================================================================

ATTEMPTING LOGIN
Logging in as: your-email@example.com
Successfully logged in!

STARTING TO MESSAGE 10 LISTINGS

[1/10] Processing: Secure Garage Space
Message sent successfully!

[2/10] Processing: Parking Available
Message sent successfully!

================================================================================
PROGRESS SUMMARY
================================================================================
Processed: 2/10 listings
Sent: 2
Failed: 0
Skipped: 0
Elapsed time: 15.3s
================================================================================
```

### Final Report

```
================================================================================
FINAL REPORT
================================================================================
Total listings processed: 10
Messages sent successfully: 8
Messages failed: 2
Messages skipped: 0
Total time: 78.5s (1.3 minutes)
Success rate: 80.0%

Contacted listings saved to: contacted_listings.json
Detailed log saved to: messaging_log.json
================================================================================
```

## Output Files

### contacted_listings.json

Tracks all contacted listings to prevent duplicates:

```json
{
  "contacted_ids": ["1203728519", "1500554038"],
  "history": [
    {
      "listing_id": "1203728519",
      "url": "https://www.gumtree.com/p/-/...",
      "status": "success",
      "timestamp": "2025-11-08T15:30:00.123456"
    }
  ]
}
```

### messaging_log.json

Detailed log of all activity:

```json
{
  "summary": {
    "total": 10,
    "sent": 8,
    "failed": 2,
    "skipped": 0,
    "elapsed_seconds": 78.5,
    "success_rate": 80.0
  },
  "progress": [
    {
      "timestamp": "2025-11-08T15:30:00.123456",
      "message": "Login successful"
    },
    {
      "timestamp": "2025-11-08T15:30:15.123456",
      "message": "[1] SUCCESS: Secure Garage Space"
    }
  ]
}
```

## Troubleshooting

### Login Issues

**Problem**: Login fails or stays on login page

**Solutions**:
- Verify credentials in config.json
- Check for CAPTCHA (run in non-headless mode)
- Try logging in manually first
- Gumtree may have changed their login page

### Message Button Not Found

**Problem**: Spider can't find the message button

**Solutions**:
- Run in non-headless mode to see the page
- The listing may not allow messages
- You may need a verified account
- Some listings have messaging disabled

### Rate Limiting

**Problem**: Getting blocked or errors after many messages

**Solutions**:
- Increase `message_delay` to 10-15 seconds
- Send fewer messages per batch (try 5-10)
- Wait between batches
- Gumtree may have anti-spam measures

### Already Contacted Listings

**Problem**: Want to re-contact listings

**Solutions**:
- Set `skip_contacted: false` in config
- Or delete `contacted_listings.json`

### Browser Detection Issues

**Problem**: Gumtree is blocking or detecting automation

**Solutions**:
- Try switching browsers (Firefox vs Chromium)
- Edit `gumtree_scraper/spiders/gumtree_messenger.py`
- Change `BROWSER = "firefox"` or `BROWSER = "chromium"`
- Firefox and Chromium use different anti-detection methods
- Run in non-headless mode to see if CAPTCHAs appear
- Increase delays between messages (10-15 seconds)

### Browser Not Found

**Problem**: "Browser executable not found" error

**Solutions**:
- Make sure you installed the browser: `playwright install firefox` or `playwright install chromium`
- Check that the `BROWSER` variable matches an installed browser
- Try reinstalling: `playwright install --force chromium firefox`

## Batch Processing

For large numbers of listings:

```bash
# First 10
scrapy crawl gumtree_messenger ...
# Wait 1 hour
# Next 10 (automatically skips first 10)
scrapy crawl gumtree_messenger ...
```

```bash
# Step 1: Scrape listings
scrapy crawl gumtree

# Step 2: Set up config
cp config.json.example config.json
# Edit with your credentials

# Step 3: Create template
cp message_template.txt.example message_template.txt
# Customize your message

# Step 4: Test with 3 messages
# Set "max_messages": 3 in config.json
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright

# Step 5: Check results
cat messaging_log.json

# Step 6: Send to all (if successful)
# Set "max_messages": 0 in config.json
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
```

### Debug Logging

```bash
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright -s LOG_LEVEL=DEBUG
```
