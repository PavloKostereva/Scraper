# Gumtree Scraper & Automated Messenger

A scraper written using scrapy for scraping garage and parking space listings from Gumtree

## Features

### Scraping
- Extracts listing data from JSON (it's embedded inside the HTML thank you lord gumtree)
- Collects title, price, location, date posted, contact name and full description from json and listing url
- Automatic pagination through all listings
- Exports to JSON so it could be used later to message the sellers

### Automated Messaging
NB! Automated messaging is currently untested and just braindead claude code so can't verify it actually works. will test it later with my own gumtree acc and listing.
- Logs into Gumtree automatically
- Sends bulk messages to sellers from scraped listings
- Customizable message templates with dynamic placeholders
- Tracks contacted listings to prevent duplicates
- Real-time progress tracking and detailed reporting
- Configurable rate limiting

## Installation

Install the basic dependencies:

Note: If running scrapy crawl gumtree fails then try using python 3.12.0 and reinstall the requirements and see if it works then

```bash
pip install -r requirements.txt
```

For the messaging features, also install Playwright:

```bash
pip install scrapy-playwright
# Install both browsers (you can choose which one to use in the code)
playwright install chromium firefox
```

## Quick Start

### Scraping Listings

```bash
# Basic scraping (recommended)
scrapy crawl gumtree
```

The scraped data will be saved to `gumtree_listings.json`.

### Sending Messages

After scraping, you can automatically message sellers:

```bash
# Set up configuration
cp config.json.example config.json
# Edit config.json with your credentials

# Create message template
cp message_template.txt.example message_template.txt
# Customize your message

# Send messages
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
```

For complete messaging documentation, see [MESSAGING_GUIDE.md](MESSAGING_GUIDE.md).

## Output Format

```json
{
  "listing_id": "1203728519",
  "title": "Storage Containers for Rent and caravan storage",
  "location": "Exeter, Devon",
  "price": "Please contact",
  "description": "Age: 0 days",
  "url": "https://www.gumtree.com/p/-/storage-containers.../1203728519",
  "scraped_at": "2025-11-08T15:09:08.070008"
}
```

## Configuration

### Scraping Settings

Edit `gumtree_scraper/settings.py` to adjust:
- Request delays (default: 1 second)
- Concurrent requests (default: 1 per domain)
- User agent string

### Messaging Configuration

Create `config.json` from the example:

```json
{
  "email": "your-email@example.com",
  "password": "your-password",
  "max_messages": 10,
  "message_delay": 5,
  "skip_contacted": true
}
```

## Message Templates

Templates support these placeholders:
- `{title}` - Listing title
- `{location}` - Location
- `{price}` - Price
- `{listing_id}` - Listing ID
- `{url}` - Listing URL
- `{description}` - Description

Example template:

```text
Hi,

I'm interested in your listing: {title}
Location: {location}
Price: {price}

Could you provide more details?

Thanks!
```

## Advanced Usage

### Debug Mode

Set `headless: False` in `settings_playwright.py` to watch the browser during messaging.

### Browser Selection

The scraper supports both **Chromium** and **Firefox** browsers. You can switch between them by changing the `BROWSER` variable at the top of the relevant files:

#### For Messaging Spider (gumtree_messenger):
Edit `gumtree_scraper/spiders/gumtree_messenger.py`:
```python
# Change this line at the top of the file
BROWSER = "firefox"  # Options: "chromium" or "firefox"
```

#### For General Playwright Settings:
Edit `gumtree_scraper/settings_playwright.py`:
```python
# Change this line near the top of the file
BROWSER = "firefox"  # Options: "chromium" or "firefox"
```

**Browser Differences:**
- **Chromium**: More mature automation features, better at avoiding detection with `--disable-blink-features` flags
- **Firefox**: Alternative option if Chromium is detected, uses Firefox-specific preferences to hide automation

**Note:** Each browser has its own specific configurations:
- Chromium uses command-line arguments for automation hiding
- Firefox uses browser preferences (`firefoxUserPrefs`) for automation hiding
- User agent strings automatically match the selected browser

## Troubleshooting

### Login Issues
- Verify credentials in `config.json`
- Check for CAPTCHA by running in non-headless mode
- Try logging in manually first

### Message Button Not Found
- Some listings may not allow messages
- Run in non-headless mode to debug
- Check if listing is still active

### Rate Limiting
- Increase `message_delay` in config
- Reduce `max_messages` per run
- Wait between batches

## Documentation

- [MESSAGING_GUIDE.md](MESSAGING_GUIDE.md) - Complete messaging documentation
- [QUICK_START.md](QUICK_START.md) - Quick reference guide
# Scraper
