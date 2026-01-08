"""
Settings for running Gumtree scraper with Playwright support.

To use these settings, run:
    scrapy crawl gumtree_playwright -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
"""

from .settings import *

# Browser selection - Change this to "firefox" to use Firefox instead of Chromium
BROWSER = "chromium"  # Options: "chromium" or "firefox"

# Browser-specific configurations
CHROMIUM_CONFIG = {
    "browser_type": "chromium",
    "launch_options": {
        "headless": True,
        "timeout": 30000,
    },
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

FIREFOX_CONFIG = {
    "browser_type": "firefox",
    "launch_options": {
        "headless": True,
        "timeout": 30000,
        "firefox_user_prefs": {
            "dom.webdriver.enabled": False,
            "useAutomationExtension": False,
            "general.platform.override": "MacIntel",
            "general.appversion.override": "5.0 (Macintosh)",
        },
    },
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
}

# Select browser configuration
BROWSER_CONFIG = FIREFOX_CONFIG if BROWSER == "firefox" else CHROMIUM_CONFIG

# Disable item pipelines for messenger spider (it reads from JSON, doesn't write)
# Must be set early to override settings.py
ITEM_PIPELINES = {}

# Enable Playwright download handlers
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Playwright browser configuration - dynamically set based on BROWSER variable
PLAYWRIGHT_BROWSER_TYPE = BROWSER_CONFIG["browser_type"]
PLAYWRIGHT_LAUNCH_OPTIONS = BROWSER_CONFIG["launch_options"]

# Additional Playwright context options
PLAYWRIGHT_CONTEXT_ARGS = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": BROWSER_CONFIG["user_agent"],
}

# Increase download timeout for pages with JavaScript
DOWNLOAD_TIMEOUT = 60

# Playwright-specific settings
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000  # 30 seconds

# Enable cookies to maintain session
COOKIES_ENABLED = True

# Concurrent requests - keep low when using Playwright
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Download delay
DOWNLOAD_DELAY = 2
