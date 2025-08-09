from scrapers.craiglist import CraigslistParisScraper

if __name__ == "__main__":
    scraper = CraigslistParisScraper()
    annonces = scraper.scrape_craigslist(
        search_term="studio",
        min_price=500,
        max_price=1500
    )
    
    print(f"\n{len(annonces)} annonces trouvées :\n")
    for a in annonces:
        print(f"{a['titre']} - {a['prix']} - {a['adresse']} - {a['url']}")
