# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os
import secrets
import string
from datetime import datetime, timedelta
from itemadapter import ItemAdapter
from dotenv import load_dotenv
from supabase import create_client, Client
from scrapy.exceptions import CloseSpider

# Load environment variables
load_dotenv()


class GumtreeScraperPipeline:
    def process_item(self, item, spider):
        """Basic pipeline for item validation"""
        adapter = ItemAdapter(item)

        # Clean up whitespace in text fields
        for field in ['title', 'description', 'location', 'price']:
            if adapter.get(field):
                adapter[field] = ' '.join(adapter[field].split())

        return item


class JsonWriterPipeline:
    """Pipeline to write items to a JSON file"""

    def open_spider(self, spider):
        self.file = open('gumtree_listings.json', 'w', encoding='utf-8')
        self.file.write('[\n')
        self.first_item = True

    def close_spider(self, spider):
        self.file.write('\n]')
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False, indent=2)
        if not self.first_item:
            self.file.write(',\n')
        self.file.write(line)
        self.first_item = False
        return item


class SupabasePipeline:
    """Pipeline to write items to Supabase ghost_listings table"""

    def __init__(self):
        self.supabase: Client = None
        self.stats = {
            'inserted': 0,
            'errors': 0,
            'duplicates': 0
        }
        self.max_inserts = 10  # Maximum number of records to insert

    def open_spider(self, spider):
        """Initialize Supabase connection when spider opens"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")

        if not supabase_url or not supabase_key:
            spider.logger.error(
                "❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE not found in environment variables!"
            )
            spider.logger.error("Please add them to your .env file")
            return

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            spider.logger.info("✅ Connected to Supabase successfully")
        except Exception as e:
            spider.logger.error(f"❌ Failed to connect to Supabase: {e}")
            self.supabase = None

    def generate_claim_token(self, length=32):
        """Generate a unique claim token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def extract_image_url(self, item):
        """Extract image URL from item if available"""
        # Check if there's an image_url field
        if 'image_url' in item:
            return item['image_url']
        
        # Check if there's an images field (list)
        if 'images' in item and item['images']:
            if isinstance(item['images'], list) and len(item['images']) > 0:
                return item['images'][0]
            return item['images']
        
        # Try to extract from description or URL
        # For now, return None - can be enhanced later
        return None

    def extract_seller_email(self, item):
        """Extract seller email from contact_info or other fields"""
        # Check contact_info field
        contact_info = item.get('contact_info', '')
        
        # If contact_info looks like an email
        if '@' in str(contact_info):
            return contact_info
        
        # Check if there's a seller_email field
        if 'seller_email' in item:
            return item['seller_email']
        
        # Check if there's an email field
        if 'email' in item:
            return item['email']
        
        return None

    def process_item(self, item, spider):
        """Process item and insert into Supabase"""
        if not self.supabase:
            spider.logger.warning("Supabase not connected, skipping database insert")
            return item

        adapter = ItemAdapter(item)

        try:
            # Generate unique claim token
            claim_token = self.generate_claim_token()

            # Map fields from item to database schema
            ghost_listing_data = {
                'claim_token': claim_token,
                'title': adapter.get('title', '')[:500] if adapter.get('title') else None,  # Limit title length
                'description': adapter.get('description'),
                'original_price': adapter.get('price'),
                'size': None,  # Not in current JSON structure, can be extracted from description later
                'location': adapter.get('location', ''),
                'original_image_url': self.extract_image_url(adapter),
                'seller_email': self.extract_seller_email(adapter),
                'source_platform': 'gumtree',
                'status': 'pending_claim',
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),  # Expires in 30 days
            }

            # Validate required fields
            if not ghost_listing_data['title']:
                spider.logger.warning(f"Skipping item: missing title")
                self.stats['errors'] += 1
                return item

            if not ghost_listing_data['location']:
                spider.logger.warning(f"Skipping item: missing location")
                self.stats['errors'] += 1
                return item

            # Insert into Supabase
            response = self.supabase.table('ghost_listings').insert(ghost_listing_data).execute()

            if response.data:
                self.stats['inserted'] += 1
                spider.logger.info(
                    f"✅ Inserted ghost listing [{self.stats['inserted']}/{self.max_inserts}]: "
                    f"{ghost_listing_data['title'][:50]}... (Token: {claim_token[:8]}...)"
                )
                
                # Stop spider after reaching max inserts
                if self.stats['inserted'] >= self.max_inserts:
                    spider.logger.info("=" * 60)
                    spider.logger.info(f"🎯 Reached maximum inserts limit ({self.max_inserts})")
                    spider.logger.info("Stopping spider...")
                    spider.logger.info("=" * 60)
                    raise CloseSpider(f'Reached maximum inserts limit: {self.max_inserts}')
            else:
                spider.logger.warning(f"⚠️ No data returned from insert")
                self.stats['errors'] += 1

        except CloseSpider:
            # Re-raise CloseSpider to stop the spider
            raise
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a duplicate token error (shouldn't happen, but just in case)
            if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
                spider.logger.warning(f"⚠️ Duplicate token (retrying): {error_msg}")
                self.stats['duplicates'] += 1
                # Retry with new token
                return self.process_item(item, spider)
            else:
                spider.logger.error(f"❌ Error inserting into Supabase: {error_msg}")
                spider.logger.error(f"   Item: {adapter.get('title', 'Unknown')}")
                self.stats['errors'] += 1

        return item

    def close_spider(self, spider):
        """Log statistics when spider closes"""
        if self.supabase:
            spider.logger.info("=" * 60)
            spider.logger.info("SUPABASE PIPELINE STATISTICS")
            spider.logger.info("=" * 60)
            spider.logger.info(f"✅ Successfully inserted: {self.stats['inserted']}")
            spider.logger.info(f"❌ Errors: {self.stats['errors']}")
            spider.logger.info(f"⚠️ Duplicates (retried): {self.stats['duplicates']}")
            spider.logger.info("=" * 60)
