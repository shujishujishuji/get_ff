# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ResearcherItem(scrapy.Item):
    img = scrapy.Field()
    img_file = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    shopper_status = scrapy.Field()
    shopper_name = scrapy.Field()
    shopper_url = scrapy.Field()
    category = scrapy.Field()

