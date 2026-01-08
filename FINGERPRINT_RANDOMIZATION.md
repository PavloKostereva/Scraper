# Fingerprint Randomization Guide

## Overview

This implementation adds **randomized browser fingerprinting** to make each scraper session unique and avoid pattern-based detection. Every time you run the scraper, it uses a completely different but realistic browser fingerprint.

## What Gets Randomized

### 1. **Screen Properties** 🖥️
```javascript
// Different every run!
screen.width        // 1920, 2560, 3840, etc.
screen.height       // 1080, 1440, 2160, etc.
screen.availWidth   // Slightly less than width
screen.availHeight  // Accounts for menubar/taskbar
screen.colorDepth   // 24 or 32 bit
screen.pixelDepth   // Matches colorDepth
```

**Why:** Fingerprinting scripts use screen resolution as a major identifier. By randomizing this, each session appears to come from a different computer.

### 2. **Window Properties** 🪟
```javascript
// Different every run!
window.innerWidth   // Based on screen size - browser chrome
window.innerHeight  // Based on screen size - browser chrome
window.outerWidth   // Includes browser UI
window.outerHeight  // Includes browser UI
window.screenX      // Random position on screen
window.screenY      // Random position on screen
window.pageXOffset  // Starts at 0
window.pageYOffset  // Starts at 0
```

**Why:** Window dimensions vary between users based on their preferences and screen size. Randomizing creates realistic diversity.

### 3. **Navigator Properties** 🧭
```javascript
// Different every run!
navigator.userAgent         // Rotates through 5+ real user agents per browser
navigator.platform          // MacIntel, Macintosh, Win32, Win64, etc.
navigator.hardwareConcurrency  // 4, 6, 8, 10, 12, or 16 cores
navigator.deviceMemory      // 4, 8, 16, or 32 GB
```

**Why:** These properties create a unique hardware signature. By rotating through realistic combinations, we avoid having a consistent fingerprint across sessions.

## Available Screen Resolutions

The system randomly selects from these common resolutions:

| Resolution | Name | Common Use |
|------------|------|------------|
| 1920x1080 | Full HD | Most common desktop |
| 1920x1200 | WUXGA | 16:10 monitors |
| 2560x1440 | QHD | High-end displays |
| 2560x1600 | WQXGA | MacBook Pro, high-end |
| 1680x1050 | WSXGA+ | Older wide monitors |
| 1440x900 | WXGA+ | MacBook Air |
| 1366x768 | HD | Laptops |
| 3840x2160 | 4K UHD | High-end desktops |
| 2880x1800 | Retina | MacBook Pro Retina |
| 2560x1080 | Ultrawide | Ultrawide monitors |

## User Agent Rotation

### Chromium (Mac) - 5 Variants
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/131.0.0.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130.0.0.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/129.0.0.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_0) Chrome/131.0.0.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_0) Chrome/131.0.0.0
```

### Chromium (Windows) - 4 Variants
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0
Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0
Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0
Mozilla/5.0 (Windows NT 11.0; Win64; x64) Chrome/131.0.0.0
```

### Firefox (Mac) - 5 Variants
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Firefox/121.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Firefox/120.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Firefox/119.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 11.6; rv:121.0) Firefox/121.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 12.6; rv:121.0) Firefox/121.0
```

### Firefox (Windows) - 4 Variants
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Firefox/121.0
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Firefox/120.0
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Firefox/119.0
Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:121.0) Firefox/121.0
```

## How It Works

### 1. Generation on Spider Init
```python
# At the top of gumtree_messenger.py
from gumtree_scraper.browser_fingerprint import generate_fingerprint

BROWSER = "firefox"  # or "chromium"
FINGERPRINT = generate_fingerprint(browser_type=BROWSER, os_type="mac")
```

**When:** A new fingerprint is generated every time the spider starts.

### 2. Browser Configuration
```python
# The fingerprint automatically configures the browser
CHROMIUM_CONFIG = {
    "launch_options": {
        "args": [
            f"--window-size={FINGERPRINT.window_inner_width},{FINGERPRINT.window_inner_height}",
            # ... other args
        ],
    },
    "user_agent": FINGERPRINT.user_agent,  # Random user agent
    "viewport": FINGERPRINT.get_viewport(),  # Random viewport
}
```

### 3. JavaScript Injection
```python
# In hide_automation() method
async def hide_automation(self, page):
    # Inject fingerprint FIRST (before page loads)
    fingerprint_script = FINGERPRINT.get_javascript_injection()
    await page.add_init_script(fingerprint_script)

    # Then inject other anti-detection measures
    await page.add_init_script("""...""")
```

**Result:** All JavaScript that checks screen size, window size, platform, etc. will see the randomized values.

## Testing Randomization

### Run the Test Script
```bash
python test_fingerprint_randomization.py
```

**Output:**
```
==================================================
FINGERPRINT RANDOMIZATION TEST
==================================================

Generating 5 random fingerprints for Chromium...
1. BrowserFingerprint(browser=chromium, os=mac, screen=2560x1440, platform=MacIntel, cores=8)
2. BrowserFingerprint(browser=chromium, os=mac, screen=1920x1080, platform=MacIntel, cores=12)
3. BrowserFingerprint(browser=chromium, os=mac, screen=2880x1800, platform=Macintosh, cores=6)
4. BrowserFingerprint(browser=chromium, os=mac, screen=3840x2160, platform=MacIntel, cores=16)
5. BrowserFingerprint(browser=chromium, os=mac, screen=1680x1050, platform=MacIntel, cores=4)

...

✓ Randomization is working correctly!
  Each scraper run will have a unique fingerprint.
```

### Manual Verification

1. Run the scraper:
   ```bash
   scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
   ```

2. Check the startup log:
   ```
   ==================================================
   RANDOMIZED FINGERPRINT
   ==================================================
   Browser: firefox
   Screen: 2560x1440
   Viewport: 2540x1290
   Platform: MacIntel
   CPU Cores: 12
   Memory: 16GB
   User Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0)...
   ==================================================
   ```

3. In the browser console (if headless=False), test:
   ```javascript
   // Check screen
   console.log(screen.width, screen.height);  // Different each run

   // Check window
   console.log(window.innerWidth, window.innerHeight);  // Different each run

   // Check navigator
   console.log(navigator.platform);  // May vary
   console.log(navigator.hardwareConcurrency);  // Different each run
   console.log(navigator.userAgent);  // Different each run
   ```

## Benefits

### 1. **Prevents Pattern Detection** 🔒
Traditional automation runs the same fingerprint every time:
- ❌ Every session: 1920x1080, 8 cores, same user agent
- ✅ Now: Completely different fingerprint each run

### 2. **Realistic Variance** 🎲
The randomization uses only realistic, common values:
- Real screen resolutions from actual devices
- Real user agents from recent browser versions
- Realistic CPU core counts (4-16)
- Realistic memory sizes (4-32GB)

### 3. **Internally Consistent** ✅
All values are correlated properly:
- MacOS = MacIntel platform + Mac user agent
- Larger screens = larger viewports
- Window size < Screen size (accounts for browser chrome)
- availHeight < height (accounts for menubar)

### 4. **No Duplicate Fingerprints** 🆕
With 10 resolutions × 5 user agents × 6 CPU configs × 4 memory sizes:
- **1,200+ possible unique fingerprints**
- Extremely unlikely to repeat the same combination

## Advanced Usage

### Change OS Type
```python
# In gumtree_messenger.py, change:
FINGERPRINT = generate_fingerprint(browser_type=BROWSER, os_type="windows")
```

Options: `"mac"`, `"windows"`, `"linux"`

### Programmatic Access
```python
from gumtree_scraper.browser_fingerprint import BrowserFingerprint

# Create specific fingerprint
fp = BrowserFingerprint(browser_type="chromium", os_type="mac")

# Access properties
print(fp.screen_width)           # e.g., 2560
print(fp.user_agent)              # e.g., "Mozilla/5.0..."
print(fp.hardware_concurrency)    # e.g., 12

# Get as dictionary
data = fp.to_dict()
print(data["screen"]["width"])    # 2560
print(data["navigator"]["platform"])  # "MacIntel"

# Get JavaScript
js = fp.get_javascript_injection()
# Contains all the Object.defineProperty calls
```

### Add More Resolutions
Edit `gumtree_scraper/browser_fingerprint.py`:
```python
COMMON_RESOLUTIONS = [
    (1920, 1080),
    (2560, 1440),
    # Add your custom resolution:
    (5120, 2880),  # 5K display
]
```

### Add More User Agents
Edit `gumtree_scraper/browser_fingerprint.py`:
```python
USER_AGENTS = {
    "chrome_mac": [
        "Mozilla/5.0 (Macintosh...) Chrome/131.0.0.0...",
        # Add your custom UA:
        "Mozilla/5.0 (Macintosh...) Chrome/132.0.0.0...",
    ],
}
```

## Implementation Files

1. **`gumtree_scraper/browser_fingerprint.py`** - Core randomization module
2. **`gumtree_scraper/spiders/gumtree_messenger.py`** - Uses fingerprint
3. **`test_fingerprint_randomization.py`** - Test script

## Compatibility with Anti-Detection

The fingerprint randomization works **in combination** with the anti-detection measures:

1. **Fingerprint injected FIRST** - Sets the baseline properties
2. **Anti-detection injected SECOND** - Removes automation traces

Both scripts run before any page content loads, making them very effective.

## Logging

Every scraper run logs the fingerprint:
```
2025-11-10 22:30:15 [gumtree_messenger] INFO: ==================================================
2025-11-10 22:30:15 [gumtree_messenger] INFO: RANDOMIZED FINGERPRINT
2025-11-10 22:30:15 [gumtree_messenger] INFO: ==================================================
2025-11-10 22:30:15 [gumtree_messenger] INFO: Browser: firefox
2025-11-10 22:30:15 [gumtree_messenger] INFO: Screen: 2560x1440
2025-11-10 22:30:15 [gumtree_messenger] INFO: Viewport: 2540x1290
2025-11-10 22:30:15 [gumtree_messenger] INFO: Platform: MacIntel
2025-11-10 22:30:15 [gumtree_messenger] INFO: CPU Cores: 12
2025-11-10 22:30:15 [gumtree_messenger] INFO: Memory: 16GB
2025-11-10 22:30:15 [gumtree_messenger] INFO: ==================================================
```

This helps track which fingerprint was used for each run.

## Summary

✅ **What's Randomized:**
- Screen resolution (10 options)
- Window size (calculated from screen)
- User agent (5 per browser)
- Platform (2-3 per OS)
- CPU cores (6 options)
- Device memory (4 options)
- Color depth (2 options)

✅ **Total Combinations:** 1,200+

✅ **Realistic:** All values from real devices

✅ **Consistent:** Properties correlate properly

✅ **Automatic:** New fingerprint every run

✅ **Logged:** Visible in spider output

🎉 **Result:** Fingerprint-based detection becomes much harder!
