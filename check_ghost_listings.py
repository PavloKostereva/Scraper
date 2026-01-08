#!/usr/bin/env python3
"""
Script to check ghost listings in Supabase
Shows recent ghost listings and their status
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def check_ghost_listings(limit=10, status=None):
    """Check ghost listings in Supabase"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")
    
    if not supabase_url or not supabase_key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE not found!")
        return
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        query = supabase.table('ghost_listings').select('*')
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).limit(limit)
        
        response = query.execute()
        
        if not response.data:
            print("No ghost listings found")
            return
        
        print("=" * 80)
        print(f"GHOST LISTINGS (showing {len(response.data)} most recent)")
        print("=" * 80)
        print()
        
        for idx, listing in enumerate(response.data, 1):
            print(f"[{idx}] {listing.get('title', 'N/A')[:60]}")
            print(f"     Location: {listing.get('location', 'N/A')}")
            print(f"     Price: {listing.get('original_price', 'N/A')}")
            print(f"     Status: {listing.get('status', 'N/A')}")
            print(f"     Platform: {listing.get('source_platform', 'N/A')}")
            print(f"     Claim Token: {listing.get('claim_token', 'N/A')[:16]}...")
            
            created_at = listing.get('created_at')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    print(f"     Created: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"     Created: {created_at}")
            
            expires_at = listing.get('expires_at')
            if expires_at:
                try:
                    dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    print(f"     Expires: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"     Expires: {expires_at}")
            
            print()
        
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")


def count_by_status():
    """Count ghost listings by status"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")
    
    if not supabase_url or not supabase_key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE not found!")
        return
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        response = supabase.table('ghost_listings').select('status').execute()
        
        if not response.data:
            print("No ghost listings found")
            return
        
        status_counts = {}
        for listing in response.data:
            status = listing.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("=" * 60)
        print("GHOST LISTINGS BY STATUS")
        print("=" * 60)
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        print(f"  TOTAL: {len(response.data)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "count":
        count_by_status()
    else:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
        status = sys.argv[2] if len(sys.argv) > 2 else None
        check_ghost_listings(limit=limit, status=status)

