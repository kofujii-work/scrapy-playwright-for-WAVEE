import scrapy
import psycopg2  # PostgreSQL データベースに接続するためのライブラリ
from scrapy_playwright.page import PageMethod
from company_scraper.items import CompanyTextItem
from urllib.parse import urljoin, urlparse
from datetime import datetime


class CompanySpider(scrapy.Spider):
    name = "company_spider"

    # データベース接続情報
    DB_HOST = "localhost"
    DB_NAME = "company_db"
    DB_USER = "postgres"
    DB_PASSWORD = "Kou314F15926"

    def __init__(self, *args, **kwargs):
        super(CompanySpider, self).__init__(*args, **kwargs)
        self.company_urls = []
        self.allowed_domains = []

    def start_requests(self):
        # データベースに接続
        conn = psycopg2.connect(
            host=self.DB_HOST,
            database=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD
        )

        cur = conn.cursor()
        # データベースから企業の URL とドメインを取得
        cur.execute("SELECT company_id, name, url FROM company_URLs;")
        companies = cur.fetchall()

        # データベースから取得したURLと企業名に基づいてリクエストを送信
        for company in companies:
            company_id, company_name, url = company
            domain = urlparse(url).netloc
            self.company_urls.append(url)
            self.allowed_domains.append(domain)

            # 各URLに対してリクエストを送信し、company_id と company_name を渡す
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
                    "company_id": company_id,  # company_id を渡す
                    "company_name": company_name,  # company_name を渡す
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

        # アイテムの生成: URL, 抽出されたテキスト、HTML全体、company_id, company_name, scrape_time を保存
        item = CompanyTextItem()
        item['url'] = response.url
        item['text'] = full_text
        item['html'] = response.text  # HTML全体を保存（ログには表示しない）
        item['company_id'] = response.meta['company_id']
        item['name'] = response.meta['company_name']  # company_name をアイテムに追加
        item['scrape_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在時刻をscrape_timeとして保存

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
                        "company_id": response.meta['company_id'],  # 次のリクエストにも company_id を渡す
                        "company_name": response.meta['company_name'],  # 次のリクエストにも company_name を渡す
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
