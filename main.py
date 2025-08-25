from scrapers.c21 import C21Scraper

if __name__ == "__main__":
    scraper = C21Scraper()
    result = scraper.scrape_c21(limit=300000, workers=24)
    if isinstance(result, int):
        print(f"\nAnnonces sauvegardées : {result}\n")
    else:
        annonces = result
        print(f"\n{len(annonces)} annonces récupérées :\n")
        for a in annonces[:5]:
            print(f"- {a.get('titre')} | {a.get('prix')} | {a.get('rooms')} br | {a.get('surface')} | {a.get('url')}")
