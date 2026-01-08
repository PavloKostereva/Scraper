#!/usr/bin/env python3
"""
A/B Testing Script for Gumtree Messenger

This script splits listings into two groups (A and B) and allows testing
different configurations (browser, message template, delays, etc.)

Usage:
    python3 ab_testing.py input.json --group-a-browser chromium --group-b-browser firefox
    python3 ab_testing.py input.json --split 50-50 --group-a-delay 5 --group-b-delay 10
"""

import json
import os
import argparse
import random
from pathlib import Path


def load_listings(json_file):
    """Load listings from JSON file"""
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if content.endswith(','):
            content = content[:-1] + ']'
        if not content.endswith(']'):
            last_bracket = content.rfind(']')
            if last_bracket > 0:
                content = content[:last_bracket+1]
        
        listings = json.loads(content)
        return listings if isinstance(listings, list) else []


def split_listings(listings, split_ratio="50-50"):
    """Split listings into two groups based on ratio"""
    total = len(listings)
    
    if split_ratio == "50-50":
        split_point = total // 2
    elif split_ratio == "70-30":
        split_point = int(total * 0.7)
    elif split_ratio == "30-70":
        split_point = int(total * 0.3)
    else:
        # Parse custom ratio like "60-40"
        try:
            a_percent, b_percent = map(int, split_ratio.split('-'))
            split_point = int(total * (a_percent / 100))
        except:
            split_point = total // 2
    
    # Shuffle to randomize
    shuffled = listings.copy()
    random.shuffle(shuffled)
    
    group_a = shuffled[:split_point]
    group_b = shuffled[split_point:]
    
    return group_a, group_b


def create_config_file(output_file, listings, browser="firefox", delay=10, 
                      message_template="claim_message_template.txt", 
                      max_messages=0, fast_mode=False):
    """Create a config.json file for a test group"""
    config = {
        "email": os.getenv("GUMTREE_EMAIL", "dolinskiian25@gmail.com"),
        "password": os.getenv("GUMTREE_PASSWORD", ""),
        "input_json": output_file.replace('.json', '_listings.json'),
        "message_template": message_template,
        "max_messages": max_messages if max_messages > 0 else len(listings),
        "message_delay": delay,
        "skip_contacted": True,
        "fast_mode": fast_mode
    }
    
    # Save listings to separate file
    listings_file = config["input_json"]
    with open(listings_file, 'w', encoding='utf-8') as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)
    
    # Save config
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config


def update_browser_in_messenger(browser, group_name):
    """Update browser setting in gumtree_messenger.py for a specific group"""
    messenger_file = "gumtree_scraper/spiders/gumtree_messenger.py"
    
    if not os.path.exists(messenger_file):
        print(f"Warning: {messenger_file} not found, skipping browser update")
        return
    
    with open(messenger_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace BROWSER setting
    import re
    pattern = r'BROWSER\s*=\s*["\'](chromium|firefox)["\']'
    replacement = f'BROWSER = "{browser}"  # A/B Test Group {group_name}'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        
        with open(messenger_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated browser to {browser} in {messenger_file} for Group {group_name}")
    else:
        print(f"Could not find BROWSER setting in {messenger_file}")


def main():
    parser = argparse.ArgumentParser(
        description='A/B Testing setup for Gumtree Messenger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split 50-50, test Chromium vs Firefox
  python3 ab_testing.py bxb_dallas.json --group-a-browser chromium --group-b-browser firefox
  
  # Split 70-30, test different delays
  python3 ab_testing.py bxb_dallas.json --split 70-30 --group-a-delay 5 --group-b-delay 15
  
  # Test different message templates
  python3 ab_testing.py bxb_dallas.json --group-a-template template_a.txt --group-b-template template_b.txt
        """
    )
    
    parser.add_argument('input_file', help='Input JSON file with listings')
    parser.add_argument(
        '--split',
        default='50-50',
        choices=['50-50', '70-30', '30-70'],
        help='Split ratio (default: 50-50)'
    )
    
    # Group A options
    parser.add_argument('--group-a-browser', choices=['chromium', 'firefox'], 
                       default='firefox', help='Browser for Group A')
    parser.add_argument('--group-a-delay', type=int, default=10, 
                       help='Message delay (seconds) for Group A')
    parser.add_argument('--group-a-template', default='claim_message_template.txt',
                       help='Message template for Group A')
    parser.add_argument('--group-a-max', type=int, default=0,
                       help='Max messages for Group A (0 = all)')
    parser.add_argument('--group-a-fast', action='store_true',
                       help='Enable fast mode for Group A')
    
    # Group B options
    parser.add_argument('--group-b-browser', choices=['chromium', 'firefox'],
                       default='chromium', help='Browser for Group B')
    parser.add_argument('--group-b-delay', type=int, default=10,
                       help='Message delay (seconds) for Group B')
    parser.add_argument('--group-b-template', default='claim_message_template.txt',
                       help='Message template for Group B')
    parser.add_argument('--group-b-max', type=int, default=0,
                       help='Max messages for Group B (0 = all)')
    parser.add_argument('--group-b-fast', action='store_true',
                       help='Enable fast mode for Group B')
    
    args = parser.parse_args()
    
    # Load listings
    try:
        listings = load_listings(args.input_file)
    except Exception as e:
        print(f"Error loading listings: {e}")
        return
    
    if len(listings) == 0:
        print("No listings found!")
        return
    
    # Split listings
    group_a_listings, group_b_listings = split_listings(listings, args.split)
    
    # Create Group A config
    config_a = create_config_file(
        "config_group_a.json",
        group_a_listings,
        browser=args.group_a_browser,
        delay=args.group_a_delay,
        message_template=args.group_a_template,
        max_messages=args.group_a_max,
        fast_mode=args.group_a_fast
    )
    
    print(f"Created config_group_a.json with {len(group_a_listings)} listings")
    
    # Create Group B config
    config_b = create_config_file(
        "config_group_b.json",
        group_b_listings,
        browser=args.group_b_browser,
        delay=args.group_b_delay,
        message_template=args.group_b_template,
        max_messages=args.group_b_max,
        fast_mode=args.group_b_fast
    )
    
    print(f"Created config_group_b.json with {len(group_b_listings)} listings")
    print()
    print("To run Group A:")
    print(f"  1. Update gumtree_scraper/spiders/gumtree_messenger.py: BROWSER = \"{args.group_a_browser}\"")
    print("  2. cp config_group_a.json config.json")
    print("  3. scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright")
    print()
    print("To run Group B:")
    print(f"  1. Update gumtree_scraper/spiders/gumtree_messenger.py: BROWSER = \"{args.group_b_browser}\"")
    print("  2. cp config_group_b.json config.json")
    print("  3. scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright")


if __name__ == "__main__":
    main()

