from scrapers.craiglist import CraigslistParisScraper

if __name__ == "__main__":
    # Créer le scraper
    scraper = CraigslistParisScraper()

    # Lancer le scraping avec des critères
    annonces = scraper.scrape_craigslist(
        search_term="studio",   # mot-clé
        min_price=500,          # prix minimum
        max_price=1500          # prix maximum
    )

    # Afficher les résultats
    print(f"\n{len(annonces)} annonces trouvées :\n")
    for a in annonces:
        print(f"{a['titre']} - {a['prix']} - {a['adresse']} - {a['url']}")
