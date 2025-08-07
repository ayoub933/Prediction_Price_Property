import psycopg2
from psycopg2 import sql
import os
from pathlib import Path
from connection import get_connection

# Fonction permettant de créer la base de donnée PostgreSQL via le fichier migrations.sql
def run_migrations():
    try:
        connexion = get_connection()
        if connexion is None:
            print("erreur")
            return
        
        cursor = connexion.cursor()

        # Lecture du fichier SQL
        sql_script = Path("migrations.sql").read_text()

        # Exécution du script complet
        cursor.execute(sql_script)

        connexion.commit()
        cursor.close()
        connexion.close()
        print("Migrations exécutées")
        
    except Exception as e:
        print(f"Erreur lors de l'exécution des migrations : {e}")

# Fonction permettant de sauvegarder les données passée en paramètre dans la table adaptée (properties)
def save_property(title, price, address, surface, rooms, property_type, latitude, longitude, description, features, source, url, scraped_at):
    try:
        connexion = get_connection()
        if connexion is None:
            print("erreur")
            return
        
        cursor = connexion.cursor()
        requête = """
             INSERT INTO properties
             (title, price, address, surface, rooms, property_type, latitude, longitude, description, features, source, url, scraped_at) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             """
        cursor.execute(requête, (title, price, address, surface, rooms, property_type, latitude, longitude, description, features, source, url, scraped_at))
        connexion.commit()
        cursor.close()
        connexion.close()
        print("Sauvegarde effectuée")
    except Exception as e:
        print(f"Erreur de sauvegarde : {e}")

# Fonction permettant d'afficher les données contenue dans la table properties
def get_all_properties():
    try:
        connexion = get_connection()
        if connexion is None:
            return
        
        cursor = connexion.cursor()
        requête = "SELECT * FROM properties"
        cursor.execute(requête)
        fetch = cursor.fetchall()  
        print(f"Voici les données contenu dans la table : \n {fetch}")
        cursor.close()
        connexion.close()
    except Exception as e:
        print(f"Erreur de récupération : {e}")

# Lancer ce fichier pour appliquer les 3 fonctions ci-dessus        
if __name__ == "__main__":
    run_migrations()
    # save_property(...)
    get_all_properties()