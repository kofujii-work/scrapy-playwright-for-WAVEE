# items.py

# company_scraper/items.py

import scrapy

class CompanyTextItem(scrapy.Item):
    url = scrapy.Field()   # スクレイピング対象のページのURL
    text = scrapy.Field()  # ページから抽出されたテキストデータ
    html = scrapy.Field()  # ページ全体のHTMLコンテンツ
    company_id = scrapy.Field()  # 会社識別ID
    name = scrapy.Field() # 会社名
    scrape_time = scrapy.Field() # データ取得時間
    