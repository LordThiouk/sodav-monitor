import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer l'URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"DATABASE_URL trouvée : {DATABASE_URL}")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL n'est pas définie!")

# Assurer que l'URL commence par postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Tester la connexion
print("Tentative de connexion à la base de données...")
engine = create_engine(DATABASE_URL)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        print(f"✅ Connexion à la base réussie ! Résultat du test : {result}")
except Exception as e:
    print(f"❌ Erreur de connexion : {e}") 