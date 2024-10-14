import scrapy
from scrapy_playwright.page import PageMethod
from company_scraper.items import CompanyTextItem
from urllib.parse import urljoin, urlparse


class CompanySpider(scrapy.Spider):
    name = "company_spider"
    
    # 処理する企業のリスト
    company_urls = [
        'https://eggforward.co.jp/',
        'https://starup01.jp/',
        # 他の企業のURLを追加
    ]
    
    # 許可されたドメインのリスト
    allowed_domains = [
        'eggforward.co.jp',
        'starup01.jp',
        # 他の企業のドメインを追加
    ]

    def __init__(self, *args, **kwargs):
        super(CompanySpider, self).__init__(*args, **kwargs)
        self.company_index = 0  # 現在処理中の企業のインデックス

    def start_requests(self):
        if self.company_index < len(self.company_urls):
            url = self.company_urls[self.company_index]
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "a[href]"),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 20000),
                    ],
                    "errback": self.errback,
                }
            )

    async def parse(self, response):
        # ページURLのログ出力（デバッグ用）
        self.logger.debug(f"スクレイピング中のURL: {response.url}")

        # スクリプトやスタイルタグを除外したテキストを取得
        page_text = response.xpath(
            "//body//text()[not(ancestor::script) and not(ancestor::style) and not(ancestor::noscript) and not(ancestor::template) and not(ancestor::comment())]"
        ).getall()

        # 不要な空白や改行を削除
        page_text = [text.strip() for text in page_text if text.strip()]

        # テキストを一つの文字列に結合
        full_text = ' '.join(page_text)

        # アイテムの生成: URL, 抽出されたテキスト、HTML全体を保存
        item = CompanyTextItem()
        item['url'] = response.url
        item['text'] = full_text
        item['html'] = response.text  # HTML全体を保存

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
                            PageMethod("wait_for_timeout", 20000),
                        ],
                        "errback": self.errback,
                    }
                )

        # 次の企業を処理
        self.company_index += 1
        if self.company_index < len(self.company_urls):
            next_url = self.company_urls[self.company_index]
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "body"),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 20000),
                    ],
                    "errback": self.errback,
                }
            )

    async def errback(self, failure):
        # エラーハンドリング
        self.logger.error(f"リクエスト失敗: {repr(failure)}")
        
        # 次の企業を処理（エラーが発生しても次の企業へ）
        self.company_index += 1
        if self.company_index < len(self.company_urls):
            next_url = self.company_urls[self.company_index]
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "body"),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 20000),
                    ],
                    "errback": self.errback,
                }
            )
