from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime
import os
import sqlite3

# Configure logging with a better format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def print_separator(char="=", length=80):
    logger.info(char * length)

def show_database_logs():
    try:
        print_separator()
        logger.info("CONSULTATION DES LOGS DE LA BASE DE DONNÉES")
        print_separator()
        
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, "sodav_monitor.db")
        
        logger.info(f"Chemin de la base de données: {db_path}")
        
        # Use direct SQLite connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='radio_stations';")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                print_separator("-")
                logger.info("CONTENU DE LA TABLE RADIO_STATIONS")
                
                # Get all stations
                cursor.execute("""
                    SELECT id, name, stream_url, country, language, status, is_active, 
                           last_checked, last_detection_time, total_play_time 
                    FROM radio_stations;
                """)
                stations = cursor.fetchall()
                
                if stations:
                    for station in stations:
                        print_separator("-")
                        logger.info(f"Station ID: {station[0]}")
                        logger.info(f"Nom: {station[1]}")
                        logger.info(f"URL: {station[2]}")
                        logger.info(f"Pays: {station[3]}")
                        logger.info(f"Langue: {station[4]}")
                        logger.info(f"Statut: {station[5]}")
                        logger.info(f"Actif: {'Oui' if station[6] else 'Non'}")
                        logger.info(f"Dernière vérification: {station[7]}")
                        logger.info(f"Dernière détection: {station[8]}")
                        logger.info(f"Temps total de lecture: {station[9] or '0:00:00'}")
                else:
                    logger.info("Aucune station trouvée dans la base de données")
            else:
                logger.info("❌ La table radio_stations n'existe pas")
            
            print_separator()
            logger.info("CONSULTATION TERMINÉE")
            print_separator()
            
        except Exception as e:
            logger.error(f"❌ Erreur pendant la consultation: {str(e)}")
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {str(e)}")
        raise e

def init_database():
    try:
        print_separator()
        logger.info("VÉRIFICATION DE LA BASE DE DONNÉES")
        print_separator()
        
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, "sodav_monitor.db")
        
        logger.info(f"Chemin de la base de données: {db_path}")
        
        # Use direct SQLite connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='radio_stations';")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                logger.info("✓ Table radio_stations existe déjà")
                # Get number of stations
                cursor.execute("SELECT COUNT(*) FROM radio_stations;")
                count = cursor.fetchone()[0]
                logger.info(f"✓ Nombre de stations: {count}")
            else:
                print_separator("-")
                logger.info("CRÉATION DE LA NOUVELLE TABLE")
                # Create fresh radio_stations table
                cursor.execute("""
                    CREATE TABLE radio_stations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        stream_url TEXT,
                        country TEXT,
                        language TEXT,
                        status TEXT DEFAULT 'inactive',
                        is_active INTEGER DEFAULT 0,
                        last_checked TIMESTAMP,
                        last_detection_time TIMESTAMP,
                        total_play_time TEXT
                    );
                """)
                
                conn.commit()
                logger.info("✓ Table radio_stations créée avec succès")
            
            print_separator()
            logger.info("VÉRIFICATION TERMINÉE AVEC SUCCÈS")
            print_separator()
            
        except Exception as e:
            logger.error(f"❌ Erreur pendant la vérification: {str(e)}")
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {str(e)}")
        raise e

if __name__ == "__main__":
    init_database()
    show_database_logs() 