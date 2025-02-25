import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer l'URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL n'est pas définie!")

# Assurer que l'URL commence par postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Créer la connexion
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# Lister toutes les tables
print("\n📊 Tables trouvées dans la base de données :")
print("=" * 50)
for table_name in inspector.get_table_names():
    print(f"✓ {table_name}")
    columns = inspector.get_columns(table_name)
    for column in columns:
        print(f"  - {column['name']} ({column['type']})")
    print("-" * 50)

# Vérifier les tables spécifiques attendues
expected_tables = {
    'users', 'radio_stations', 'tracks', 'track_detections', 
    'detection_hourly', 'artist_stats', 'analytics_data',
    'detection_daily', 'detection_monthly', 'artist_daily',
    'artist_monthly', 'reports', 'report_subscriptions'
}

found_tables = set(inspector.get_table_names())
missing_tables = expected_tables - found_tables

if missing_tables:
    print("\n⚠️ Tables manquantes :")
    for table in missing_tables:
        print(f"❌ {table}")
else:
    print("\n✅ Toutes les tables attendues ont été créées avec succès!") 