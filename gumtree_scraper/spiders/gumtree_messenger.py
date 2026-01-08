"""
Gumtree Messenger Spider - Automated messaging to listings


This spider logs into Gumtree and sends messages to sellers from scraped listings.

Usage:
    scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright

Configuration:
    Set environment variables or use config.json:
    - GUMTREE_EMAIL: Your Gumtree account email
    - GUMTREE_PASSWORD: Your Gumtree account password
    - MESSAGE_TEMPLATE: Path to message template file (default: message_template.txt)
    - INPUT_JSON: Path to listings JSON file (default: gumtree_listings.json)
    - MAX_MESSAGES: Maximum number of messages to send (default: unlimited)
    - MESSAGE_DELAY: Delay between messages in seconds (default: 5)
"""

import scrapy
import json
import os
import time
import random
from datetime import datetime
from pathlib import Path
import re
from gumtree_scraper.browser_fingerprint import generate_fingerprint

# Browser selection - Change this to "firefox" to use Firefox instead of Chromium
BROWSER = "firefox"  # Options: "chromium" or "firefox"

# Generate a randomized fingerprint for this session
FINGERPRINT = generate_fingerprint(browser_type=BROWSER, os_type="mac")

# Browser-specific configurations
CHROMIUM_CONFIG = {
    "browser_type": "chromium",
    "launch_options": {
        "headless": False,
        "timeout": 30000,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            f"--window-size={FINGERPRINT.window_inner_width},{FINGERPRINT.window_inner_height}",
            "--start-maximized",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-prompt-on-repost",
            "--disable-domain-reliability",
            "--disable-component-extensions-with-background-pages",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--disable-background-networking",
            "--mute-audio",
        ],
    },
    "user_agent": FINGERPRINT.user_agent,
    "viewport": FINGERPRINT.get_viewport(),
}

FIREFOX_CONFIG = {
    "browser_type": "firefox",
    "launch_options": {
        "headless": False,
        "timeout": 30000,
        "firefox_user_prefs": {
            # Core anti-detection preferences
            "dom.webdriver.enabled": False,
            "useAutomationExtension": False,
            "general.platform.override": FINGERPRINT.platform,
            "general.appversion.override": "5.0 (Macintosh)",
            # Additional stealth preferences
            "media.peerconnection.enabled": False,  # Disable WebRTC to prevent IP leaks
            "privacy.trackingprotection.enabled": True,
            "geo.enabled": False,  # Disable geolocation API
            "browser.cache.disk.enable": False,
            "browser.cache.memory.enable": True,
            "browser.cache.offline.enable": False,
            "network.http.use-cache": False,
            "browser.startup.homepage": "about:blank",
            "browser.startup.page": 0,
            "browser.shell.checkDefaultBrowser": False,
            "browser.tabs.warnOnClose": False,
            "browser.tabs.warnOnOpen": False,
            "devtools.console.stdout.content": False,
            "extensions.update.enabled": False,
            "datareporting.healthreport.uploadEnabled": False,
            "datareporting.policy.dataSubmissionEnabled": False,
        },
    },
    "user_agent": FINGERPRINT.user_agent,
    "viewport": FINGERPRINT.get_viewport(),
}

# Select browser configuration
BROWSER_CONFIG = FIREFOX_CONFIG if BROWSER == "firefox" else CHROMIUM_CONFIG


class GumtreeMessengerSpider(scrapy.Spider):
    name = "gumtree_messenger"
    allowed_domains = ["gumtree.com"]

    # Disable pipelines - this spider only reads from JSON, doesn't write to it
    # Also ensure Playwright handlers are enabled
    custom_settings = {
        "ITEM_PIPELINES": {},
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": BROWSER_CONFIG["browser_type"],
        "PLAYWRIGHT_LAUNCH_OPTIONS": BROWSER_CONFIG["launch_options"],
        "PLAYWRIGHT_CONTEXT_ARGS": {
            "viewport": BROWSER_CONFIG["viewport"],
            "user_agent": BROWSER_CONFIG["user_agent"],
            "locale": "en-GB",
            "timezone_id": "Europe/London",
            "permissions": ["geolocation"],
            "geolocation": {
                "latitude": 51.5074,
                "longitude": -0.1278,
            },  # London coordinates
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            },
        },
    }

    def __init__(self, *args, **kwargs):
        super(GumtreeMessengerSpider, self).__init__(*args, **kwargs)

        # Load configuration
        self.config = self.load_config()

        # Credentials
        self.email = self.config.get("email") or os.getenv("GUMTREE_EMAIL")
        self.password = self.config.get("password") or os.getenv("GUMTREE_PASSWORD")

        if not self.email or not self.password:
            raise ValueError("GUMTREE_EMAIL and GUMTREE_PASSWORD must be set!")

        # Settings
        self.input_json = self.config.get("input_json", "gumtree_listings.json")
        self.message_template_file = self.config.get(
            "message_template", "message_template.txt"
        )
        self.max_messages = self.config.get("max_messages", 0)  # 0 = unlimited
        self.message_delay = self.config.get("message_delay", 5)  # seconds
        self.skip_contacted = self.config.get("skip_contacted", True)
        self.fast_mode = self.config.get("fast_mode", False)  # Fast mode for speed optimization

        # State tracking
        self.listings = []
        self.contacted_file = "contacted_listings.json"
        self.contacted_ids = self.load_contacted_listings()
        self.messages_sent = 0
        self.messages_failed = 0
        self.messages_skipped = 0
        self.logged_in = False

        # Load message template
        self.message_template = self.load_message_template()

        # Progress tracking
        self.start_time = datetime.now()
        self.progress_log = []

        self.logger.info("=" * 80)
        self.logger.info("GUMTREE MESSENGER SPIDER INITIALIZED")
        self.logger.info("=" * 80)
        self.logger.info(f"Input file: {self.input_json}")
        self.logger.info(f"Message template: {self.message_template_file}")
        self.logger.info(
            f"Max messages: {self.max_messages if self.max_messages > 0 else 'Unlimited'}"
        )
        self.logger.info(f"Message delay: {self.message_delay}s")
        self.logger.info(f"Skip contacted: {self.skip_contacted}")
        self.logger.info(f"Fast mode: {self.fast_mode}")
        self.logger.info(f"Already contacted: {len(self.contacted_ids)} listings")
        self.logger.info("=" * 80)
        self.logger.info("RANDOMIZED FINGERPRINT")
        self.logger.info("=" * 80)
        self.logger.info(f"Browser: {BROWSER}")
        self.logger.info(
            f"Screen: {FINGERPRINT.screen_width}x{FINGERPRINT.screen_height}"
        )
        self.logger.info(
            f"Viewport: {FINGERPRINT.window_inner_width}x{FINGERPRINT.window_inner_height}"
        )
        self.logger.info(f"Platform: {FINGERPRINT.platform}")
        self.logger.info(f"CPU Cores: {FINGERPRINT.hardware_concurrency}")
        self.logger.info(f"Memory: {FINGERPRINT.device_memory}GB")
        self.logger.info(f"User Agent: {FINGERPRINT.user_agent[:80]}...")
        self.logger.info("=" * 80)

    def load_config(self):
        """Load configuration from config.json if it exists"""
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                return json.load(f)
        return {}

    def load_contacted_listings(self):
        """Load list of already contacted listing IDs"""
        if os.path.exists(self.contacted_file):
            with open(self.contacted_file, "r") as f:
                data = json.load(f)
                return set(data.get("contacted_ids", []))
        return set()

    def save_contacted_listing(self, listing_id, listing_url, status="success"):
        """Save a contacted listing ID to avoid duplicates"""
        self.contacted_ids.add(listing_id)

        # Load existing data
        if os.path.exists(self.contacted_file):
            with open(self.contacted_file, "r") as f:
                data = json.load(f)
        else:
            data = {"contacted_ids": [], "history": []}

        # Update data
        if listing_id not in data["contacted_ids"]:
            data["contacted_ids"].append(listing_id)

        data["history"].append(
            {
                "listing_id": listing_id,
                "url": listing_url,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save
        with open(self.contacted_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_message_template(self):
        """Load message template from file"""
        if os.path.exists(self.message_template_file):
            with open(self.message_template_file, "r", encoding="utf-8") as f:
                template = f.read()
                self.logger.info(
                    f"Loaded message template from {self.message_template_file}"
                )
                return template
        else:
            # Default template
            default_template = """Hi,

I'm interested in your listing: {title}
Location: {location}
Price: {price}

Could you please provide more details?

Thanks!"""
            self.logger.warning("Template file not found. Using default template.")
            self.logger.warning(
                f"Create {self.message_template_file} to customize your message."
            )
            return default_template

    def format_message(self, listing):
        """Format message template with listing data"""
        message = self.message_template

        # Replace placeholders
        replacements = {
            "{title}": listing.get("title", "N/A"),
            "{location}": listing.get("location", "N/A"),
            "{price}": listing.get("price", "N/A"),
            "{listing_id}": listing.get("listing_id", "N/A"),
            "{url}": listing.get("url", "N/A"),
            "{description}": listing.get("description", "N/A"),
            "{claim_link}": listing.get("claim_link", "N/A"),
        }

        for placeholder, value in replacements.items():
            message = message.replace(placeholder, str(value))

        return message

    def start_requests(self):
        """Load listings and start with login"""
        # Load listings from JSON
        if not os.path.exists(self.input_json):
            self.logger.error(f"Input file not found: {self.input_json}")
            return

        print("Opening input json", self.input_json)
        with open(self.input_json, "r") as f:
            c = f.read()
            self.listings = json.loads(c)

        self.logger.info(f"Loaded {len(self.listings)} listings from {self.input_json}")

        # Filter out already contacted if enabled
        if self.skip_contacted:
            original_count = len(self.listings)
            self.listings = [
                l
                for l in self.listings
                if l.get("listing_id") not in self.contacted_ids
            ]
            filtered_count = original_count - len(self.listings)
            self.logger.info(
                f"Filtered out {filtered_count} already contacted listings"
            )
            self.logger.info(f"Remaining: {len(self.listings)} listings to contact")

        # Limit messages if configured
        if self.max_messages > 0:
            self.listings = self.listings[: self.max_messages]
            self.logger.info(f"Limited to first {self.max_messages} listings")

        if not self.listings:
            self.logger.warning("No listings to process!")
            return

        # Start with login page - create a shared context for all requests
        yield scrapy.Request(
            "https://www.gumtree.com",
            callback=self.login,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "gumtree_session",  # Share context across all requests
                "playwright_page_init_callback": self.hide_automation,
            },
            errback=self.errback_close_page,
        )

    async def hide_automation(self, page):
        """Hide automation traces from the browser"""
        # Ignore common non-critical console errors from Gumtree's ad scripts
        ignored_patterns = [
            "getGA4Script",
            "regeneratorRuntime",
            "GPT",
            "Failed to register listener",
            "slotRequestedEvent",
            "Attestation check",
            "iframe.*sandbox",
            "401",
            "403",
            "timeout exceeded",
            "criteo",
            "doubleclick",
            "facebook.com",
            "rlcdn.com",
            "tapad.com"
        ]
        
        def filter_console(msg):
            """Filter out non-critical console messages"""
            msg_text = msg.text.lower()
            # Only log if it's not an ignored pattern
            if not any(pattern.lower() in msg_text for pattern in ignored_patterns):
                if msg.type in ['error', 'warning']:
                    self.logger.debug(f"Browser console [{msg.type}]: {msg.text}")
        
        # Listen to console messages (filtered)
        page.on("console", filter_console)
        
        # Only log critical page errors (not ad script errors)
        def filter_page_error(err):
            """Filter out non-critical page errors"""
            err_text = str(err).lower()
            if not any(pattern.lower() in err_text for pattern in ignored_patterns):
                self.logger.error(f"Browser page error: {err}")
        
        page.on("pageerror", filter_page_error)

        # Inject randomized fingerprint first
        fingerprint_script = FINGERPRINT.get_javascript_injection()
        await page.add_init_script(fingerprint_script)

        # Then inject comprehensive anti-detection
        await page.add_init_script("""
            // ===== COMPREHENSIVE ANTI-DETECTION SCRIPT =====

            // 1. Remove all Selenium/WebDriver properties
            const seleniumProperties = [
                '__webdriver_evaluate',
                '__selenium_evaluate',
                '__webdriver_script_function',
                '__webdriver_script_func',
                '__webdriver_script_fn',
                '__fxdriver_evaluate',
                '__driver_unwrapped',
                '__webdriver_unwrapped',
                '__driver_evaluate',
                '__selenium_unwrapped',
                '__fxdriver_unwrapped',
                '__webdriver_script_fn',
                'webdriver',
                '__webdriverFunc',
                '__webdriver_evaluate_func',
                '__webdriver_unwrapped_func'
            ];

            // Remove from window
            seleniumProperties.forEach(prop => {
                if (window[prop]) {
                    delete window[prop];
                }
            });

            // Remove from document
            seleniumProperties.forEach(prop => {
                if (document[prop]) {
                    delete document[prop];
                }
            });

            // 2. Override navigator.webdriver to always return false (CRITICAL)
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
                configurable: true
            });

            // Remove webdriver from navigator prototype
            if (navigator.__proto__.hasOwnProperty('webdriver')) {
                delete navigator.__proto__.webdriver;
            }

            // Also set on window level (some detection scripts check this)
            Object.defineProperty(window, 'webdriver', {
                get: () => false,
                configurable: true
            });

            // 2b. Ensure navigator.appVersion matches navigator.userAgent
            // (Detection checks if these mismatch - spoofing indicator)
            // Note: This is already set by fingerprint injection, but we verify consistency
            if (navigator.appVersion && navigator.userAgent) {
                const appVersionInUA = navigator.userAgent.includes(navigator.appVersion.split(' ')[0]);
                if (!appVersionInUA) {
                    console.warn('[Anti-Detection] AppVersion/UserAgent mismatch detected, but this is expected with fingerprint randomization');
                }
            }

            // 3. Fix User Agent - ensure no "HeadlessChrome" or automation markers
            Object.defineProperty(navigator, 'userAgent', {
                get: () => {
                    const ua = navigator.userAgent || '';
                    // Remove HeadlessChrome and replace with regular Chrome
                    return ua.replace(/HeadlessChrome/g, 'Chrome')
                             .replace(/Headless/g, '');
                },
                configurable: true
            });

            // 4. Mock plugins (empty array looks suspicious, add realistic ones)
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                            description: "Native Client",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        }
                    ];
                },
                configurable: true
            });

            // 5. Mock mimeTypes
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => {
                    return [
                        {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: {name: "Chrome PDF Plugin"}},
                        {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: {name: "Chrome PDF Plugin"}},
                        {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: {name: "Native Client"}},
                        {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: {name: "Native Client"}}
                    ];
                },
                configurable: true
            });

            // 6. Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en-US', 'en'],
                configurable: true
            });

            // 7. Mock chrome object (Puppeteer detection)
            if (!window.chrome) {
                window.chrome = {};
            }

            if (!window.chrome.runtime) {
                window.chrome.runtime = {
                    connect: function() {},
                    sendMessage: function() {},
                    onMessage: {
                        addListener: function() {},
                        removeListener: function() {}
                    }
                };
            }

            // 8. Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 9. Override toString to avoid detection
            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === window.navigator.permissions.query) {
                    return 'function query() { [native code] }';
                }
                return originalToString.call(this);
            };

            // 10. Platform and hardware properties are set by fingerprint
            // (already injected above)

            // 11. Mock battery API to return realistic values
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }

            // 12. Add connection property
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    downlink: 10,
                    rtt: 50,
                    saveData: false
                }),
                configurable: true
            });

            // 13. Spoof vendor
            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.',
                configurable: true
            });

            // 14. Remove _phantom and callPhantom (PhantomJS detection)
            if (window._phantom) {
                delete window._phantom;
            }
            if (window.callPhantom) {
                delete window.callPhantom;
            }

            // 15. Override console.debug to hide automation logging
            const noop = () => {};
            console.debug = noop;

            // 16. Make sure there's no automation extension
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: true
            });

            // 17. Ensure consistent timing for performance
            if (window.performance && window.performance.timing) {
                Object.defineProperty(window.performance, 'timing', {
                    get: () => {
                        const timing = {};
                        const now = Date.now();
                        const base = now - Math.floor(Math.random() * 1000);

                        timing.navigationStart = base;
                        timing.fetchStart = base + 5;
                        timing.domainLookupStart = base + 10;
                        timing.domainLookupEnd = base + 15;
                        timing.connectStart = base + 15;
                        timing.connectEnd = base + 25;
                        timing.requestStart = base + 25;
                        timing.responseStart = base + 100;
                        timing.responseEnd = base + 200;
                        timing.domLoading = base + 205;
                        timing.domInteractive = base + 500;
                        timing.domContentLoadedEventStart = base + 505;
                        timing.domContentLoadedEventEnd = base + 510;
                        timing.domComplete = base + 800;
                        timing.loadEventStart = base + 805;
                        timing.loadEventEnd = base + 810;

                        return timing;
                    },
                    configurable: true
                });
            }

            // 18. Patch notification permissions
            if (Notification) {
                Object.defineProperty(Notification, 'permission', {
                    get: () => 'default',
                    configurable: true
                });
            }

            // 19. Remove Firebug detection
            if (window.document.firebug) {
                delete window.document.firebug;
            }
            Object.defineProperty(window.document, 'firebug', {
                get: () => undefined,
                configurable: true
            });

            // 20. Advanced Canvas Fingerprinting Protection
            // Comprehensive protection against all canvas fingerprinting techniques

            // Save originals
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            const originalFillText = CanvasRenderingContext2D.prototype.fillText;
            const originalStrokeText = CanvasRenderingContext2D.prototype.strokeText;
            const originalFillRect = CanvasRenderingContext2D.prototype.fillRect;
            const originalStrokeRect = CanvasRenderingContext2D.prototype.strokeRect;

            // Detect if canvas is being used for fingerprinting
            function isCanvasFingerprintAttempt(canvas) {
                // Common fingerprinting canvas sizes
                const suspiciousSizes = [
                    [16, 16], [220, 30], [280, 60], [300, 150],
                    [240, 60], [200, 20], [50, 50], [100, 100]
                ];

                for (const [w, h] of suspiciousSizes) {
                    if (Math.abs(canvas.width - w) <= 10 && Math.abs(canvas.height - h) <= 10) {
                        return true;
                    }
                }

                // Small canvases are often for fingerprinting
                if (canvas.width < 400 && canvas.height < 400) {
                    return Math.random() > 0.7; // Randomly add noise to small canvases
                }

                return false;
            }

            // Generate consistent but slightly randomized noise seed per session
            const canvasNoiseSeed = Math.random() * 0.001;

            // Add sophisticated noise to image data
            function addCanvasNoise(imageData) {
                const data = imageData.data;
                const length = data.length;

                // Add subtle, imperceptible noise to break fingerprinting
                // But keep it consistent within the session
                for (let i = 0; i < length; i += 4) {
                    // Calculate position-based noise (consistent per position)
                    const pixelIndex = i / 4;
                    const row = Math.floor(pixelIndex / (imageData.width || 1));
                    const col = pixelIndex % (imageData.width || 1);

                    // Use position and seed to generate consistent noise
                    const noise = ((row * col * canvasNoiseSeed) % 1) * 2 - 1;

                    // Add tiny noise to RGB channels (±1-2 pixels)
                    data[i] = Math.min(255, Math.max(0, data[i] + Math.floor(noise * 2)));     // R
                    data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + Math.floor(noise * 2))); // G
                    data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + Math.floor(noise * 2))); // B
                    // Alpha channel unchanged (data[i + 3])
                }

                return imageData;
            }

            // Override fillText to add subtle variations (text rendering fingerprinting)
            CanvasRenderingContext2D.prototype.fillText = function(text, x, y, maxWidth) {
                // Add microscopic offset to prevent exact text rendering fingerprints
                const xOffset = (Math.random() - 0.5) * 0.0001;
                const yOffset = (Math.random() - 0.5) * 0.0001;

                return originalFillText.call(this, text, x + xOffset, y + yOffset, maxWidth);
            };

            // Override strokeText similarly
            CanvasRenderingContext2D.prototype.strokeText = function(text, x, y, maxWidth) {
                const xOffset = (Math.random() - 0.5) * 0.0001;
                const yOffset = (Math.random() - 0.5) * 0.0001;

                return originalStrokeText.call(this, text, x + xOffset, y + yOffset, maxWidth);
            };

            // Override getImageData to add noise
            CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
                const imageData = originalGetImageData.call(this, sx, sy, sw, sh);

                // Add noise if this looks like fingerprinting
                const canvas = this.canvas;
                if (canvas && isCanvasFingerprintAttempt(canvas)) {
                    addCanvasNoise(imageData);
                }

                return imageData;
            };

            // Override toDataURL to add noise
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                // Add noise before converting to data URL if fingerprinting detected
                if (isCanvasFingerprintAttempt(this)) {
                    const ctx = this.getContext('2d');
                    if (ctx) {
                        try {
                            const imageData = originalGetImageData.call(ctx, 0, 0, this.width, this.height);
                            addCanvasNoise(imageData);
                            ctx.putImageData(imageData, 0, 0);
                        } catch(e) {
                            // Ignore errors, proceed with original
                        }
                    }
                }

                return originalToDataURL.call(this, type, quality);
            };

            // Override toBlob for completeness
            if (originalToBlob) {
                HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
                    if (isCanvasFingerprintAttempt(this)) {
                        const ctx = this.getContext('2d');
                        if (ctx) {
                            try {
                                const imageData = originalGetImageData.call(ctx, 0, 0, this.width, this.height);
                                addCanvasNoise(imageData);
                                ctx.putImageData(imageData, 0, 0);
                            } catch(e) {
                                // Ignore errors
                            }
                        }
                    }

                    return originalToBlob.call(this, callback, type, quality);
                };
            }

            // Override rect drawing to add microscopic variations
            CanvasRenderingContext2D.prototype.fillRect = function(x, y, width, height) {
                const canvas = this.canvas;
                if (canvas && isCanvasFingerprintAttempt(canvas)) {
                    // Add tiny offset to break fingerprinting patterns
                    x += (Math.random() - 0.5) * 0.0001;
                    y += (Math.random() - 0.5) * 0.0001;
                }
                return originalFillRect.call(this, x, y, width, height);
            };

            CanvasRenderingContext2D.prototype.strokeRect = function(x, y, width, height) {
                const canvas = this.canvas;
                if (canvas && isCanvasFingerprintAttempt(canvas)) {
                    x += (Math.random() - 0.5) * 0.0001;
                    y += (Math.random() - 0.5) * 0.0001;
                }
                return originalStrokeRect.call(this, x, y, width, height);
            };

            // 21. WebGL Fingerprinting Protection
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // Spoof WebGL parameters to avoid fingerprinting
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    return 'Intel Iris OpenGL Engine';
                }
                return originalGetParameter.apply(this, arguments);
            };

            // Also for WebGL2
            if (window.WebGL2RenderingContext) {
                const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return originalGetParameter2.apply(this, arguments);
                };
            }

            // 22. DevTools Detection Prevention
            // Prevent detection of open DevTools via timing attacks
            let devtoolsOpen = false;
            const element = new Image();
            Object.defineProperty(element, 'id', {
                get: function() {
                    devtoolsOpen = true;
                    return 'debug';
                }
            });

            // Override console methods to prevent DevTools detection
            const consoleImage = console.log;
            console.log = function() {
                consoleImage.apply(console, arguments);
            };

            // Prevent toString DevTools detection
            const originalLog = console.log;
            console.log = function(...args) {
                return originalLog.apply(console, args);
            };

            // Prevent debugger statement detection
            const originalDebugger = window.eval;
            window.eval = function(code) {
                if (code.includes('debugger')) {
                    return null;
                }
                return originalDebugger.apply(this, arguments);
            };

            // 23. AudioContext Fingerprinting Protection
            if (window.AudioContext || window.webkitAudioContext) {
                const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
                const OriginalCreateAnalyser = OriginalAudioContext.prototype.createAnalyser;

                OriginalAudioContext.prototype.createAnalyser = function() {
                    const analyser = OriginalCreateAnalyser.apply(this, arguments);
                    const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;

                    analyser.getFloatFrequencyData = function(array) {
                        const result = originalGetFloatFrequencyData.apply(this, arguments);
                        // Add noise to audio fingerprinting
                        for (let i = 0; i < array.length; i++) {
                            array[i] = array[i] + Math.random() * 0.0001;
                        }
                        return result;
                    };

                    return analyser;
                };
            }

            // 24. Font Fingerprinting Protection
            // Override measureText to add slight variations
            const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = function(text) {
                const metrics = originalMeasureText.apply(this, arguments);
                // Add tiny random variation to width
                const noise = (Math.random() - 0.5) * 0.0001;
                Object.defineProperty(metrics, 'width', {
                    get: function() {
                        return metrics.width + noise;
                    }
                });
                return metrics;
            };

            // 25. Screen Resolution - set by randomized fingerprint
            // (already injected above)

            // 26. Timezone Consistency
            // Ensure Date.prototype.getTimezoneOffset returns consistent value
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {
                return 0; // UTC timezone (matches London setting in context)
            };

            // 27. MediaDevices Enumeration (prevent empty devices detection)
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                navigator.mediaDevices.enumerateDevices = function() {
                    return originalEnumerateDevices.apply(this, arguments).then(devices => {
                        // If no devices, return fake ones
                        if (devices.length === 0) {
                            return [
                                {
                                    deviceId: 'default',
                                    kind: 'audioinput',
                                    label: 'Default - Microphone (Built-in)',
                                    groupId: 'default'
                                },
                                {
                                    deviceId: 'default',
                                    kind: 'videoinput',
                                    label: 'Default - Camera (Built-in)',
                                    groupId: 'default'
                                }
                            ];
                        }
                        return devices;
                    });
                };
            }

            // 28. Error Stack Trace Sanitization
            // Prevents detection via error.stack analysis (PhantomJS, automation traces)
            const OriginalError = window.Error;
            window.Error = function(...args) {
                const error = new OriginalError(...args);

                // Override stack property to clean automation traces
                Object.defineProperty(error, 'stack', {
                    get: function() {
                        const stack = error.stack || '';
                        // Remove all automation-related strings from stack traces
                        return stack
                            .replace(/phantomjs/gi, 'chrome')
                            .replace(/phantom/gi, 'chrome')
                            .replace(/headless/gi, '')
                            .replace(/selenium/gi, '')
                            .replace(/webdriver/gi, '')
                            .replace(/automation/gi, '')
                            .replace(/__webdriver/gi, '')
                            .replace(/__selenium/gi, '')
                            .replace(/__fxdriver/gi, '')
                            .replace(/__driver/gi, '');
                    },
                    configurable: true
                });

                return error;
            };

            // Preserve Error properties
            window.Error.prototype = OriginalError.prototype;
            window.Error.captureStackTrace = OriginalError.captureStackTrace;
            window.Error.stackTraceLimit = OriginalError.stackTraceLimit;

            // Override Error.prototype.toString to prevent detection
            const originalErrorToString = Error.prototype.toString;
            Error.prototype.toString = function() {
                return originalErrorToString.call(this);
            };

            // 29. Null Function Call Protection
            // Handle the (null)[0]() detection test gracefully
            // This test tries to trigger an error and check the stack for 'phantomjs'
            try {
                // Preemptively catch this specific test pattern
                const nullTest = null;
                if (nullTest && typeof nullTest[0] === 'function') {
                    nullTest[0]();
                }
            } catch(e) {
                // Ensure error stack doesn't contain automation traces
                if (e.stack) {
                    e.stack = e.stack
                        .replace(/phantomjs/gi, 'chrome')
                        .replace(/selenium/gi, '')
                        .replace(/webdriver/gi, '');
                }
            }

            // 30. Edge Browser Consistency Check
            // Ensure platform matches browser type in user agent
            const ua = navigator.userAgent.toLowerCase();
            const platform = navigator.platform.toLowerCase();

            // If UA says Edge but platform doesn't match Windows, it's suspicious
            if (ua.includes('edge') || ua.includes('edg/')) {
                // Edge should be on Windows
                if (!platform.includes('win')) {
                    console.warn('[Anti-Detection] Edge browser on non-Windows platform detected, but this is normal for Edge on Mac');
                }
            }

            // If UA says Mac but platform says Windows (or vice versa), it's spoofing
            const uaHasMac = ua.includes('macintosh') || ua.includes('mac os');
            const uaHasWindows = ua.includes('windows');
            const platformHasMac = platform.includes('mac');
            const platformHasWindows = platform.includes('win');

            if ((uaHasMac && platformHasWindows) || (uaHasWindows && platformHasMac)) {
                console.error('[Anti-Detection] Platform/UserAgent mismatch detected! This indicates spoofing.');
                // Our fingerprint system ensures these match, so this should never trigger
            }

            console.log('[Anti-Detection] All automation traces removed successfully');
            console.log('[Anti-Detection] Canvas fingerprinting protection enabled');
            console.log('[Anti-Detection] WebGL fingerprinting protection enabled');
            console.log('[Anti-Detection] DevTools detection prevention enabled');
            console.log('[Anti-Detection] Error stack trace sanitization enabled');
            console.log('[Anti-Detection] Platform consistency verified');
            console.log('[Anti-Detection] navigator.webdriver = ' + navigator.webdriver);
        """)

    async def login(self, response):
        """Handle login using Playwright"""
        page = response.meta["playwright_page"]

        try:
            self.logger.info("=" * 80)
            self.logger.info("ATTEMPTING LOGIN")
            self.logger.info("=" * 80)

            # Handle cookie consent popup if present
            try:
                cookie_button = await page.wait_for_selector(
                    "#onetrust-accept-btn-handler", timeout=3000
                )
                if cookie_button:
                    self.logger.info("Accepting cookie consent...")
                    await cookie_button.click()
                    await page.wait_for_timeout(500 if self.fast_mode else 1000)
            except Exception as e:
                self.logger.debug(f"No cookie popup found or already accepted: {e}")

            # Click the login button in header to open login modal
            self.logger.info("Clicking login button...")
            await page.click('button[data-q="hm-login"]')
            await page.wait_for_timeout(500 if self.fast_mode else 1000)

            # Click "Continue with email" button
            self.logger.info("Clicking 'Continue with email'...")
            await page.click('button[data-q="email-login"]')
            await page.wait_for_timeout(500 if self.fast_mode else 1000)

            # Wait for email field to appear
            await page.wait_for_selector(
                '[data-testid="input-username"]', timeout=10000
            )

            self.logger.info(f"Logging in as: {self.email}")

            # Fill in credentials using data-testid attributes
            await page.fill('[data-testid="input-username"]', self.email)
            await page.fill('[data-testid="input-password"]', self.password)

            # Click the "Continue" button to submit
            self.logger.info("Clicking 'Continue' to submit login...")
            await page.click('button[type="submit"]:has-text("Continue")')

            # Wait a bit for the login to process
            self.logger.info("Waiting for login to complete...")
            await page.wait_for_timeout(1500 if self.fast_mode else 3000)

            # Check if login was successful by checking URL
            current_url = page.url
            if "login" in current_url.lower():
                self.logger.error("Login failed - still on login page")
                self.logged_in = False
            else:
                self.logged_in = True
                self.logger.info("✓ Successfully logged in!")
                self.logger.info(f"Current URL: {current_url}")
                self.log_progress("Login successful")

        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            self.log_progress(f"Login failed: {str(e)}")
            await page.close()
            return

        # After successful login, start messaging
        if self.logged_in:
            self.logger.info("=" * 80)
            self.logger.info(f"STARTING TO MESSAGE {len(self.listings)} LISTINGS")
            self.logger.info("=" * 80)

            # Process each listing
            for idx, listing in enumerate(self.listings, 1):
                listing_url = listing.get("url")
                reply_url = listing.get("reply_url")
                listing_id = listing.get("listing_id")

                # Prefer reply_url if available, fallback to listing URL
                target_url = reply_url if reply_url else listing_url

                if not target_url:
                    self.logger.warning(f"Skipping listing {idx}: No URL or reply_url")
                    self.messages_skipped += 1
                    continue

                self.logger.info(
                    f"\n[{idx}/{len(self.listings)}] Processing: {listing.get('title', 'Unknown')}"
                )
                if reply_url:
                    self.logger.info(f"Using direct reply URL: {reply_url}")
                else:
                    self.logger.warning(
                        f"No reply_url available, using listing URL: {listing_url}"
                    )

                # Visit reply page (or listing page as fallback) and send message
                yield scrapy.Request(
                    target_url,
                    callback=self.send_message,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context": "gumtree_session",  # Use same context with login cookies
                        "playwright_page_init_callback": self.hide_automation,
                        "listing": listing,
                        "index": idx,
                        "is_reply_url": bool(
                            reply_url
                        ),  # Flag to know if we're using direct reply URL
                    },
                    dont_filter=True,
                    errback=self.errback_close_page,
                )

                # Add delay between requests (longer if previous message failed)
                if idx < len(self.listings):
                    if self.fast_mode:
                        # Fast mode: reduce delay significantly
                        delay = max(1000, self.message_delay * 500)  # At least 1 second, but much faster
                    else:
                        delay = self.message_delay * 1000
                    # If last message failed, wait longer
                    if self.messages_failed > 0 and (self.messages_sent + self.messages_failed) % 3 == 0:
                        delay = delay * 2  # Double delay every 3rd message if there were failures
                        self.logger.info(f"⚠️  Extended delay due to previous failures: {delay/1000}s")
                    await page.wait_for_timeout(delay)

        await page.close()

    async def send_message(self, response):
        """Send message to seller"""
        page = response.meta["playwright_page"]
        listing = response.meta["listing"]
        index = response.meta["index"]
        is_reply_url = response.meta.get("is_reply_url", False)

        listing_id = listing.get("listing_id")
        listing_title = listing.get("title", "Unknown")
        target_url = response.url

        self.logger.info("=" * 60)
        self.logger.info(f"[{index}] Processing: {listing_title}")
        self.logger.info(f"URL: {target_url}")
        self.logger.info(f"Is reply URL: {is_reply_url}")
        self.logger.info("=" * 60)

        # Check page URL and title after navigation
        current_url = page.url
        page_title = await page.title()
        self.logger.info(f"Current page URL: {current_url}")
        self.logger.info(f"Page title: {page_title}")

        # Check if page loaded correctly
        if "gumtree.com" not in current_url.lower():
            self.logger.error(f"❌ Page not on Gumtree! Current URL: {current_url}")
            self.messages_failed += 1
            await page.close()
            return

        # Ignore non-critical network errors (ad scripts, tracking, etc.)
        ignored_domains = [
            "doubleclick.net",
            "google-analytics.com",
            "googletagmanager.com",
            "criteo.com",
            "rlcdn.com",
            "tapad.com",
            "facebook.com",
            "measurement-api.criteo.com"
        ]
        
        def filter_request_failed(request):
            """Filter out non-critical failed requests"""
            url = request.url.lower()
            if not any(domain in url for domain in ignored_domains):
                self.logger.warning(f"Request failed: {request.url} - {request.failure}")
        
        def filter_response(response):
            """Filter out non-critical error responses"""
            if response.status >= 400:
                url = response.url.lower()
                if not any(domain in url for domain in ignored_domains):
                    # Only log if it's a critical error (500+) or from gumtree.com
                    if response.status >= 500 or "gumtree.com" in url:
                        self.logger.error(f"HTTP {response.status}: {response.url}")
        
        # Log failed network requests (filtered)
        page.on("requestfailed", filter_request_failed)
        
        # Log responses with errors (filtered)
        page.on("response", filter_response)

        try:
            # If we're using the direct reply URL, skip the message button click
            if is_reply_url:
                self.logger.info(
                    "Using direct reply URL, skipping message button click..."
                )
                # Wait for message form to load directly
                await page.wait_for_timeout(1500 if self.fast_mode else 3000)
                
                # Check if we're on the right page
                page_content = await page.content()
                if "reply" not in current_url.lower() and "message" not in page_content.lower():
                    self.logger.warning("⚠️  Reply URL may not have loaded correctly")
                    # Take screenshot for debugging
                    screenshot_path = f"debug_reply_page_{index}.png"
                    await page.screenshot(path=screenshot_path)
                    self.logger.info(f"Screenshot saved: {screenshot_path}")
            else:
                # Click the "Message" button as soon as it appears
                self.logger.info("Looking for message button...")
                try:
                    # Wait for button to be present and visible
                    message_button = await page.wait_for_selector(
                        '[data-q="contact-email"]', timeout=20000, state="visible"
                    )
                    self.logger.info("Found message button, clicking immediately...")

                    # Scroll into view and click
                    await message_button.scroll_into_view_if_needed()
                    await page.wait_for_timeout(300 if self.fast_mode else 1000)
                    await message_button.click()
                    self.logger.info("Clicked message button successfully")
                except Exception as e:
                    self.logger.warning(
                        f"✗ Could not find or click message button for: {listing_title}"
                    )
                    self.logger.error(f"Error: {e}")
                    self.messages_failed += 1
                    self.log_progress(
                        f"[{index}] FAILED - No message button: {listing_title}"
                    )
                    await page.close()
                    return

                # Wait longer for message form to load (Gumtree may be slow)
                self.logger.info("Waiting for message form to load...")
                await page.wait_for_timeout(2000 if self.fast_mode else 5000)

            # Find the textarea with class "reply-form-message"
            try:
                textarea = await page.wait_for_selector(
                    "textarea.reply-form-message", timeout=15000, state="visible"
                )
                self.logger.info("Found message textarea")

                # Human-like behavior: scroll to textarea
                await textarea.scroll_into_view_if_needed()
                await page.wait_for_timeout(200 if self.fast_mode else 500)

                # Human-like behavior: move mouse to textarea and click it
                if not self.fast_mode:
                    box = await textarea.bounding_box()
                    if box:
                        await page.mouse.move(
                            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                        )
                        await page.wait_for_timeout(300)
                        await page.mouse.click(
                            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                        )
                        await page.wait_for_timeout(500)
                else:
                    # Fast mode: just focus
                    await textarea.focus()
                    await page.wait_for_timeout(100)

                # Format message
                message = self.format_message(listing)

                # Typing strategy: fast mode uses paste, normal mode uses faster typing
                if self.fast_mode:
                    # Fast mode: use fill (instant) or paste
                    self.logger.info("Filling message (fast mode)...")
                    await textarea.fill(message)
                    self.logger.info(f"Message filled instantly ({len(message)} characters)")
                else:
                    # Normal mode: faster typing (reduced delays)
                    self.logger.info("Typing message...")
                    char_count = 0
                    for char in message:
                        # Faster typing: 20-50ms per char (much faster than before)
                        delay = 20 + random.randint(0, 30) + (hash(char) % 10)
                        await textarea.type(char, delay=delay)
                        char_count += 1
                        
                        # Shorter pause every ~100 characters
                        if char_count % 100 == 0:
                            pause = random.randint(200, 500)
                            await page.wait_for_timeout(pause)
                            self.logger.debug(f"Pause after {char_count} characters: {pause}ms")

                    self.logger.info(f"Finished typing message ({len(message)} characters)")

                self.logger.info("Message preview:")
                self.logger.info("-" * 60)
                self.logger.info(message[:200] + ("..." if len(message) > 200 else ""))
                self.logger.info("-" * 60)

                # Wait before clicking send (human-like pause to review message)
                if self.fast_mode:
                    # Fast mode: minimal wait
                    self.logger.info("Waiting before sending (fast mode)...")
                    await page.wait_for_timeout(500)
                else:
                    # Normal mode: human-like behavior
                    self.logger.info("Waiting before sending (human-like pause)...")
                    await textarea.scroll_into_view_if_needed()
                    await page.wait_for_timeout(random.randint(1000, 2000))  # Reduced from 2-4 seconds
                    
                    # Scroll page slightly (human-like behavior)
                    await page.evaluate("window.scrollBy(0, -100)")
                    await page.wait_for_timeout(random.randint(300, 600))
                    await page.evaluate("window.scrollBy(0, 100)")
                    await page.wait_for_timeout(random.randint(500, 1000))

                # Click the send button with data-title="submit-message"
                self.logger.info("Looking for send button...")
                send_button = await page.wait_for_selector(
                    'button[data-title="submit-message"]',
                    timeout=10000,
                    state="visible",
                )

                if not send_button:
                    raise Exception("Send button not found")

                # Human-like: scroll to send button
                await send_button.scroll_into_view_if_needed()
                if self.fast_mode:
                    await page.wait_for_timeout(200)
                else:
                    await page.wait_for_timeout(random.randint(400, 800))

                send_box = await send_button.bounding_box()
                if send_box and not self.fast_mode:
                    # Move mouse in a more human-like way (not directly to button)
                    # First move to a random nearby point
                    random_x = send_box["x"] + send_box["width"] / 2 + random.randint(-50, 50)
                    random_y = send_box["y"] + send_box["height"] / 2 + random.randint(-30, 30)
                    await page.mouse.move(random_x, random_y)
                    await page.wait_for_timeout(random.randint(200, 400))
                    
                    # Then move to the actual button center
                    button_x = send_box["x"] + send_box["width"] / 2
                    button_y = send_box["y"] + send_box["height"] / 2
                    await page.mouse.move(button_x, button_y, steps=random.randint(5, 10))
                    await page.wait_for_timeout(random.randint(500, 1000))  # Reduced pause

                # Check if button is enabled
                is_disabled = await send_button.get_attribute("disabled")
                if is_disabled:
                    self.logger.warning("⚠️  Send button is disabled!")
                    raise Exception("Send button is disabled")

                self.logger.info("Clicking send button...")
                
                # Listen for navigation/response errors before clicking
                error_occurred = {"value": False}
                error_message = {"value": ""}
                
                def handle_response(response):
                    if response.status >= 400:
                        error_occurred["value"] = True
                        error_message["value"] = f"HTTP {response.status}: {response.url}"
                        self.logger.error(f"❌ Error response: {error_message['value']}")
                
                page.on("response", handle_response)
                
                # Try using keyboard Enter instead of click (more human-like)
                if not self.fast_mode:
                    # First, focus on the textarea
                    await textarea.focus()
                    await page.wait_for_timeout(random.randint(200, 500))
                    
                    # Try pressing Enter to submit (some forms support this)
                    try:
                        await page.keyboard.press("Enter")
                        self.logger.info("Used Enter key to submit")
                        await page.wait_for_timeout(1500 if self.fast_mode else 2000)  # Wait to see if it worked
                        
                        # Check if form disappeared (success)
                        form_still_visible = await page.query_selector("textarea.reply-form-message")
                        if not form_still_visible:
                            self.logger.info("✅ Message sent via Enter key!")
                            # Success - skip button click
                        else:
                            # Enter didn't work, use button click
                            self.logger.info("Enter didn't work, using button click...")
                            await send_button.click()
                    except Exception as e:
                        self.logger.warning(f"Enter key failed: {e}, using button click...")
                        await send_button.click()
                else:
                    # Fast mode: just click
                    await send_button.click()
                
                # Wait for response (check for errors)
                self.logger.info("Waiting for response after clicking send...")
                self.logger.info("=" * 60)
                self.logger.info("CHECKING MESSAGE STATUS...")
                self.logger.info("=" * 60)
                
                # Wait a bit for page to respond
                await page.wait_for_timeout(1500 if self.fast_mode else 3000)  # Wait less in fast mode
                
                # Check current state
                current_url = page.url
                page_title = await page.title()
                self.logger.info(f"Current URL: {current_url}")
                self.logger.info(f"Page title: {page_title}")
                
                # Check if form disappeared (success indicator)
                form_still_visible = await page.query_selector("textarea.reply-form-message")
                self.logger.info(f"Message form visible: {form_still_visible is not None}")
                
                # Check for success messages
                success_indicators = [
                    "message sent",
                    "your message has been sent",
                    "message delivered",
                    "success",
                    "thank you for your message"
                ]
                
                page_content = await page.content()
                page_text = page_content.lower()
                
                found_success = False
                for indicator in success_indicators:
                    if indicator in page_text:
                        self.logger.info(f"✅ Found success indicator: '{indicator}'")
                        found_success = True
                        break
                
                # Wait a bit more to see if page loads completely
                await page.wait_for_timeout(1000 if self.fast_mode else 2000)
                
                # Re-check after additional wait
                current_url_2 = page.url
                form_still_visible_2 = await page.query_selector("textarea.reply-form-message")
                
                self.logger.info(f"After additional wait:")
                self.logger.info(f"  URL: {current_url_2}")
                self.logger.info(f"  Form visible: {form_still_visible_2 is not None}")
                
                # Check for Gumtree error pages
                if "error 500" in page_text or "error 500" in current_url.lower() or "500" in page_title.lower():
                    error_occurred["value"] = True
                    error_message["value"] = "Gumtree Error 500 detected"
                    self.logger.error("❌ Gumtree Error 500 detected!")
                    self.logger.error(f"   Current URL: {current_url}")
                    self.logger.error(f"   Page title: {page_title}")
                    
                    # Take screenshot for debugging
                    screenshot_path = f"error_500_{index}_{listing_id}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    self.logger.info(f"Screenshot saved: {screenshot_path}")
                    
                    # Save page HTML for debugging
                    html_path = f"error_500_{index}_{listing_id}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(page_content)
                    self.logger.info(f"Page HTML saved: {html_path}")
                    
                    # Wait longer before next attempt (rate limiting)
                    wait_time = 15000 if self.fast_mode else 30000
                    self.logger.warning(f"⚠️  Waiting {wait_time/1000} seconds before next message (rate limiting)...")
                    await page.wait_for_timeout(wait_time)
                    
                    raise Exception("Gumtree Error 500: Message submission failed - possible rate limiting or anti-bot protection")
                
                # Detailed check for success/failure
                if form_still_visible_2:
                    # Form still visible - might be an error or still processing
                    self.logger.warning("⚠️  Message form still visible after send")
                    
                    # Check for error messages
                    error_selectors = [
                        '.error',
                        '.error-message',
                        '[role="alert"]',
                        '.alert-danger',
                        '.notification-error',
                        '.alert',
                        '[class*="error"]',
                        '[class*="Error"]'
                    ]
                    
                    found_error = False
                    for selector in error_selectors:
                        try:
                            error_elem = await page.query_selector(selector)
                            if error_elem:
                                error_text = await error_elem.inner_text()
                                if error_text and len(error_text.strip()) > 0:
                                    self.logger.error(f"❌ Error on page: {error_text[:200]}")
                                    error_occurred["value"] = True
                                    error_message["value"] = error_text[:200]
                                    found_error = True
                                    break
                        except Exception as e:
                            continue
                    
                    if not found_error:
                        # Check if page is blank/white
                        if not page_text or len(page_text) < 100:
                            self.logger.warning("⚠️  Page appears to be blank/white")
                            error_occurred["value"] = True
                            error_message["value"] = "Page became blank/white after send - may have failed"
                        else:
                            # Wait a bit more - might be processing
                            wait_time = 1500 if self.fast_mode else 3000
                            self.logger.info(f"Waiting additional {wait_time/1000} seconds for processing...")
                            await page.wait_for_timeout(wait_time)
                            
                            # Final check
                            form_still_visible_final = await page.query_selector("textarea.reply-form-message")
                            current_url_final = page.url
                            
                            self.logger.info(f"Final check:")
                            self.logger.info(f"  Form visible: {form_still_visible_final is not None}")
                            self.logger.info(f"  URL: {current_url_final}")
                            
                            if form_still_visible_final:
                                # Still visible - likely failed
                                error_occurred["value"] = True
                                error_message["value"] = "Message form still visible after send - submission may have failed"
                else:
                    # Form disappeared - likely success!
                    self.logger.info("✅ Message form disappeared - likely successful!")
                    
                    # Additional success checks
                    if found_success:
                        self.logger.info("✅ Success message found on page!")
                    
                    # Check if we're on a different page (success redirect)
                    if current_url_2 != target_url:
                        self.logger.info(f"✅ Redirected to different page: {current_url_2}")
                        self.logger.info(f"  (was: {target_url})")
                        self.logger.info("This usually indicates successful submission!")
                    
                    # Take screenshot of success page
                    try:
                        success_screenshot = f"success_{index}_{listing_id}.png"
                        await page.screenshot(path=success_screenshot, full_page=True)
                        self.logger.info(f"Screenshot saved: {success_screenshot}")
                    except Exception as e:
                        self.logger.debug(f"Could not save screenshot: {e}")
                
                if error_occurred["value"]:
                    screenshot_path = f"error_send_{index}_{listing_id}.png"
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                        self.logger.info(f"Screenshot saved: {screenshot_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not save error screenshot: {e}")
                    
                    self.logger.error("=" * 60)
                    self.logger.error("MESSAGE SEND FAILED")
                    self.logger.error("=" * 60)
                    self.logger.error(f"Error: {error_message['value']}")
                    self.logger.error(f"URL: {current_url_2}")
                    self.logger.error("=" * 60)
                    
                    raise Exception(f"Failed to send message: {error_message['value']}")
                
                # Success!
                self.logger.info("=" * 60)
                self.logger.info("MESSAGE SENT SUCCESSFULLY!")
                self.logger.info("=" * 60)
                self.logger.info(f"Listing: {listing_title}")
                self.logger.info(f"Final URL: {current_url_2}")
                self.logger.info(f"Form disappeared: Yes")
                self.logger.info(f"Success indicator found: {found_success}")
                self.logger.info("=" * 60)
                
                self.messages_sent += 1
                self.logger.info(f"✅ Message sent successfully! Total sent: {self.messages_sent}")
                self.log_progress(f"[{index}] SUCCESS: {listing_title}")
                self.save_contacted_listing(listing_id, listing.get("url"), "success")
                
                # Wait a bit before closing to ensure everything is saved
                wait_time = 500 if self.fast_mode else 2000
                self.logger.info(f"Waiting {wait_time/1000} seconds before closing page...")
                await page.wait_for_timeout(wait_time)

            except Exception as e:
                self.logger.warning(f"✗ Failed to send message: {e}")
                self.messages_failed += 1
                self.log_progress(f"[{index}] FAILED - {str(e)}: {listing_title}")

        except Exception as e:
            self.logger.error(f"✗ Error sending message: {str(e)}")
            self.messages_failed += 1
            self.log_progress(f"[{index}] ERROR: {listing_title} - {str(e)}")

        finally:
            await page.close()
            self.print_progress_summary()

    async def errback_close_page(self, failure):
        """Close page on error"""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.value}")

    def log_progress(self, message):
        """Log progress entry"""
        entry = {"timestamp": datetime.now().isoformat(), "message": message}
        self.progress_log.append(entry)

    def print_progress_summary(self):
        """Print current progress summary"""
        total = len(self.listings)
        processed = self.messages_sent + self.messages_failed + self.messages_skipped
        elapsed = (datetime.now() - self.start_time).total_seconds()

        self.logger.info("\n" + "=" * 80)
        self.logger.info("PROGRESS SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Processed: {processed}/{total} listings")
        self.logger.info(f"✓ Sent: {self.messages_sent}")
        self.logger.info(f"✗ Failed: {self.messages_failed}")
        self.logger.info(f"⊘ Skipped: {self.messages_skipped}")
        self.logger.info(f"⏱ Elapsed time: {elapsed:.1f}s")
        if self.messages_sent > 0:
            self.logger.info(
                f"📊 Avg time per message: {elapsed / self.messages_sent:.1f}s"
            )
        self.logger.info("=" * 80 + "\n")

    def closed(self, reason):
        """Called when spider closes"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("FINAL REPORT")
        self.logger.info("=" * 80)
        self.logger.info(f"Total listings processed: {len(self.listings)}")
        self.logger.info(f"✓ Messages sent successfully: {self.messages_sent}")
        self.logger.info(f"✗ Messages failed: {self.messages_failed}")
        self.logger.info(f"⊘ Messages skipped: {self.messages_skipped}")

        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"⏱ Total time: {elapsed:.1f}s ({elapsed / 60:.1f} minutes)")

        success_rate = (
            (self.messages_sent / len(self.listings) * 100) if self.listings else 0
        )
        self.logger.info(f"📊 Success rate: {success_rate:.1f}%")

        self.logger.info(f"\nContacted listings saved to: {self.contacted_file}")
        self.logger.info("=" * 80)

        # Save final progress log
        with open("messaging_log.json", "w") as f:
            json.dump(
                {
                    "summary": {
                        "total": len(self.listings),
                        "sent": self.messages_sent,
                        "failed": self.messages_failed,
                        "skipped": self.messages_skipped,
                        "elapsed_seconds": elapsed,
                        "success_rate": success_rate,
                    },
                    "progress": self.progress_log,
                },
                f,
                indent=2,
            )

        self.logger.info(f"Detailed log saved to: messaging_log.json\n")
