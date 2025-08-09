from scrapers.craiglist import CraigslistParisScraper
import time

if __name__ == "__main__":
    all_annonces = []

    for i, city_host in enumerate(CraigslistParisScraper.cities):
        print(f"\n--- Scraping {city_host} ---")
        
        scraper = CraigslistParisScraper(city_index=i)
        annonces = scraper.scrape_craigslist(
            search_term="studio",
            min_price=300,
            max_price=2500
        )
        
        print(f"{len(annonces)} annonces trouvées pour {city_host}")
        
        for a in annonces:
            print(f"{a['titre']} - {a['prix']} - {a['adresse']} - {a['url']}")
        time.sleep(2)
        all_annonces.extend(annonces)

    print(f"\nTOTAL\n{len(all_annonces)} annonces trouvées sur toutes les villes.")
