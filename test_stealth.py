#!/usr/bin/env python3
"""
Test script to verify anti-detection measures work correctly.
This script launches a browser with the anti-detection configuration
and opens the test HTML page.

Usage:
    python test_stealth.py
"""

import asyncio
import os
from playwright.async_api import async_playwright


# Browser selection - Change this to test different browsers
BROWSER = "firefox"  # Options: "chromium" or "firefox"

# Browser-specific configurations (same as in gumtree_messenger.py)
CHROMIUM_CONFIG = {
    "browser_type": "chromium",
    "launch_options": {
        "headless": False,
        "timeout": 30000,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1920,1080",
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
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

FIREFOX_CONFIG = {
    "browser_type": "firefox",
    "launch_options": {
        "headless": False,
        "timeout": 30000,
        "firefox_user_prefs": {
            "dom.webdriver.enabled": False,
            "useAutomationExtension": False,
            "general.platform.override": "MacIntel",
            "general.appversion.override": "5.0 (Macintosh)",
            "media.peerconnection.enabled": False,
            "privacy.trackingprotection.enabled": True,
            "geo.enabled": False,
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
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
}

# Select browser configuration
BROWSER_CONFIG = FIREFOX_CONFIG if BROWSER == "firefox" else CHROMIUM_CONFIG


async def inject_anti_detection(page):
    """Inject comprehensive anti-detection script"""
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

        // 2. Override navigator.webdriver to always return false
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
            configurable: true
        });

        // Remove webdriver from navigator prototype
        if (navigator.__proto__.hasOwnProperty('webdriver')) {
            delete navigator.__proto__.webdriver;
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

        // 10. Add realistic platform and hardware properties
        Object.defineProperty(navigator, 'platform', {
            get: () => 'MacIntel',
            configurable: true
        });

        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: true
        });

        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });

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

        // 20. Canvas Fingerprinting Protection
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const isFingerprintAttempt = this.width === 16 || this.width === 220 || this.height === 16;

            if (isFingerprintAttempt) {
                const ctx = this.getContext('2d');
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                const data = imageData.data;

                for (let i = 0; i < data.length; i += 4) {
                    data[i] = data[i] + Math.floor(Math.random() * 3) - 1;
                    data[i + 1] = data[i + 1] + Math.floor(Math.random() * 3) - 1;
                    data[i + 2] = data[i + 2] + Math.floor(Math.random() * 3) - 1;
                }
                ctx.putImageData(imageData, 0, 0);
            }

            return originalToDataURL.apply(this, arguments);
        };

        CanvasRenderingContext2D.prototype.getImageData = function() {
            const imageData = originalGetImageData.apply(this, arguments);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 10) {
                data[i] = data[i] + Math.floor(Math.random() * 3) - 1;
            }
            return imageData;
        };

        // 21. WebGL Fingerprinting Protection
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return originalGetParameter.apply(this, arguments);
        };

        if (window.WebGL2RenderingContext) {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return originalGetParameter2.apply(this, arguments);
            };
        }

        console.log('[Anti-Detection] All automation traces removed successfully');
        console.log('[Anti-Detection] Canvas fingerprinting protection enabled');
        console.log('[Anti-Detection] WebGL fingerprinting protection enabled');
    """)


async def main():
    """Main test function"""
    print("=" * 80)
    print("ANTI-DETECTION STEALTH TEST")
    print("=" * 80)
    print(f"Browser: {BROWSER}")
    print(f"User Agent: {BROWSER_CONFIG['user_agent']}")
    print("=" * 80)
    print()

    # Get path to test HTML file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_html_path = os.path.join(current_dir, "test_anti_detection.html")

    if not os.path.exists(test_html_path):
        print(f"❌ Error: Test file not found at {test_html_path}")
        return

    async with async_playwright() as p:
        # Launch browser
        print(f"🚀 Launching {BROWSER}...")
        browser_type = getattr(p, BROWSER_CONFIG["browser_type"])

        # Remove browser_type from launch options
        launch_options = BROWSER_CONFIG["launch_options"].copy()

        browser = await browser_type.launch(**launch_options)

        # Create context with user agent
        context = await browser.new_context(
            user_agent=BROWSER_CONFIG["user_agent"],
            viewport={"width": 1920, "height": 1080},
        )

        # Create page
        page = await context.new_page()

        # Inject anti-detection script
        print("💉 Injecting anti-detection script...")
        await inject_anti_detection(page)

        # Navigate to test page
        print(f"🌐 Opening test page: {test_html_path}")
        await page.goto(f"file://{test_html_path}")

        print()
        print("=" * 80)
        print("✅ Browser opened successfully!")
        print("=" * 80)
        print("📊 Check the browser window to see the test results.")
        print("🔍 All tests should show as PASSED if anti-detection is working.")
        print()
        print("Press Ctrl+C to close the browser and exit...")
        print("=" * 80)

        try:
            # Keep browser open until user closes it
            await page.wait_for_timeout(300000)  # 5 minutes
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
