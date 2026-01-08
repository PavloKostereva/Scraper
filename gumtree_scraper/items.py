# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GumtreeListingItem(scrapy.Item):
    """Item for storing Gumtree listing data"""

    title = scrapy.Field()
    description = scrapy.Field()
    price = scrapy.Field()
    location = scrapy.Field()
    url = scrapy.Field()
    reply_url = scrapy.Field()
    listing_id = scrapy.Field()
    contact_info = scrapy.Field()
    scraped_at = scrapy.Field()
