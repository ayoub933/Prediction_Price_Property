from scrapers.base import BaseScraper
from database.models import save_property
from data_processing.price_extractor import extract_price

class CraigslistParisScraper(BaseScraper):
    cities = [
        "london.craigslist.org",
        "berlin.craigslist.org",
        "madrid.craigslist.org",
        "milano.craigslist.org",
        "amsterdam.craigslist.org",
        "newyork.craigslist.org",
        "losangeles.craigslist.org",
        "chicago.craigslist.org",
        "miami.craigslist.org",
        "toronto.craigslist.org",
        "tokyo.craigslist.org",
        "hongkong.craigslist.org",
        "manila.craigslist.org",
        "bangkok.craigslist.org",
        "delhi.craigslist.org"
    ]

    def __init__(self, city_index=0):
        city_host = self.cities[city_index]
        super().__init__(
            name=f"craigslist_{city_host.split('.')[0]}",
            url=f"https://{city_host}"
        )

    
    # On construit l'URL de recherche pour craigslist (ex : https://paris.craigslist.org/search/apa?isTrusted=true&is_furnished=1&max_price=2000&min_price=500#search=2~gallery~0)
    def build_search_url(self, search_term="", min_price=None, max_price=None):
        base_url = f"{self.url}/search/apa"
        params = []
        
        if search_term:
            search_encoded = search_term.replace(" ", "+")
            params.append(f"query={search_encoded}")
        if min_price:
            params.append(f"min_price={min_price}")
        if max_price:
            params.append(f"max_price={max_price}")
        
        if params:
            return f"{base_url}?{'&'.join(params)}"
        else:
            return base_url
    
    # Extraction des données
    def extract_property_data(self, soup):
        annonces = []
        for item in soup.select("li.cl-static-search-result"):
            titre_tag = item.select_one(".title")
            titre = titre_tag.get_text(strip=True) if titre_tag else None

            lien_tag = item.select_one("a")
            lien = lien_tag["href"] if lien_tag else None

            prix_tag = item.select_one(".price")
            prix = prix_tag.get_text(strip=True) if prix_tag else None

            loc_tag = item.select_one(".location")
            location = loc_tag.get_text(strip=True) if loc_tag else None

            annonces.append({
                "titre": titre,
                "prix": prix,
                "adresse": location,
                "url": lien
            })
        return annonces
            
    def scrape_craigslist(self, search_term="", min_price=None, max_price=None):
            url = self.build_search_url(search_term, min_price, max_price)
            soup = self.scrape(url)

            if soup is None:
                print("Erreur lors du scraping")
                return []

            properties = self.extract_property_data(soup)
            for prop in properties:
                prop["prix"] = extract_price(prop["prix"]) # €1 100 ----> 1100
            
            saved_count = 0
            for prop in properties:
                try:
                    save_property(
                        title=prop["titre"],
                        price=prop["prix"],
                        address=prop["adresse"],
                        surface=None,
                        rooms=None,
                        property_type="appartement",
                        latitude=None,
                        longitude=None,
                        description=None,
                        features=[],
                        source="craigslist_paris",
                        url=prop["url"],
                        scraped_at="2025-08-09"
                    )
                    saved_count += 1
                except Exception as e:
                    print(f"Erreur sauvegarde : {e}")
            
            print(f"{saved_count}/{len(properties)} annonces sauvegardées")
            return properties
