import psycopg2
import logging
from scrapy.exceptions import DropItem
from scrapy import Item

class PostgresPipeline:
    def __init__(self, postgres_config):
        self.postgres_config = postgres_config

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            postgres_config=crawler.settings.get('POSTGRESQL')  # Scrapy設定からDB設定を取得
        )

    def open_spider(self, spider):
        try:
            self.connection = psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                dbname=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password']
            )
            self.cursor = self.connection.cursor()
            logging.info("PostgreSQLに接続しました。")

            # テーブルが存在しない場合は作成する
            create_table_query = """
                CREATE TABLE IF NOT EXISTS scraped_homepage (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    text TEXT NOT NULL,
                    html TEXT NOT NULL,
                    scrape_time TIMESTAMP
                );
            """
            self.cursor.execute(create_table_query)
            self.connection.commit()
            logging.info("scraped_homepage テーブルを確認しました。")
        except Exception as e:
            logging.error(f"PostgreSQLへの接続に失敗しました: {e}")
            raise e

    def close_spider(self, spider):
        self.cursor.close()
        self.connection.close()
        logging.info("PostgreSQLの接続を閉じました。")

    def process_item(self, item, spider):
        try:
            self.cursor.execute("""
                INSERT INTO scraped_homepage (company_id, name, url, text, html, scrape_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (item['company_id'], item['name'], item['url'], item['text'], item['html'], item['scrape_time']))
            self.connection.commit()
            return item
        except Exception as e:
            logging.error(f"アイテムの保存中にエラーが発生しました: {e}")
            self.connection.rollback()
            raise DropItem(f"保存エラー: {e}")
