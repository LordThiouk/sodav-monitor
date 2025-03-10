# Script PowerShell pour configurer Docker avec les logs et lancer les services
Write-Host "Configuration de Docker avec les paramètres de logging..." -ForegroundColor Green

# Créer les répertoires de logs s'ils n'existent pas
$logDirs = @(
    "logs/docker",
    "logs/docker/backend",
    "logs/docker/frontend",
    "logs/docker/postgres",
    "logs/docker/redis",
    "logs/docker/prometheus",
    "logs/docker/grafana",
    "logs/docker/node-exporter",
    "logs/docker/nginx"
)

foreach ($dir in $logDirs) {
    if (-not (Test-Path $dir)) {
        Write-Host "Création du répertoire $dir..." -ForegroundColor Yellow
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}

# Charger les variables d'environnement depuis .env
if (Test-Path .env) {
    Write-Host "Chargement des variables d'environnement depuis .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Variable définie: $name" -ForegroundColor Gray
        }
    }
}

# Vérifier si Docker est en cours d'exécution
try {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker n'est pas en cours d'exécution. Veuillez démarrer Docker Desktop." -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker est en cours d'exécution." -ForegroundColor Green
} catch {
    Write-Host "Erreur lors de la vérification de Docker: $_" -ForegroundColor Red
    exit 1
}

# Copier le fichier de configuration Docker si nécessaire
$dockerConfigDir = "$env:USERPROFILE\.docker"
if (-not (Test-Path $dockerConfigDir)) {
    Write-Host "Création du répertoire de configuration Docker..." -ForegroundColor Yellow
    New-Item -Path $dockerConfigDir -ItemType Directory -Force | Out-Null
}

if (Test-Path "docker\daemon.json") {
    Write-Host "Copie du fichier de configuration Docker..." -ForegroundColor Yellow
    Copy-Item -Path "docker\daemon.json" -Destination "$dockerConfigDir\daemon.json" -Force
}

# Nettoyer les conteneurs et images existants si nécessaire
Write-Host "Nettoyage des conteneurs arrêtés..." -ForegroundColor Yellow
docker container prune -f

# Lancer Docker Compose avec logs détaillés
Write-Host "Lancement de Docker Compose..." -ForegroundColor Green
docker-compose --log-level DEBUG up -d

# Vérifier l'état des services
Write-Host "Vérification de l'état des services..." -ForegroundColor Green
docker-compose ps

Write-Host "Configuration terminée. Les logs sont disponibles dans le répertoire logs/docker/" -ForegroundColor Green 