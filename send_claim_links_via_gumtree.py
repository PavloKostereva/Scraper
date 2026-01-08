#!/usr/bin/env python3
"""
Script to send claim links via Gumtree messenger
Reads ghost listings from Supabase and creates JSON for gumtree_messenger
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()


def get_ghost_listings_from_supabase():
    """Get ghost listings from Supabase that need claim links sent"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE not found!")
        return []

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get ghost listings with status='pending_claim' that haven't been messaged yet
        # You might want to add a field like 'claim_link_sent' to track this
        response = supabase.table('ghost_listings').select('*').eq('status', 'pending_claim').execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"❌ Error fetching from Supabase: {e}")
        return []


def load_real_listings_from_json(json_file='gumtree_listings.json'):
    """Load real listings from JSON file"""
    if not os.path.exists(json_file):
        print(f"⚠️  JSON file not found: {json_file}")
        return []
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Try to fix common JSON issues
            if content.endswith(','):
                content = content[:-1] + ']'
            if not content.endswith(']'):
                # Try to find last valid entry
                last_bracket = content.rfind(']')
                if last_bracket > 0:
                    content = content[:last_bracket+1]
            
            listings = json.loads(content)
            return listings if isinstance(listings, list) else []
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"   Trying to load partial data...")
        # Try to load valid entries line by line
        try:
            listings = []
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract individual JSON objects
                import re
                # Find all { ... } blocks that look like listings
                pattern = r'\{[^{}]*"url"[^{}]*\}'
                matches = re.findall(pattern, content)
                for match in matches[:100]:  # Limit to first 100
                    try:
                        listing = json.loads(match)
                        if 'url' in listing:
                            listings.append(listing)
                    except:
                        continue
            print(f"✅ Loaded {len(listings)} listings from partial parse")
            return listings
        except Exception as e2:
            print(f"❌ Failed to parse even partially: {e2}")
            return []
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return []


def create_messenger_json(ghost_listings, base_url="http://localhost:8080"):
    """Create JSON file for gumtree_messenger with claim links
    Uses real listings from gumtree_listings.json and adds claim_link from Supabase
    """
    
    # Load real listings with valid URLs
    print("📥 Loading real listings from gumtree_listings.json...")
    real_listings = load_real_listings_from_json()
    
    if not real_listings:
        print("❌ No real listings found! Using ghost listings only (URLs may be invalid)")
        # Fallback to ghost listings
        real_listings = []
    
    # Create mapping of claim tokens by title+location
    tokens_map = {}
    for ghost in ghost_listings:
        claim_token = ghost.get('claim_token')
        if not claim_token:
            continue
        # Use title+location as key for matching
        key = f"{ghost.get('title', '')[:50]}_{ghost.get('location', '')}"
        if key not in tokens_map:
            tokens_map[key] = claim_token
    
    print(f"✅ Found {len(tokens_map)} claim tokens")
    print(f"✅ Found {len(real_listings)} real listings")
    
    messenger_listings = []
    matched = 0
    
    # Match real listings with claim tokens
    for listing in real_listings:
        title = listing.get('title', '')[:50]
        location = listing.get('location', '')
        key = f"{title}_{location}"
        
        claim_token = tokens_map.get(key)
        
        if claim_token:
            claim_link = f"{base_url}/claim/{claim_token}"
            # Add claim_link to real listing
            listing_with_claim = listing.copy()
            listing_with_claim['claim_link'] = claim_link
            messenger_listings.append(listing_with_claim)
            matched += 1
        else:
            # Skip if no claim token found
            continue
    
    print(f"✅ Matched {matched} listings with claim tokens")
    
    return messenger_listings


def main():
    print("=" * 60)
    print("SEND CLAIM LINKS VIA GUMTREE MESSENGER")
    print("=" * 60)
    print()
    
    # Get ghost listings from Supabase
    print("📥 Fetching ghost listings from Supabase...")
    ghost_listings = get_ghost_listings_from_supabase()
    
    if not ghost_listings:
        print("❌ No ghost listings found or error occurred")
        return
    
    print(f"✅ Found {len(ghost_listings)} ghost listings")
    print()
    
    # Create messenger JSON
    print("📝 Creating messenger JSON...")
    base_url = os.getenv("VITE_PUBLIC_SITE_URL", "http://localhost:8080")
    messenger_listings = create_messenger_json(ghost_listings, base_url)
    
    if not messenger_listings:
        print("❌ No listings to send")
        return
    
    # Save to JSON file
    output_file = "claim_links_messenger.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(messenger_listings, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created {output_file} with {len(messenger_listings)} listings")
    print()
    print("=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print(f"1. Update config.json:")
    print(f'   "input_json": "{output_file}"')
    print(f'   "message_template": "claim_message_template.txt"')
    print()
    print("2. Run gumtree_messenger:")
    print("   python3 -m scrapy crawl gumtree_messenger \\")
    print("     -s SETTINGS_MODULE=gumtree_scraper.settings_playwright")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()

