#!/bin/bash
# Script pour démarrer le système SODAV Monitor complet
# Ce script lance à la fois le serveur web et le service de détection en parallèle

# Définir les couleurs pour les logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Vérifier si Python est installé
if ! command -v python &> /dev/null; then
    error "Python n'est pas installé. Veuillez installer Python 3.8 ou supérieur."
    exit 1
fi

# Vérifier la version de Python
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
log "Version de Python détectée: $PYTHON_VERSION"

# Vérifier si les dépendances sont installées
log "Vérification des dépendances..."
if ! python -c "import fastapi, uvicorn, sqlalchemy, aiohttp" &> /dev/null; then
    warning "Certaines dépendances sont manquantes. Installation en cours..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        error "Échec de l'installation des dépendances. Veuillez les installer manuellement."
        exit 1
    fi
    success "Dépendances installées avec succès."
fi

# Vérifier si fpcalc est installé
if ! command -v fpcalc &> /dev/null; then
    warning "fpcalc (Chromaprint) n'est pas installé. La détection avec AcoustID ne fonctionnera pas correctement."
    warning "Sur Ubuntu/Debian: sudo apt-get install libchromaprint-tools"
    warning "Sur macOS: brew install chromaprint"
fi

# Fonction pour arrêter tous les processus à la sortie
cleanup() {
    log "Arrêt des processus..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        log "Serveur web arrêté (PID: $SERVER_PID)"
    fi
    if [ ! -z "$DETECTION_PID" ]; then
        kill $DETECTION_PID 2>/dev/null
        log "Service de détection arrêté (PID: $DETECTION_PID)"
    fi
    exit 0
}

# Capturer les signaux pour un arrêt propre
trap cleanup SIGINT SIGTERM

# Démarrer le serveur web en arrière-plan
log "Démarrage du serveur web..."
python backend/run_app.py &
SERVER_PID=$!

# Vérifier si le serveur a démarré correctement
sleep 3
if ! ps -p $SERVER_PID > /dev/null; then
    error "Le serveur web n'a pas démarré correctement."
    cleanup
    exit 1
fi
success "Serveur web démarré avec PID: $SERVER_PID"

# Demander à l'utilisateur s'il souhaite démarrer le service de détection
read -p "Voulez-vous démarrer le service de détection musicale? (o/n): " START_DETECTION

if [[ "$START_DETECTION" =~ ^[oO]$ ]]; then
    # Demander les paramètres de configuration
    read -p "Nombre maximum de stations à traiter simultanément [5]: " MAX_CONCURRENT
    MAX_CONCURRENT=${MAX_CONCURRENT:-5}
    
    read -p "Intervalle entre les cycles de détection en secondes [60]: " INTERVAL
    INTERVAL=${INTERVAL:-60}
    
    # Démarrer le service de détection en arrière-plan
    log "Démarrage du service de détection (max_concurrent=$MAX_CONCURRENT, interval=$INTERVAL)..."
    python backend/scripts/run_detection_service.py --max_concurrent $MAX_CONCURRENT --interval $INTERVAL &
    DETECTION_PID=$!
    
    # Vérifier si le service a démarré correctement
    sleep 2
    if ! ps -p $DETECTION_PID > /dev/null; then
        error "Le service de détection n'a pas démarré correctement."
        warning "Le serveur web continue de fonctionner."
    else
        success "Service de détection démarré avec PID: $DETECTION_PID"
    fi
else
    warning "Service de détection non démarré. Vous pouvez le démarrer manuellement avec:"
    warning "python backend/scripts/run_detection_service.py"
fi

# Afficher les informations sur l'accès au serveur
success "SODAV Monitor est en cours d'exécution!"
log "Serveur web disponible à l'adresse: http://localhost:8000"
log "Documentation API: http://localhost:8000/api/docs"
log "Pour arrêter tous les services, appuyez sur Ctrl+C"

# Attendre que les processus se terminent
wait $SERVER_PID
log "Le serveur web s'est arrêté."

if [ ! -z "$DETECTION_PID" ]; then
    wait $DETECTION_PID
    log "Le service de détection s'est arrêté."
fi

success "SODAV Monitor arrêté avec succès." 