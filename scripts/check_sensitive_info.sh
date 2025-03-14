#!/bin/bash

# Script pour vérifier la présence d'informations sensibles dans le code
# Utilisation: ./scripts/check_sensitive_info.sh

echo "Vérification des informations sensibles dans le code..."

# Définir les motifs à rechercher
PATTERNS=(
    "password"
    "secret"
    "token"
    "key"
    "api_key"
    "apikey"
    "ACOUSTID_API_KEY"
    "AUDD_API_KEY"
    "SECRET_KEY"
    "POSTGRES_PASSWORD"
)

# Fichiers à exclure
EXCLUDE_DIRS=(
    ".git"
    "node_modules"
    "venv"
    "env"
    "__pycache__"
    ".mypy_cache"
    ".pytest_cache"
)

# Construire la commande d'exclusion
EXCLUDE_CMD=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_CMD="$EXCLUDE_CMD --exclude-dir=$dir"
done

# Fichiers à inclure
INCLUDE_FILES=(
    "*.py"
    "*.js"
    "*.ts"
    "*.tsx"
    "*.jsx"
    "*.json"
    "*.yml"
    "*.yaml"
    "*.md"
    "*.sh"
    "*.sql"
    "Dockerfile*"
    "docker-compose*"
)

# Construire la commande d'inclusion
INCLUDE_CMD=""
for file in "${INCLUDE_FILES[@]}"; do
    INCLUDE_CMD="$INCLUDE_CMD --include=$file"
done

# Motifs à ignorer (expressions régulières)
IGNORE_PATTERNS=(
    "os\\.getenv\\([\"'].*[\"']\\)"
    "\\$\\{.*\\}"
    "\\.env\\.example"
    "check_sensitive_info\\.sh"
    "# Get your .* API key from"
    "# Générer une clé secrète avec"
    "your-.*-key"
    "your_.*_key"
    "your_.*_password"
    "your-.*-password"
    "test_.*_key"
    "test_secret_key"
    "example_key"
    "example_password"
)

# Rechercher les motifs
echo "Recherche des motifs potentiellement sensibles..."
FOUND_SENSITIVE=false

for pattern in "${PATTERNS[@]}"; do
    echo "Recherche du motif: $pattern"
    
    # Construire la commande de base
    CMD="grep -r -i \"$pattern\" $EXCLUDE_CMD $INCLUDE_CMD ."
    
    # Ajouter les motifs à ignorer
    for ignore in "${IGNORE_PATTERNS[@]}"; do
        CMD="$CMD | grep -v -E \"$ignore\""
    done
    
    # Exécuter la commande et capturer le résultat
    RESULT=$(eval "$CMD" 2>/dev/null || true)
    
    if [ -n "$RESULT" ]; then
        echo "⚠️  Motif potentiellement sensible trouvé: $pattern"
        echo "$RESULT"
        echo ""
        FOUND_SENSITIVE=true
    fi
done

if [ "$FOUND_SENSITIVE" = true ]; then
    echo "⚠️  Des informations potentiellement sensibles ont été trouvées dans le code."
    echo "    Veuillez vérifier les résultats ci-dessus et vous assurer qu'aucune information sensible n'est exposée."
    echo "    Si ce sont des faux positifs, vous pouvez les ignorer."
    exit 1
else
    echo "✅ Aucune information sensible n'a été trouvée dans le code."
    exit 0
fi 