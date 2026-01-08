import base64
import json
import re
from datetime import datetime
import traceback
import time
import random
import hashlib

import scrapy

from gumtree_scraper.items import GumtreeListingItem


class GumtreeSpider(scrapy.Spider):
    name = "gumtree"
    allowed_domains = ["gumtree.com"]

    def __init__(self, *args, **kwargs):
        super(GumtreeSpider, self).__init__(*args, **kwargs)
        self.start_urls = [
            "https://www.gumtree.com/flats-houses/garage-parking",
            "https://www.gumtree.com/flats-houses/commercial"
        ]
        self.fetch_descriptions = True
        self.seen_items = set()  # Track seen items by hash

        # Keywords to filter out parking places
        self.parking_keywords = [
            'parking', 'parking space', 'parking spot', 'car park',
            'parking bay', 'park space', 'vehicle space'
        ]

        # Keywords to keep (garages, warehouses, workshops, commercial)
        self.wanted_keywords = [
            'garage', 'warehouse', 'workshop', 'commercial',
            'storage', 'industrial', 'business', 'office'
        ]

    def generate_item_hash(self, item):
        """Generate a hash from key fields to detect duplicates"""
        # Create a string combining key fields
        hash_string = (
            f"{item.get('title', '')}|"
            f"{item.get('description', '')}|"
            f"{item.get('price', '')}|"
            f"{item.get('location', '')}|"
            f"{item.get('contact_info', '')}"
        )
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

    def is_duplicate(self, item):
        """Check if an item is a duplicate"""
        item_hash = self.generate_item_hash(item)
        if item_hash in self.seen_items:
            return True
        self.seen_items.add(item_hash)
        return False

    def is_parking_only(self, item):
        """Check if item is a parking place (to be filtered out)"""
        title_lower = item.get('title', '').lower()
        description_lower = item.get('description', '').lower()
        combined_text = f"{title_lower} {description_lower}"

        # Check if it's ONLY parking (no garage/warehouse/workshop/commercial)
        has_parking = any(keyword in combined_text for keyword in self.parking_keywords)
        has_wanted = any(keyword in combined_text for keyword in self.wanted_keywords)

        # If it has parking keywords but no wanted keywords, filter it out
        if has_parking and not has_wanted:
            self.logger.info(f"Filtering out parking-only listing: {item.get('title')}")
            return True

        return False

    def start_requests(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        for url in self.start_urls:
            yield scrapy.Request(url, headers=headers, callback=self.parse)

    def parse(self, response):
        self.logger.info(f"Parsing listing page: {response.url}")

        if not hasattr(response, "text"):
            self.logger.error(f"Response has no text attribute: {type(response)}")
            return

        if self.settings.getbool("DEBUG_SAVE_HTML", False):
            with open("debug_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            self.logger.info("Saved response HTML to debug_response.html")

        json_match = re.search(
            r"window\.gumtreeDataLayer\s*=\s*\[JSON\.parse\(b64ToUtf8\(\'([^\']+)\'\)\)\]",
            response.text,
        )

        if not json_match:
            self.logger.error("Could not find gumtreeDataLayer JSON data")
            return

        try:
            base64_data = json_match.group(1)
            decoded_json = base64.b64decode(base64_data).decode("utf-8")
            data = json.loads(decoded_json)

            self.logger.info("Successfully extracted JSON data")

            listings = data.get("listListingDetails", [])
            self.logger.info(f"Found {len(listings)} listings in JSON data")

            for listing_data in listings:
                item = self.parse_listing_json(listing_data)
                if item:
                    # Check for duplicates and parking-only listings
                    if self.is_duplicate(item):
                        self.logger.info(f"Skipping duplicate: {item.get('title')}")
                        continue

                    if self.is_parking_only(item):
                        continue

                    if self.fetch_descriptions:
                        # Add random delay (100-1500ms)
                        delay = random.uniform(0.1, 1.5)
                        yield scrapy.Request(
                            item["url"],
                            callback=self.parse_listing,
                            headers=response.request.headers,
                            meta={
                                "item": item,
                                "download_delay": delay
                            },
                            dont_filter=True,
                        )
                    else:
                        yield item

            if len(listings) >= 30:
                next_page_num = (
                    data.get("searchParameters", {}).get("pageNumber", 1) + 1
                )
                if "/page" in response.url:
                    next_url = re.sub(
                        r"/page\d+", f"/page{next_page_num}", response.url
                    )
                else:
                    next_url = f"{response.url}/page{next_page_num}"

                self.logger.info(f"Following next page: {next_url}")
                yield scrapy.Request(
                    next_url, callback=self.parse, headers=response.request.headers
                )

        except Exception as e:
            self.logger.error(f"Error parsing JSON data: {e}")

            self.logger.error(traceback.format_exc())

    def parse_listing_json(self, listing_data):
        try:
            item = GumtreeListingItem()

            item["listing_id"] = str(listing_data.get("id", "N/A"))
            item["title"] = listing_data.get("name", "N/A")
            item["location"] = listing_data.get("location", "N/A")

            price = listing_data.get("price")
            if price is not None:
                item["price"] = f"£{price}"
            else:
                price_pennies = listing_data.get("pricePennies")
                if price_pennies:
                    item["price"] = f"£{price_pennies / 100:.2f}"
                else:
                    item["price"] = "Please contact"

            item["description"] = f"Age: {listing_data.get('age', 'N/A')}"

            listing_id = listing_data.get("id")
            if listing_id:
                title_slug = listing_data.get("name", "").lower().replace(" ", "-")
                title_slug = re.sub(r"[^a-z0-9-]", "", title_slug)[:50]
                item["url"] = f"https://www.gumtree.com/p/-/{title_slug}/{listing_id}"
                item["reply_url"] = f"https://www.gumtree.com/reply/{listing_id}"
            else:
                item["url"] = "N/A"
                item["reply_url"] = "N/A"

            item["scraped_at"] = datetime.now().isoformat()
            return item

        except Exception as e:
            self.logger.error(f"Error parsing listing JSON: {e}")
            return None

    def parse_listing(self, response):
        self.logger.info(f"Fetching description from: {response.url}")

        # Apply the random delay
        delay = response.meta.get("download_delay", 0)
        if delay > 0:
            time.sleep(delay)
            self.logger.debug(f"Applied delay of {delay:.2f}s")

        item = response.meta.get("item")
        if not item:
            self.logger.error("No item in meta, skipping")
            return

        desc = response.css('p[itemprop="description"]::text').getall()
        if not desc:
            json_match = re.search(
                r"window\.gumtreeDataLayer\s*=\s*\[JSON\.parse\(b64ToUtf8\(\'([^\']+)\'\)\)\]",
                response.text,
            )
            if json_match:
                try:
                    base64_data = json_match.group(1)
                    decoded_json = base64.b64decode(base64_data).decode("utf-8")
                    data = json.loads(decoded_json)
                    desc = [data.get("description", "")]
                except Exception as _:
                    pass

        if desc:
            description = " ".join([d.strip() for d in desc if d and d.strip()])
            if description:
                item["description"] = description
            else:
                self.logger.warning(f"Empty description for {response.url}")
        else:
            self.logger.warning(f"Could not find description for {response.url}")

        contact_info = response.css("h2.seller-rating-block-name::text").getall()
        if contact_info:
            print("ITEM", item)
            print(
                "CONTACT INFO",
                contact_info,
            )
            contact_info = " ".join(
                [d.strip() for d in contact_info if d and d.strip()]
            )

            item["contact_info"] = contact_info
        else:
            self.logger.warning(
                f"Could not find contact info for {response.url}. CSS SELECTORS HAVE PROBABLY CHANGED"
            )

        price = response.css('h3[data-q="ad-price"]::text').getall()

        if price:
            # no special formatting applied so price is likely in a format such as £2300pm etc
            item["price"] = " ".join([d.strip() for d in price if d and d.strip()])
        else:
            self.logger.warning(
                f"Could not find price info for {response.url}. CSS SELECTORS HAVE PROBABLY CHANGED"
            )

        # Check again for duplicates after getting full description and contact info
        if self.is_duplicate(item):
            self.logger.info(f"Skipping duplicate after full fetch: {item.get('title')}")
            return

        # Check again for parking-only after getting full description
        if self.is_parking_only(item):
            return

        yield item
