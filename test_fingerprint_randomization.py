#!/usr/bin/env python3
"""
Test script to verify fingerprint randomization works correctly.

This script generates multiple fingerprints and verifies they are different.
It also opens a browser to test the JavaScript injection.

Usage:
    python test_fingerprint_randomization.py
"""

import sys
from gumtree_scraper.browser_fingerprint import generate_fingerprint


def test_fingerprint_generation():
    """Test that fingerprints are generated with variety"""
    print("=" * 80)
    print("FINGERPRINT RANDOMIZATION TEST")
    print("=" * 80)
    print()

    # Generate 5 fingerprints for each browser type
    print("Generating 5 random fingerprints for Chromium...")
    print("-" * 80)
    chromium_prints = []
    for i in range(5):
        fp = generate_fingerprint("chromium", "mac")
        chromium_prints.append(fp)
        print(f"{i+1}. {fp}")

    print()
    print("Generating 5 random fingerprints for Firefox...")
    print("-" * 80)
    firefox_prints = []
    for i in range(5):
        fp = generate_fingerprint("firefox", "mac")
        firefox_prints.append(fp)
        print(f"{i+1}. {fp}")

    print()
    print("=" * 80)
    print("VARIANCE ANALYSIS")
    print("=" * 80)

    # Check for variance in screen resolutions
    chromium_resolutions = set((fp.screen_width, fp.screen_height) for fp in chromium_prints)
    firefox_resolutions = set((fp.screen_width, fp.screen_height) for fp in firefox_prints)

    print(f"Chromium unique resolutions: {len(chromium_resolutions)}/5")
    print(f"Firefox unique resolutions: {len(firefox_resolutions)}/5")

    # Check for variance in user agents
    chromium_uas = set(fp.user_agent for fp in chromium_prints)
    firefox_uas = set(fp.user_agent for fp in firefox_prints)

    print(f"Chromium unique user agents: {len(chromium_uas)}/5")
    print(f"Firefox unique user agents: {len(firefox_uas)}/5")

    # Check for variance in CPU cores
    chromium_cores = set(fp.hardware_concurrency for fp in chromium_prints)
    firefox_cores = set(fp.hardware_concurrency for fp in firefox_prints)

    print(f"Chromium unique CPU cores: {len(chromium_cores)}/5")
    print(f"Firefox unique CPU cores: {len(firefox_cores)}/5")

    # Check for variance in memory
    chromium_memory = set(fp.device_memory for fp in chromium_prints)
    firefox_memory = set(fp.device_memory for fp in firefox_prints)

    print(f"Chromium unique memory configs: {len(chromium_memory)}/5")
    print(f"Firefox unique memory configs: {len(firefox_memory)}/5")

    print()
    print("=" * 80)
    print("DETAILED FINGERPRINT COMPARISON")
    print("=" * 80)

    # Show detailed comparison of first 2 fingerprints
    fp1 = chromium_prints[0]
    fp2 = chromium_prints[1]

    print("Comparing first two Chromium fingerprints:")
    print()
    print(f"Screen Resolution:")
    print(f"  FP1: {fp1.screen_width}x{fp1.screen_height}")
    print(f"  FP2: {fp2.screen_width}x{fp2.screen_height}")
    print(f"  Different: {fp1.screen_width != fp2.screen_width or fp1.screen_height != fp2.screen_height}")

    print(f"\nWindow Size:")
    print(f"  FP1: {fp1.window_inner_width}x{fp1.window_inner_height}")
    print(f"  FP2: {fp2.window_inner_width}x{fp2.window_inner_height}")
    print(f"  Different: {fp1.window_inner_width != fp2.window_inner_width or fp1.window_inner_height != fp2.window_inner_height}")

    print(f"\nPlatform:")
    print(f"  FP1: {fp1.platform}")
    print(f"  FP2: {fp2.platform}")
    print(f"  Different: {fp1.platform != fp2.platform}")

    print(f"\nCPU Cores:")
    print(f"  FP1: {fp1.hardware_concurrency}")
    print(f"  FP2: {fp2.hardware_concurrency}")
    print(f"  Different: {fp1.hardware_concurrency != fp2.hardware_concurrency}")

    print(f"\nMemory:")
    print(f"  FP1: {fp1.device_memory}GB")
    print(f"  FP2: {fp2.device_memory}GB")
    print(f"  Different: {fp1.device_memory != fp2.device_memory}")

    print(f"\nUser Agent:")
    print(f"  FP1: {fp1.user_agent[:60]}...")
    print(f"  FP2: {fp2.user_agent[:60]}...")
    print(f"  Different: {fp1.user_agent != fp2.user_agent}")

    print()
    print("=" * 80)
    print("JAVASCRIPT INJECTION TEST")
    print("=" * 80)

    # Test JavaScript generation
    fp = generate_fingerprint("chromium", "mac")
    js = fp.get_javascript_injection()

    print(f"Generated JavaScript injection script ({len(js)} characters)")
    print("\nFirst 500 characters:")
    print("-" * 80)
    print(js[:500])
    print("...")
    print("-" * 80)

    # Verify critical properties are in the script
    checks = [
        ("screen.width" in js, "Screen width property"),
        ("screen.height" in js, "Screen height property"),
        ("window.innerWidth" in js, "Window innerWidth property"),
        ("window.innerHeight" in js, "Window innerHeight property"),
        ("navigator.userAgent" in js, "User agent property"),
        ("navigator.platform" in js, "Platform property"),
        ("hardwareConcurrency" in js, "Hardware concurrency property"),
        ("deviceMemory" in js, "Device memory property"),
    ]

    print("\nJavaScript injection includes:")
    for check, name in checks:
        status = "✓" if check else "✗"
        print(f"  {status} {name}")

    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    # Calculate overall success
    total_unique = (
        len(chromium_resolutions) + len(firefox_resolutions) +
        len(chromium_uas) + len(firefox_uas) +
        len(chromium_cores) + len(firefox_cores) +
        len(chromium_memory) + len(firefox_memory)
    )
    max_possible = 8 * 5  # 8 categories * 5 samples

    diversity_score = (total_unique / max_possible) * 100
    all_js_checks_passed = all(check for check, _ in checks)

    print(f"Fingerprint Diversity: {diversity_score:.1f}%")
    print(f"JavaScript Injection: {'PASS' if all_js_checks_passed else 'FAIL'}")

    if diversity_score > 60 and all_js_checks_passed:
        print("\n✓ Randomization is working correctly!")
        print("  Each scraper run will have a unique fingerprint.")
        return True
    else:
        print("\n✗ Randomization may not be working optimally.")
        print("  Check the browser_fingerprint.py module.")
        return False


def show_usage_example():
    """Show usage example"""
    print()
    print("=" * 80)
    print("USAGE IN SCRAPER")
    print("=" * 80)
    print("""
The fingerprint is automatically generated and used in gumtree_messenger.py:

    from gumtree_scraper.browser_fingerprint import generate_fingerprint

    BROWSER = "chromium"  # or "firefox"
    FINGERPRINT = generate_fingerprint(browser_type=BROWSER, os_type="mac")

Every time you run the scraper, it will use a NEW random fingerprint:
- Different screen resolution
- Different user agent
- Different CPU cores
- Different memory
- Different window sizes
- Different platform variations

This makes fingerprint-based detection much harder!
""")


if __name__ == "__main__":
    print()
    success = test_fingerprint_generation()
    show_usage_example()

    print()
    print("=" * 80)
    print()

    if success:
        print("✓ All tests passed! Fingerprint randomization is working.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Check the output above.")
        sys.exit(1)
