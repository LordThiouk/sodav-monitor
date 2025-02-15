from sqlalchemy import create_engine, text
from datetime import timedelta

# Créer la connexion à la base de données
engine = create_engine('sqlite:///sodav_monitor.db')

# Vérifier si la colonne existe
with engine.connect() as conn:
    # Vérifier si la colonne existe déjà
    result = conn.execute(text("PRAGMA table_info(artist_stats)"))
    columns = [row[1] for row in result]
    
    if 'total_play_time' not in columns:
        print("Ajout de la colonne total_play_time à artist_stats...")
        conn.execute(text("ALTER TABLE artist_stats ADD COLUMN total_play_time INTERVAL DEFAULT '0'"))
        conn.commit()
        print("Colonne ajoutée avec succès!")
    else:
        print("La colonne total_play_time existe déjà dans artist_stats.") 