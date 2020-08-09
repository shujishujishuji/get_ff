import scrapy
import os
import urllib
from researcher.items import SaledItem


class SaledSpider(scrapy.Spider):
    name = 'saled'
    allowed_domains = ['buyma.com']
    # start_urls = [
    #     'https://www.buyma.com/buyer/8156968/sales_1.html',
    # ]

    myBaseUrl = ''
    start_urls = []

    def __init__(self, category='', **kwargs):
        # The category variable will have the input URL.
        self.myBaseUrl = category
        self.start_urls.append(self.myBaseUrl)
        super().__init__(**kwargs)

    def parse(self, response):
        item = SaledItem()
        for card in response.css('div.buyeritemtable_body'):
            img = card.css('li.buyeritemtable_img img::attr(src)').get()
            img_file = img.split('/')[-2] + '.jpg'
            item['img'] = img
            item['img_file'] = img_file
            item['title'] = card.css('li.buyeritemtable_info p.buyeritem_name a::text').get()
            item['item_url'] = 'https://www.buyma.com' + card.css('li.buyeritemtable_info p.buyeritem_name a::attr(href)').get()
            item['dates'] = card.css('li.buyeritemtable_info').xpath('p[3]/text()').get()
            yield item
            x_path = None
        for ind, x in enumerate(response.css('div.paging > a::text').getall()):
            if '次' in x:
                x_path = f'//*[@id="buyeritemtable_wrap"]/div[2]/div/a[{ind + 1}]'
        yield from response.follow_all(xpath=x_path, callback=self.parse)
