# company_scraper/spiders/company_spider.py

import scrapy
from scrapy_playwright.page import PageMethod
from company_scraper.items import CompanyTextItem  # アイテムをインポート
from urllib.parse import urljoin, urlparse

class CompanySpider(scrapy.Spider):
    name = "company_spider"
    
    start_urls = [
        'https://eggforward.co.jp/',
        # 他の企業のURLを追加
    ]

    allowed_domains = [
        'eggforward.co.jp',
        # 他の企業のドメインを追加
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "a[href]"),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 20000),
                    ],
                    "errback": self.errback,
                    # "dont_filter": True  # 必要に応じて
                }
            )

    async def parse(self, response):
        # ページURLのログ出力（デバッグ用）
        self.logger.debug(f"スクレイピング中のURL: {response.url}")

        # スクリプトやスタイルタグを除外せず、HTML全体を取得
        html_content = response.text
        
        # スクリプトやスタイルタグを除外したテキストを取得
        page_text = response.xpath("//body//text()[normalize-space()]").getall()

        # 不要な空白や改行を削除
        page_text = [text.strip() for text in page_text if text.strip()]
        
        # テキストを一つの文字列に結合
        full_text = ' '.join(page_text)

        # アイテムの生成: URL, 抽出されたテキスト、HTML全体を保存
        item = CompanyTextItem()
        item['url'] = response.url
        item['text'] = full_text
        item['html'] = html_content  # HTML全体を保存

        yield item

        # ページ内のすべてのリンクを抽出
        links = response.xpath('//a[@href]/@href').getall()
        self.logger.debug(f"抽出されたリンク数: {len(links)}")

        for link in links:
            # 絶対URLを構築
            absolute_url = urljoin(response.url, link)

            # URLを解析してホストを取得
            parsed_url = urlparse(absolute_url)
            host = parsed_url.netloc.lower()

            # allowed_domains の全てをチェック
            if any(host == domain.lower() or host.endswith('.' + domain.lower()) for domain in self.allowed_domains):
                yield scrapy.Request(
                    url=absolute_url,
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "body"),
                            PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                            PageMethod("wait_for_timeout", 1000),
                        ],
                        "errback": self.errback,
                        # "dont_filter": True  # 必要に応じて
                    }
                )

    async def errback(self, failure):
        # エラーハンドリング
        self.logger.error(f"リクエスト失敗: {repr(failure)}")
