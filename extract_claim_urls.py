#!/usr/bin/env python3
"""
Extract Claim URLs from JSON files

Extracts claim URLs from processed listings and outputs them to a text file.
Useful for providing URLs to clients after processing.

Usage:
    python3 extract_claim_urls.py claim_links_messenger.json --limit 100
    python3 extract_claim_urls.py claim_links_messenger.json --output urls.txt
"""

import json
import os
import argparse
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


def extract_urls(listings, url_type="claim_link", limit=0):
    """Extract URLs from listings"""
    urls = []
    
    for listing in listings:
        url = listing.get(url_type)
        if url:
            urls.append(url)
        
        if limit > 0 and len(urls) >= limit:
            break
    
    return urls


def main():
    parser = argparse.ArgumentParser(
        description='Extract claim URLs from JSON listings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract first 100 claim URLs
  python3 extract_claim_urls.py claim_links_messenger.json --limit 100
  
  # Extract all reply URLs
  python3 extract_claim_urls.py claim_links_messenger.json --type reply_url
  
  # Extract to custom file
  python3 extract_claim_urls.py claim_links_messenger.json --output my_urls.txt
        """
    )
    
    parser.add_argument('input_file', help='Input JSON file with listings')
    parser.add_argument(
        '--type',
        choices=['claim_link', 'url', 'reply_url'],
        default='claim_link',
        help='Type of URL to extract (default: claim_link)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Maximum number of URLs to extract (0 = all)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output file (default: claim_urls.txt or urls.txt or reply_urls.txt)'
    )
    parser.add_argument(
        '--format',
        choices=['plain', 'json', 'csv'],
        default='plain',
        help='Output format (default: plain)'
    )
    
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
    
    # Extract URLs
    urls = extract_urls(listings, url_type=args.type, limit=args.limit)
    
    if len(urls) == 0:
        print("No URLs found!")
        return
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        if args.type == "claim_link":
            output_file = "claim_urls.txt"
        elif args.type == "reply_url":
            output_file = "reply_urls.txt"
        else:
            output_file = "urls.txt"
    
    # Write output
    if args.format == "plain":
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(f"{url}\n")
    
    elif args.format == "json":
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(urls, f, indent=2, ensure_ascii=False)
    
    elif args.format == "csv":
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("url\n")
            for url in urls:
                f.write(f"{url}\n")
    
    print(f"Saved {len(urls)} URLs to {output_file}")


if __name__ == "__main__":
    main()

