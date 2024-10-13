# items.py

# company_scraper/items.py

import scrapy

class CompanyTextItem(scrapy.Item):
    url = scrapy.Field()   # スクレイピング対象のページのURL
    text = scrapy.Field()  # ページから抽出されたテキストデータ
    html = scrapy.Field()  # ページ全体のHTMLコンテンツ
