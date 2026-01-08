"""
Browser Fingerprint Randomization Module

This module generates randomized but realistic browser fingerprints
to avoid detection through fingerprinting analysis.
"""

import random
from typing import Dict, List, Tuple


class BrowserFingerprint:
    """Generates randomized browser fingerprint attributes"""

    # Common screen resolutions (width, height)
    COMMON_RESOLUTIONS = [
        (1920, 1080),  # Full HD
        (1920, 1200),  # WUXGA
        (2560, 1440),  # QHD
        (2560, 1600),  # WQXGA
        (1680, 1050),  # WSXGA+
        (1440, 900),   # WXGA+
        (1366, 768),   # HD
        (3840, 2160),  # 4K
        (2880, 1800),  # MacBook Pro Retina
        (2560, 1080),  # Ultrawide
    ]

    # User agents for different browsers and OS combinations
    USER_AGENTS = {
        "chrome_mac": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ],
        "chrome_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ],
        "firefox_mac": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.6; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.6; rv:121.0) Gecko/20100101 Firefox/121.0",
        ],
        "firefox_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ],
    }

    # Platform strings that match OS in user agent
    PLATFORMS = {
        "mac": ["MacIntel", "Macintosh"],
        "windows": ["Win32", "Win64"],
        "linux": ["Linux x86_64", "Linux"],
    }

    def __init__(self, browser_type: str = "chromium", os_type: str = "mac"):
        """
        Initialize fingerprint generator

        Args:
            browser_type: "chromium" or "firefox"
            os_type: "mac", "windows", or "linux"
        """
        self.browser_type = browser_type
        self.os_type = os_type
        self._generate_fingerprint()

    def _generate_fingerprint(self):
        """Generate all randomized attributes"""
        self._generate_screen_properties()
        self._generate_user_agent()
        self._generate_hardware_properties()
        self._generate_window_properties()

    def _generate_screen_properties(self):
        """Generate randomized screen properties"""
        # Pick a random resolution
        self.screen_width, self.screen_height = random.choice(self.COMMON_RESOLUTIONS)

        # Available height is slightly less than full height (accounts for taskbar/menubar)
        taskbar_height = random.randint(25, 75)
        self.screen_avail_height = self.screen_height - taskbar_height
        self.screen_avail_width = self.screen_width

        # Color depth (24 or 32 bit)
        self.color_depth = random.choice([24, 32])
        self.pixel_depth = self.color_depth

    def _generate_user_agent(self):
        """Generate randomized user agent"""
        # Select user agent based on browser and OS
        if self.browser_type == "chromium":
            if self.os_type == "mac":
                ua_list = self.USER_AGENTS["chrome_mac"]
            else:
                ua_list = self.USER_AGENTS["chrome_windows"]
        else:  # firefox
            if self.os_type == "mac":
                ua_list = self.USER_AGENTS["firefox_mac"]
            else:
                ua_list = self.USER_AGENTS["firefox_windows"]

        self.user_agent = random.choice(ua_list)

        # Generate matching appVersion (must be consistent with userAgent)
        # Extract version from user agent
        if self.browser_type == "chromium":
            # Chrome UA format: "...Chrome/131.0.0.0..."
            # appVersion should be: "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
            # Basically everything after "Mozilla/"
            self.app_version = self.user_agent.replace("Mozilla/", "")
        else:  # firefox
            # Firefox UA format: "...Gecko/20100101 Firefox/121.0"
            # appVersion should be: "5.0 (Macintosh)"
            if "Macintosh" in self.user_agent:
                self.app_version = "5.0 (Macintosh)"
            elif "Windows" in self.user_agent:
                self.app_version = "5.0 (Windows)"
            else:
                self.app_version = "5.0 (X11)"

    def _generate_hardware_properties(self):
        """Generate randomized hardware properties"""
        # CPU cores (realistic range)
        self.hardware_concurrency = random.choice([4, 6, 8, 10, 12, 16])

        # Device memory in GB (realistic range)
        self.device_memory = random.choice([4, 8, 16, 32])

        # Platform string matching the OS
        if self.os_type == "mac":
            self.platform = random.choice(self.PLATFORMS["mac"])
        elif self.os_type == "windows":
            self.platform = random.choice(self.PLATFORMS["windows"])
        else:
            self.platform = random.choice(self.PLATFORMS["linux"])

    def _generate_window_properties(self):
        """Generate randomized window properties"""
        # Window size is typically smaller than screen size
        # Account for browser chrome (address bar, tabs, etc.)
        browser_chrome_height = random.randint(80, 150)
        browser_chrome_width = random.randint(0, 20)

        self.window_inner_width = self.screen_width - browser_chrome_width
        self.window_inner_height = self.screen_height - browser_chrome_height

        # Outer dimensions (includes browser UI)
        self.window_outer_width = self.screen_width
        self.window_outer_height = self.screen_height

        # Window position on screen (random but reasonable)
        self.window_screen_x = random.randint(0, 100)
        self.window_screen_y = random.randint(0, 100)

        # Page scroll offsets (start at 0 for new page)
        self.page_x_offset = 0
        self.page_y_offset = 0

    def get_screen_properties(self) -> Dict:
        """Get randomized screen properties"""
        return {
            "width": self.screen_width,
            "height": self.screen_height,
            "availWidth": self.screen_avail_width,
            "availHeight": self.screen_avail_height,
            "colorDepth": self.color_depth,
            "pixelDepth": self.pixel_depth,
        }

    def get_window_properties(self) -> Dict:
        """Get randomized window properties"""
        return {
            "innerWidth": self.window_inner_width,
            "innerHeight": self.window_inner_height,
            "outerWidth": self.window_outer_width,
            "outerHeight": self.window_outer_height,
            "screenX": self.window_screen_x,
            "screenY": self.window_screen_y,
            "pageXOffset": self.page_x_offset,
            "pageYOffset": self.page_y_offset,
        }

    def get_navigator_properties(self) -> Dict:
        """Get randomized navigator properties"""
        return {
            "userAgent": self.user_agent,
            "appVersion": self.app_version,
            "platform": self.platform,
            "hardwareConcurrency": self.hardware_concurrency,
            "deviceMemory": self.device_memory,
        }

    def get_viewport(self) -> Dict:
        """Get viewport dimensions for Playwright context"""
        return {
            "width": self.window_inner_width,
            "height": self.window_inner_height,
        }

    def to_dict(self) -> Dict:
        """Get all properties as a dictionary"""
        return {
            "screen": self.get_screen_properties(),
            "window": self.get_window_properties(),
            "navigator": self.get_navigator_properties(),
            "viewport": self.get_viewport(),
        }

    def get_javascript_injection(self) -> str:
        """
        Get JavaScript code to inject these randomized properties

        Returns:
            JavaScript code as string
        """
        screen = self.get_screen_properties()
        window_props = self.get_window_properties()
        nav = self.get_navigator_properties()

        return f"""
        // Randomized Screen Properties
        Object.defineProperty(window.screen, 'width', {{
            get: () => {screen['width']},
            configurable: true
        }});
        Object.defineProperty(window.screen, 'height', {{
            get: () => {screen['height']},
            configurable: true
        }});
        Object.defineProperty(window.screen, 'availWidth', {{
            get: () => {screen['availWidth']},
            configurable: true
        }});
        Object.defineProperty(window.screen, 'availHeight', {{
            get: () => {screen['availHeight']},
            configurable: true
        }});
        Object.defineProperty(window.screen, 'colorDepth', {{
            get: () => {screen['colorDepth']},
            configurable: true
        }});
        Object.defineProperty(window.screen, 'pixelDepth', {{
            get: () => {screen['pixelDepth']},
            configurable: true
        }});

        // Randomized Window Properties
        Object.defineProperty(window, 'innerWidth', {{
            get: () => {window_props['innerWidth']},
            configurable: true
        }});
        Object.defineProperty(window, 'innerHeight', {{
            get: () => {window_props['innerHeight']},
            configurable: true
        }});
        Object.defineProperty(window, 'outerWidth', {{
            get: () => {window_props['outerWidth']},
            configurable: true
        }});
        Object.defineProperty(window, 'outerHeight', {{
            get: () => {window_props['outerHeight']},
            configurable: true
        }});
        Object.defineProperty(window, 'screenX', {{
            get: () => {window_props['screenX']},
            configurable: true
        }});
        Object.defineProperty(window, 'screenY', {{
            get: () => {window_props['screenY']},
            configurable: true
        }});
        Object.defineProperty(window, 'pageXOffset', {{
            get: () => {window_props['pageXOffset']},
            configurable: true
        }});
        Object.defineProperty(window, 'pageYOffset', {{
            get: () => {window_props['pageYOffset']},
            configurable: true
        }});

        // Randomized Navigator Properties
        Object.defineProperty(navigator, 'userAgent', {{
            get: () => "{nav['userAgent']}",
            configurable: true
        }});
        Object.defineProperty(navigator, 'appVersion', {{
            get: () => "{nav['appVersion']}",
            configurable: true
        }});
        Object.defineProperty(navigator, 'platform', {{
            get: () => "{nav['platform']}",
            configurable: true
        }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {nav['hardwareConcurrency']},
            configurable: true
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {nav['deviceMemory']},
            configurable: true
        }});

        console.log('[Fingerprint] Randomized fingerprint applied');
        console.log('[Fingerprint] Screen: {screen['width']}x{screen['height']}');
        console.log('[Fingerprint] Platform: {nav['platform']}');
        console.log('[Fingerprint] CPU Cores: {nav['hardwareConcurrency']}');
        console.log('[Fingerprint] User Agent matches App Version: {{userAgentMatchesAppVersion}}');
        """

        # Check if UA and appVersion match
        js = js.format(
            userAgentMatchesAppVersion="true" if nav['appVersion'] in nav['userAgent'] else "true"
        )

        return js

    def __repr__(self):
        """String representation"""
        return (
            f"BrowserFingerprint(browser={self.browser_type}, os={self.os_type}, "
            f"screen={self.screen_width}x{self.screen_height}, "
            f"platform={self.platform}, cores={self.hardware_concurrency})"
        )


def generate_fingerprint(browser_type: str = "chromium", os_type: str = "mac") -> BrowserFingerprint:
    """
    Convenience function to generate a random fingerprint

    Args:
        browser_type: "chromium" or "firefox"
        os_type: "mac", "windows", or "linux"

    Returns:
        BrowserFingerprint instance with randomized properties
    """
    return BrowserFingerprint(browser_type, os_type)
