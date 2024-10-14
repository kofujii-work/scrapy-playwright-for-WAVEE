import scrapy
import psycopg2  # PostgreSQL データベースに接続するためのライブラリ
from scrapy_playwright.page import PageMethod
from company_scraper.items import CompanyTextItem
from urllib.parse import urljoin, urlparse
from datetime import datetime

class CompanySpider(scrapy.Spider):
    name = "company_spider"

    # データベース接続情報
    DB_HOST = "localhost"  # ホスト名
    DB_NAME = "company_db"  # データベース名
    DB_USER = "postgres"  # ユーザー名
    DB_PASSWORD = "Kou314F15926"  # パスワード

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

            # クローリングリクエストの送信
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "company_id": company_id,
                    "company_name": company_name,
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
        
        # データベース接続を閉じる
        cur.close()
        conn.close()

    async def parse(self, response):
        company_id = response.meta.get("company_id")
        company_name = response.meta.get("company_name")

        # データ取得日時
        scrape_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

        # アイテムの生成: URL, 抽出されたテキスト、HTML全体、データ取得日時を保存
        item = CompanyTextItem()
        item['company_id'] = company_id
        item['name'] = company_name
        item['url'] = response.url
        item['text'] = full_text
        item['html'] = response.text  # HTML全体を保存
        item['scrape_time'] = scrape_time  # データ取得日時

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

        # 動的にURLから取得したドメインに対してのみクローリングする
        if host == urlparse(response.url).netloc:
            yield scrapy.Request(
                url=absolute_url,
                callback=self.parse,
                meta={
                    "company_id": company_id,
                    "company_name": company_name,
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
