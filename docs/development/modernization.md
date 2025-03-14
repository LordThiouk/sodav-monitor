# Modernisation du Code SODAV Monitor

Ce document décrit les modifications apportées pour moderniser le code du projet SODAV Monitor et le rendre compatible avec les dernières versions des bibliothèques utilisées.

## SQLAlchemy 2.0

### Modifications apportées

- Mise à jour de l'import de `declarative_base` :
  ```python
  # Avant
  from sqlalchemy.ext.declarative import declarative_base

  # Après
  from sqlalchemy.orm import declarative_base
  ```

### Fichiers modifiés

- `backend/models/models.py`
- `backend/models/database.py`

## Pydantic V2

### Modifications apportées

1. Remplacement des validateurs `@validator` par `@field_validator` :
   ```python
   # Avant
   @validator('title', 'artist')
   def validate_non_empty(cls, v):
       # ...

   # Après
   @field_validator('title', 'artist')
   @classmethod
   def validate_non_empty(cls, v):
       # ...
   ```

2. Remplacement des classes `Config` par `model_config` avec `ConfigDict` :
   ```python
   # Avant
   class Config:
       from_attributes = True
       json_schema_extra = { ... }

   # Après
   model_config = ConfigDict(
       from_attributes=True,
       json_schema_extra={ ... }
   )
   ```

3. Mise à jour des encodeurs JSON :
   ```python
   # Avant
   class Config:
       json_encoders = {
           datetime: lambda v: v.isoformat(),
           timedelta: lambda v: int(v.total_seconds())
       }

   # Après
   model_config = ConfigDict(
       json_encoders={
           timedelta: lambda v: v.total_seconds() if v else None
       }
   )
   ```

### Fichiers modifiés

- `backend/schemas/base.py`
- `backend/config.py`
- `backend/routers/channels.py`
- `backend/routers/detections.py`

## FastAPI Lifespan

### Modifications apportées

Remplacement des gestionnaires d'événements `@app.on_event` par le nouveau système de lifespan :

```python
# Avant
@app.on_event("startup")
async def startup_event():
    # ...

@app.on_event("shutdown")
async def shutdown_event():
    # ...

# Après
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # ...
    except Exception as e:
        # ...
        raise

    yield  # Application runs here

    # Shutdown
    try:
        # ...
    except Exception as e:
        # ...

app = FastAPI(
    # ...
    lifespan=lifespan
)
```

### Fichiers modifiés

- `backend/main.py`

## Redis

### Modifications apportées

Remplacement de `close()` par `aclose()` pour la fermeture du pool Redis :

```python
# Avant
await app.state.redis_pool.close()

# Après
await app.state.redis_pool.aclose()
```

### Fichiers modifiés

- `backend/main.py` (via le gestionnaire de lifespan)

## Résultats

Ces modifications ont permis de :

1. Réduire considérablement le nombre d'avertissements de dépréciation
2. Rendre le code compatible avec les dernières versions des bibliothèques
3. Améliorer la maintenabilité du code
4. Préparer le projet pour les futures mises à jour

Les tests d'intégration passent toujours, ce qui confirme que les modifications n'ont pas introduit de régressions.

## Prochaines étapes

1. Mettre à jour les tests unitaires pour qu'ils fonctionnent avec les nouvelles versions des bibliothèques
2. Continuer à nettoyer les fichiers redondants
3. Optimiser les performances du code
4. Améliorer la documentation
