import scrapy
import os
import urllib
from researcher.items import ResearcherItem

"""使い方
cd get_ff/researcher
scrapy crawl [spider] -a url='xxx@xx.com'
"""


class BlandSpider(scrapy.Spider):
    name = "bland"
    allowed_domains = ['buyma.com']
    # start_urls = [
    #     'https://www.buyma.com/r/_Vertbaudet-%E3%83%B4%E3%82%A7%E3%83%AB%E3%83%9C%E3%83%87/',
    # ]

    # def start_requests(self):
    #     url = getattr(self, 'url', None)
    #     yield scrapy.Request(url, self.parse)

    myBaseUrl = ''
    start_urls = []

    def __init__(self, category='', **kwargs):
        # The category variable will have the input URL.
        self.myBaseUrl = category
        self.start_urls.append(self.myBaseUrl)
        super().__init__(**kwargs)

    def parse(self, response):
        item = ResearcherItem()
        for card in response.css('ul.clearfix li.product'):
            img = card.css('div.product_img img::attr(src)').get()
            img_file = img.split('/')[-2] + '.jpg'

            item['img'] = img
            item['img_file'] = img_file
            item['title'] = card.css('div.product_body div.product_name a::text').get()
            item['price'] = card.css('div.product_body div.product_price').xpath('span[@class="Price_Txt"]/text()').get()
            if card.css('div.product_body div.fab-design-of--h a'):
                item['shopper_status'] = ''.join(card.css('div.product_body div.fab-design-of--h a').xpath('span/text()').getall())
            else:
                item['shopper_status'] = ''.join(card.css('div.product_body div.fab-design-of--h').xpath('span/text()').get())
            item['shopper_name'] = card.css('div.product_body div.product_Buyer a::text').get()
            item['shopper_url'] = self.allowed_domains[0] + card.css('div.product_body div.product_Buyer a::attr(href)').get()
            item['category'] = response.xpath('//*[@id="n_search_CurrentCondWrap"]/h1/span/text()').get()
            yield item
        yield from response.follow_all(css='div.paging > a', callback=self.parse)