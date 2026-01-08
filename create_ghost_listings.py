#!/usr/bin/env python3
"""
Script to create ghost listings in Supabase from JSON file
Ingests JSON with listing data and creates ghost listings in the database

Usage:
    python3 create_ghost_listings.py listing.json
    python3 create_ghost_listings.py listings.json
    python3 create_ghost_listings.py listings.json --max-inserts 10
    python3 create_ghost_listings.py listing.json --dry-run

JSON Schema:
    {
        "listing_id": "string",
        "title": "string (required)",
        "location": "string (required)",
        "price": "string",
        "description": "string",
        "url": "string",
        "reply_url": "string",
        "scraped_at": "ISO datetime string",
        "contact_info": "string (email or N/A)"
    }

Environment Variables Required:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_SERVICE_ROLE - Your Supabase service role key
"""

import os
import sys
import json
import argparse
import secrets
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def generate_claim_token(length=32):
    """Generate a unique claim token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def extract_seller_email(contact_info):
    """Extract seller email from contact_info field"""
    if not contact_info or contact_info == "N/A":
        return None
    
    contact_str = str(contact_info).strip()
    
    if '@' in contact_str:
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, contact_str)
        if match:
            return match.group(0)
        return contact_str
    
    return None


def determine_source_platform(url):
    """Determine source platform from URL"""
    if not url or url == "N/A":
        return "unknown"
    
    url_lower = url.lower()
    if "craigslist" in url_lower:
        return "craigslist"
    elif "gumtree" in url_lower:
        return "gumtree"
    else:
        return "unknown"


def check_duplicate(listing_data, supabase: Client):
    """Check if a similar listing already exists in Supabase"""
    title = (listing_data.get('title', '') or '').strip()[:500]
    location = (listing_data.get('location', '') or '').strip()
    
    if not title or not location:
        return None
    
    try:
        response = supabase.table('ghost_listings').select('id, title, location, status').eq('title', title).eq('location', location).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    except Exception as e:
        return None


def create_ghost_listing(listing_data, supabase: Client, skip_duplicates=True):
    """Create a single ghost listing in Supabase"""
    
    if skip_duplicates:
        duplicate = check_duplicate(listing_data, supabase)
        if duplicate:
            return {
                'success': False,
                'skipped': True,
                'reason': 'duplicate',
                'existing_id': duplicate.get('id'),
                'title': duplicate.get('title', '')[:50]
            }
    
    claim_token = generate_claim_token()
    seller_email = extract_seller_email(listing_data.get('contact_info'))
    source_platform = determine_source_platform(listing_data.get('url'))
    
    ghost_listing_data = {
        'claim_token': claim_token,
        'title': (listing_data.get('title', '') or '')[:500],
        'description': listing_data.get('description') or None,
        'original_price': listing_data.get('price') or None,
        'size': None,
        'location': listing_data.get('location', '') or '',
        'original_image_url': None,
        'seller_email': seller_email,
        'source_platform': source_platform,
        'status': 'pending_claim',
        'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
    }
    
    if not ghost_listing_data['title']:
        raise ValueError("Missing required field: title")
    
    if not ghost_listing_data['location']:
        raise ValueError("Missing required field: location")
    
    try:
        response = supabase.table('ghost_listings').insert(ghost_listing_data).execute()
        
        if response.data:
            return {
                'success': True,
                'claim_token': claim_token,
                'title': ghost_listing_data['title'][:50],
                'data': response.data[0] if response.data else None
            }
        else:
            return {
                'success': False,
                'error': 'No data returned from insert'
            }
    except Exception as e:
        error_msg = str(e)
        if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
            return create_ghost_listing(listing_data, supabase)
        else:
            return {
                'success': False,
                'error': error_msg
            }


def load_json_file(file_path):
    """Load JSON from file, handling both single objects and arrays"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path}: {e}")
        
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"JSON must be an object or array, got {type(data)}")


def main():
    parser = argparse.ArgumentParser(
        description='Create ghost listings in Supabase from JSON file'
    )
    parser.add_argument(
        'input_file',
        help='Path to JSON file with listing data (single object or array)'
    )
    parser.add_argument(
        '--max-inserts',
        type=int,
        default=0,
        help='Maximum number of listings to insert (0 = unlimited)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate JSON without inserting into database'
    )
    parser.add_argument(
        '--allow-duplicates',
        action='store_true',
        help='Allow duplicate listings (by default, duplicates are skipped)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("CREATE GHOST LISTINGS FROM JSON")
    print("=" * 60)
    print()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")
    
    if not supabase_url or not supabase_key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE not found in environment variables!")
        print("Please add them to your .env file")
        sys.exit(1)
    
    if not args.dry_run:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            print("Connected to Supabase successfully")
        except Exception as e:
            print(f"Failed to connect to Supabase: {e}")
            sys.exit(1)
    else:
        supabase = None
        print("DRY RUN MODE - No database operations will be performed")
    
    print()
    
    print(f"Loading JSON from: {args.input_file}")
    try:
        listings = load_json_file(args.input_file)
        print(f"Loaded {len(listings)} listing(s)")
    except Exception as e:
        print(f"Error loading JSON: {e}")
        sys.exit(1)
    
    print()
    
    if args.max_inserts > 0 and len(listings) > args.max_inserts:
        print(f"Limiting to first {args.max_inserts} listings")
        listings = listings[:args.max_inserts]
    
    print()
    print("=" * 60)
    print("PROCESSING LISTINGS")
    print("=" * 60)
    print()
    
    stats = {
        'processed': 0,
        'success': 0,
        'errors': 0,
        'skipped': 0
    }
    
    skip_duplicates = not args.allow_duplicates
    
    for idx, listing in enumerate(listings, 1):
        listing_id = listing.get('listing_id', 'N/A')
        title = listing.get('title', 'Unknown')[:50]
        
        print(f"[{idx}/{len(listings)}] Processing: {title}...")
        print(f"   Listing ID: {listing_id}")
        
        if args.dry_run:
            required_fields = ['title', 'location']
            missing = [f for f in required_fields if not listing.get(f)]
            if missing:
                print(f"   Missing required fields: {missing}")
                stats['errors'] += 1
            else:
                print(f"   Valid structure")
                stats['success'] += 1
            stats['processed'] += 1
        else:
            try:
                result = create_ghost_listing(listing, supabase, skip_duplicates=skip_duplicates)
                
                if result.get('skipped'):
                    stats['skipped'] += 1
                    print(f"   Skipped (duplicate already exists)")
                elif result['success']:
                    stats['success'] += 1
                    print(f"   Inserted ghost listing")
                    print(f"   Token: {result['claim_token'][:8]}...")
                else:
                    stats['errors'] += 1
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                
                stats['processed'] += 1
            except Exception as e:
                stats['errors'] += 1
                stats['processed'] += 1
                print(f"   Error: {str(e)}")
        
        print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Processed: {stats['processed']}")
    print(f"Success: {stats['success']}")
    if stats['skipped'] > 0:
        print(f"Skipped (duplicates): {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 60)
    
    if stats['errors'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

