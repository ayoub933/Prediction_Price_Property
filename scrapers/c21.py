import json
import re
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from database.models import save_property
from data_processing.price_extractor import extract_price
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, random
from database.connection import get_connection


SQFT_TO_M2 = 0.09290304  # 1 sqft = 0.09290304 m2
ACRE_TO_M2 = 4046.8564224  # 1 acre = 4046.8564224 m2

# On convertit proprement en float les nombres pour l'intégrer dans la db (ex: _safe_float(1,602) -> 1602.0 | 0-700 -> 700 | 1200+ -> 1200 etc)
def _safe_float(x):
    if x is None:
        return None

    # on force en float pour la bd
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except:
            return None

    # dictionnaire -> on prend d'abord max/value puis min (ex: _safe_float({"min": 30, "max": 45}) -> 45.0)
    if isinstance(x, dict):
        for k in ("max", "maxValue", "value", "min", "minValue"):
            if k in x and x[k] is not None:
                try:
                    return float(x[k])
                except:
                    pass
        return None

    # on converti chaque élement recursivement puis on garde le max (utile pour les valeurs comme '900-1200sqft', assez floue pour l'algorithme)
    if isinstance(x, (list, tuple)):
        vals = [ _safe_float(v) for v in x ]
        vals = [ v for v in vals if v is not None ]
        return max(vals) if vals else None

    # chaîne (Canada/US: , milliers / . décimale)
    s = str(x).strip().replace("\xa0", " ") # remplace les espaces insécables
    if not s: # si vide
        return None

    # capture nombres style '1,234.56' ou '5,000' ou '700'
    tokens = re.findall(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?', s)
    if not tokens:
        return None

    vals = []
    for t in tokens:
        try:
            vals.append(float(t.replace(",", "")))  # enlève séparateurs de milliers
        except:
            continue

    return max(vals) if vals else None

# Fonction pour structurer la sous-chaîne JSON par comptage d'accolade
# ex : s = '<script>var DATA = { "user": "BOB", "age": 27, "address": {"city": "Paris", "zip": "75000"} };</script>'
def _extract_json_object(s, start_idx):
    i = s.find("{", start_idx)            # 1) trouver la première '{' à partir de start_idx
    if i == -1:
        return None

    depth = 0                             # profondeur d’imbrication des accolades
    in_string = False                     # sommes-nous à l’intérieur d’une chaîne JSON ("...") ?
    escape = False                        # le caractère précédent était-il un backslash \ ?

    for j, ch in enumerate(s[i:], start=i): # on lit à partir du caractère ou l'accolade commence (i=16 par exempleà
        if in_string:
            # 2) Si on est DANS une chaîne, on ignore les { } rencontrées
            if escape:                    # le char précédent était un \
                escape = False            # on consomme l’échappement
            elif ch == "\\":              # on vient de voir un \ -> prochain char est échappé
                escape = True
            elif ch == '"':               # guillemet non échappé -> fin de chaîne
                in_string = False
            continue

        # 3) Hors chaîne : on gère l’état normal
        if ch == '"':
            in_string = True              # entrée dans une chaîne
        elif ch == "{":
            depth += 1                    # nouvelle accolade ouvrante -> +1
        elif ch == "}":
            depth -= 1                    # accolade fermante -> -1
            if depth == 0:                # revenu au niveau 0 -> objet complet trouvé
                return s[i:j+1]
    return None                           # fin de texte sans refermer correctement -> échec


# Cette fonction sert à savoir si la maison est en vente ou si c'est uniquement pour la louer
def infer_listing_type(title=None, description=None, url=None, price=None):
    # Prix
    try:
        p = float(price) if price is not None else None
    except Exception:
        p = None
    if p is not None:
        if p < 10000:     # loyers typiques
            return "rent"
        if p >= 100000:   # ventes typiques
            return "sale"

    # Mots-clés / URL
    text = f"{title or ''} {description or ''}".lower()
    u = (url or "").lower()
    if (" for rent" in text or " rent " in text or "rental" in text or " lease" in text
        or " per month" in text or "/mo" in text or "/rent" in u or "/lease" in u):
        return "rent"
    return "sale"


class C21Scraper(BaseScraper):
    def __init__(self):
        super().__init__(name="c21", url="https://www.c21.ca")
        self.delay = 0.8

    # Récupère une page XML et la parse en XML
    def _get_xml_soup(self, url):
        html = self.get_page(url)
        if not html:
            return None
        return BeautifulSoup(html, "xml")

    # On parcourt cet adresse (https://www.c21.ca/sitemap.xml) à la recherche d'annonce intéressante pour renvoyer une liste d'URL d'annonce
    def iter_listing_urls_from_sitemap(self, limit=50):
        urls, seen = [], set()

        index_url = f"{self.url}/sitemap.xml"
        index_soup = self._get_xml_soup(index_url)
        if not index_soup:
            return urls

        listing_sitemaps = []
        for loc_tag in index_soup.find_all("loc"):
            loc = loc_tag.get_text(strip=True)
            if re.search(r"sitemap.*listings.*\.xml$", loc, re.I): # On filtre les sitemaps (listing contiennent toutes les annonces)
                listing_sitemaps.append(loc)

        if not listing_sitemaps:
            return urls

        listing_sitemaps.sort()  # du plus ancien au plus récent

        for sm_url in listing_sitemaps:
            print(f"[SITEMAP] {sm_url}", flush=True)
            sm_soup = self._get_xml_soup(sm_url)
            if not sm_soup:
                continue

            for loc_tag in sm_soup.find_all("loc"):
                page_url = loc_tag.get_text(strip=True)
                if "/listing/" not in page_url:
                    continue
                if page_url in seen:
                    continue
                seen.add(page_url)
                urls.append(page_url)
                if len(urls) >= limit:
                    print(f"[SITEMAP] {len(urls)} URLs trouvées (limite atteinte)", flush=True)
                    return urls

        print(f"[SITEMAP] {len(urls)} URLs trouvées", flush=True)
        return urls # Une liste d'URL d'annonce trouvée correspondant aux filtres appliqués

    # On cherche le script 'var Wx = {...}' qui contient tout les détails de l'annonce (prix,descriptions,titre,adresse etc)
    def parse_listing_wx(self, soup):
        try:
            # 1) Trouver le script qui contient Wx et listing_detail
            script_text = None
            for tag in soup.find_all("script"):
                t = tag.get_text(strip=False) or ""
                if "var Wx" in t and "listing_detail" in t:
                    script_text = t
                    break
            if not script_text:
                return {}

            # 2) Localiser "listing_detail" puis l'objet JSON qui suit
            key_idx = script_text.find("listing_detail")
            if key_idx == -1:
                return {}

            colon_idx = script_text.find(":", key_idx)
            if colon_idx == -1:
                return {}

            listing_json = _extract_json_object(script_text, colon_idx + 1)
            if not listing_json:
                return {}

            # 3) Tenter le parse JSON ; plan B: retirer les virgules finales de tableaux/objets
            try:
                obj = json.loads(listing_json)
            except json.JSONDecodeError:
                cleaned = re.sub(r",\s*([}\]])", r"\1", listing_json)  # supprime trailing commas
                obj = json.loads(cleaned)

            # 4) Mapping vers notre schéma
            data = {}

            # Adresse / lat-lon
            loc = obj.get("location") or {}
            addr_parts = [
                loc.get("address"),
                loc.get("city"),
                loc.get("state"),
                loc.get("zip"),
                loc.get("country_code"),
            ]
            adresse = ", ".join([p for p in addr_parts if p])

            lat = _safe_float(loc.get("latitude"))
            lon = _safe_float(loc.get("longitude"))

            # Features aplaties
            features_list = []
            for feat in obj.get("features", []) or []:
                fname = (feat.get("feature_name") or "").strip()
                for sub in (feat.get("subfeatures") or []):
                    sname = (sub.get("subfeature_name") or "").strip()
                    if fname and sname:
                        features_list.append(f"{fname}:{sname}".lower().replace(" ", "_"))
                    elif sname:
                        features_list.append(sname.lower().replace(" ", "_"))

            titre = adresse or obj.get("title") or "Listing"
            rooms = obj.get("bedrooms")
            try:
                rooms = int(rooms) if rooms is not None else None
            except Exception:
                rooms = None

           # surface: tenter valeurs directes (souvent en SQFT)
            surface = obj.get("living_area") or obj.get("sqr_footage")
            surface = _safe_float(surface)

            # si on a une valeur numérique plausible en SQFT, convertir en m²
            if surface is not None and surface > 0:
                # Heuristique: la plupart des surfaces habitables < 20 000 sqft
                if surface < 20000:
                    surface = surface * SQFT_TO_M2

            # fallback: display_sqft (ex. "0 - 700", "< 700", "5000+")
            if surface is None:
                disp = (obj.get("display_sqft")
                        or obj.get("display_square_feet")
                        or obj.get("display_square_footage"))
                sqft = _safe_float(disp)
                if sqft is not None:
                    surface = sqft * SQFT_TO_M2

            # fallback final: acreage (acres -> m²)
            acreage = _safe_float(obj.get("acreage"))
            if (surface is None or surface == 0) and acreage is not None:
                surface = acreage * ACRE_TO_M2

            price = obj.get("price") or obj.get("list_price")
            price = _safe_float(price)

            description = obj.get("comments")

            # Typologie
            ptype_src = (obj.get("property_type") or obj.get("title") or "")
            ptype = "appartement"
            if isinstance(ptype_src, str):
                pt = ptype_src.lower()
                if any(k in pt for k in ["single", "residential", "bungalow", "house"]):
                    ptype = "maison"
                elif any(k in pt for k in ["condo", "apartment", "apartment/condo"]):
                    ptype = "appartement"

            data.update(
                {
                    "titre": titre,
                    "prix": price,
                    "adresse": adresse if adresse else None,
                    "surface": surface,
                    "rooms": rooms,
                    "latitude": lat,
                    "longitude": lon,
                    "description": description,
                    "features": features_list,
                    "property_type": ptype,
                }
            )
            return data

        except Exception as e:
            # pour ne pas faire planter le programme en cas d'échec
            print(f"[WX][parse][ERR] {e}", flush=True)
            return {}


    # Lit les script comme ça : <script type="application/ld+json"> pour compléter la recherche d'info sur les annonces comme la description, les nombre de chambre etc
    # Complémentaire à celle d'au dessus
    def parse_listing_jsonld(self, soup):
        data = {}
        for tag in soup.find_all("script", type="application/ld+json"):
            raw = tag.get_text(strip=True)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue

            objs = payload if isinstance(payload, list) else [payload]
            for obj in objs:
                t = obj.get("@type", "")
                if isinstance(t, list):
                    t = ",".join(t).lower()
                else:
                    t = str(t).lower()

                if any(
                    k in t
                    for k in ["product", "offer", "realestate", "apartment", "house", "singlefamily"]
                ):
                    # titre
                    if not data.get("titre"):
                        data["titre"] = obj.get("name") or obj.get("title")

                    # url canonique
                    if not data.get("url"):
                        data["url"] = obj.get("url")

                    # prix
                    offers = obj.get("offers")
                    if isinstance(offers, dict) and data.get("prix") is None:
                        price = offers.get("price")
                        if price is not None:
                            data["prix"] = extract_price(str(price))

                    # adresse
                    addr = obj.get("address")
                    if isinstance(addr, dict) and data.get("adresse") is None:
                        parts = [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),
                            addr.get("addressCountry"),
                        ]
                        data["adresse"] = ", ".join([p for p in parts if p])

                    # chambres
                    if data.get("rooms") is None:
                        br = obj.get("numberOfBedrooms") or obj.get("numberOfRooms")
                        if isinstance(br, (int, float)):
                            data["rooms"] = int(br)
                        elif isinstance(br, str) and re.search(r"\d", br):
                            data["rooms"] = int(re.sub(r"\D", "", br))

                    # surface
                    if data.get("surface") is None:
                        size = obj.get("floorSize") or obj.get("area")
                        if isinstance(size, dict):
                            val = size.get("value")
                            data["surface"] = _safe_float(val)

                    # coordonnées GPS
                    if data.get("latitude") is None:
                        lat = obj.get("latitude")
                        if lat is None and isinstance(obj.get("geo"), dict):
                            lat = obj["geo"].get("latitude")
                        data["latitude"] = _safe_float(lat)

                    if data.get("longitude") is None:
                        lon = obj.get("longitude")
                        if lon is None and isinstance(obj.get("geo"), dict):
                            lon = obj["geo"].get("longitude")
                        data["longitude"] = _safe_float(lon)

                    # description
                    if data.get("description") is None and isinstance(
                        obj.get("description"), str
                    ):
                        desc = obj["description"].strip()
                        data["description"] = desc if desc else None

        return data

    # But de cette fonction est identique aux deux au dessus, seulement ici on s'occupe de parser l'HTML/CSS si les deux fonctions précedentes ne fonctionnent pas/ne donnent pas satisfaction
    def parse_listing_css(self, soup):
        data = {}

        # titre
        h1 = soup.find("h1")
        if h1 and not data.get("titre"):
            data["titre"] = h1.get_text(strip=True)

        # prix
        price_node = soup.select_one(".price span, .price-value, [class*='price'] span")
        if price_node and not data.get("prix"):
            data["prix"] = extract_price(price_node.get_text(strip=True))

        # adresse
        addr_node = soup.select_one("[class*='address'], .address-block, .listing-address")
        if addr_node and not data.get("adresse"):
            data["adresse"] = addr_node.get_text(" ", strip=True)

        # labels utilitaires
        def _info_value(label_regex):
            lbl = soup.find("span", string=re.compile(label_regex, re.I))
            if lbl and lbl.parent:
                val = lbl.parent.find("span", class_=re.compile("listing-info-item-value"))
                if val:
                    return val.get_text(strip=True)
            return None

        if data.get("rooms") is None:
            br = _info_value(r"^BED(S)?|BEDROOMS?$")
            data["rooms"] = int(re.sub(r"\D", "", br)) if br and re.search(r"\d", br) else None

        if data.get("surface") is None:
            sqft_text = _info_value(r"SQFT|AREA|SIZE")
            sqft_val = _safe_float(sqft_text)
            if sqft_val is not None:
                data["surface"] = sqft_val * SQFT_TO_M2


            
        if data.get("surface") is None:
            lot_txt = _info_value(r"LOT\s*SIZE|ACREAGE|LOT\s*AREA")
            if lot_txt and re.search(r"acre", lot_txt, re.I):
                val = _safe_float(lot_txt)
                if val is not None:
                    data["surface"] = val * ACRE_TO_M2

        # description
        desc_node = soup.select_one(".description, [class*='description'], .remarks, .listing-description")
        if desc_node and not data.get("description"):
            text = desc_node.get_text("\n", strip=True)
            data["description"] = text if text else None

        # coordonnées via iframe Google Maps
        iframe = soup.find("iframe", src=re.compile(r"google\.com/maps"))
        if iframe and iframe.get("src"):
            m = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", iframe["src"])
            if m:
                lat, lon = m.group(1), m.group(2)
                if data.get("latitude") is None:
                    data["latitude"] = _safe_float(lat)
                if data.get("longitude") is None:
                    data["longitude"] = _safe_float(lon)

        return data

    # On fusionne les 3 fonctions au dessus permettant de trouver des informations sur l'annonce vis à vis du code source de la page.
    def extract_property_data(self, soup, page_url=None):
        # 1) le plus riche d’abord (Wx)
        data = self.parse_listing_wx(soup) or {}

        # 2) compléter avec JSON-LD
        jsonld = self.parse_listing_jsonld(soup) or {}
        for k, v in jsonld.items():
            if data.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
                data[k] = v

        # 3) fallback HTML/CSS
        htcss = self.parse_listing_css(soup) or {}
        for k, v in htcss.items():
            if data.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
                data[k] = v

        # Valeurs par défaut pour pas bugger
        data.setdefault("titre", None)
        data.setdefault("prix", None)
        data.setdefault("adresse", None)
        data.setdefault("surface", None)
        data.setdefault("rooms", None)
        data.setdefault("latitude", None)
        data.setdefault("longitude", None)
        data.setdefault("description", None)
        data.setdefault("features", [])
        data.setdefault("property_type", "appartement")
        data.setdefault("url", page_url)

        return data

    # Fonction qui orchètre toutes les fonctions de ce fichier, il cherche les annonces, normalise les valeurs, sauvegarde les détails de l'annonce dans la db
    def scrape_c21(self, limit=300000, workers=24):
        urls = self.iter_listing_urls_from_sitemap(limit=limit) # Liste d'URL intéréssante
        print(f"URLs listées: {len(urls)}", flush=True)

        saved = 0

        def _scrape_one(u):
            try:
                soup = self.scrape(u)
                if not soup:
                    return 0
                prop = self.extract_property_data(soup, page_url=u) # prop = {"titre":xxx "prix":25000.0 etc}

                # type rent/sale
                prop["listing_type"] = infer_listing_type(
                    prop.get("titre"), prop.get("description"), prop.get("url"), price=prop.get("prix")
                )

                # insert
                save_property(
                    title=prop["titre"],
                    price=prop["prix"],
                    address=prop["adresse"],
                    surface=prop["surface"],
                    rooms=prop["rooms"],
                    property_type=prop.get("property_type", "appartement"),
                    latitude=prop["latitude"],
                    longitude=prop["longitude"],
                    description=prop["description"],
                    features=prop.get("features", []),
                    source=self.name,
                    url=prop["url"],
                    listing_type=prop.get("listing_type"),
                    scraped_at=datetime.utcnow(),
                )
                time.sleep(0.1 + random.random() * 0.3)
                return 1
            except Exception as e:
                print(f"error scrapping {u}: {e}", flush=True)
                return 0

        # On fait fonctionner des threads pour scrapper des centaines d'annonces rapidement, ça permet de paralléliser le travail
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_scrape_one, u) for u in urls]
            for f in as_completed(futures):
                saved += f.result()

        print(f"{saved}/{len(urls)} annonces C21 sauvegardées.", flush=True)
        return saved

