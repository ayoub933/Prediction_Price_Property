import psycopg2
import os
from psycopg2 import sql

def get_connection():
    try:
        connexion = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            database=os.getenv("PGDATABASE", "real_estate_db"),
            user=os.getenv("PGUSER", "lamloum"),
            password=os.getenv("PGPASSWORD", "lamloum123"),
            port=int(os.getenv("PGPORT", "5432")),
            sslmode=os.getenv("PGSSLMODE")
        )
        return connexion
    except Exception as e:
        print(f"Erreur de connexion : {e}")
        return None