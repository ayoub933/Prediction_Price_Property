import requests # Récup les pages web
from bs4 import BeautifulSoup # Analyse le HTML
import time

class BaseScraper:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.session = requests.Session()
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.delay = 1
        
    # Récupère le code HTML de la page    
    def get_page(self, url):
        try:
            
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status() # Si erreur HTTP il y'a, exception il y'aura
            html = response.text
            time.sleep(self.delay)
            return html
        
        except Exception as e:
            print(f"Erreur lors du scraping de {url}: {e}")
            return None
        
    # Parse le code html récuperer via la fonction get_page() (ex: <html><head><title>Test</title></head> ----> Test) 
    def parse_html(self, html):
        soup = BeautifulSoup(html, 'lxml')
        return soup
    
    # Combine les fonctions composant la classe BaseScaper pour les faire fonctionner en harmonie
    def scrape(self, url):
        html = self.get_page(url)
        if html is None:
            return None
        
        parser_soup = self.parse_html(html)
        return parser_soup
        
        