import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time

class BaseScraper:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.session = requests.Session()
        # Retries réseau (évite de pendre 10s × N)
        retry = Retry(total=5, connect=5, read=5, backoff_factor=0.8,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=frozenset(["GET"]))
        adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.delay = 0.3

    def get_page(self, url):
        try:
            resp = self.session.get(url, headers=self.headers, timeout=(5, 20))  # (connect, read)
            resp.raise_for_status()
            html = resp.text
            time.sleep(self.delay)
            return html
        except Exception as e:
            print(f"error{url} -> {e}", flush=True)
            return None
        
    # Si XML (sitemap), parse en XML, sinon HTML
    def parse_html(self, html):
        text = html.lstrip()
        if text.startswith("<?xml") or text.startswith("<urlset") or text.startswith("<sitemapindex"):
            return BeautifulSoup(html, "xml")
        return BeautifulSoup(html, "lxml")

    def scrape(self, url):
        html = self.get_page(url)
        if html is None:
            return None
        return self.parse_html(html)
