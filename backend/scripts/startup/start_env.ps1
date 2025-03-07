# Script PowerShell pour démarrer l'application dans différents environnements

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("development", "production")]
    [string]$Environment
)

# Aller au répertoire racine du projet
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

# Vérifier si le fichier .env.{Environment} existe
$envFile = ".env.$Environment"
if (-not (Test-Path $envFile)) {
    Write-Error "Erreur: Le fichier $envFile n'existe pas."
    Write-Host "Veuillez créer ce fichier en vous basant sur .env.example"
    exit 1
}

# Définir la variable d'environnement ENV
$env:ENV = $Environment

Write-Host "Démarrage de l'application en environnement $Environment..."
Write-Host "Utilisation du fichier de configuration: $envFile"

# Note: Les répertoires nécessaires sont créés automatiquement par config.py

# Démarrer l'application
if ($Environment -eq "development") {
    # Mode développement avec rechargement automatique
    Write-Host "Mode développement avec rechargement automatique"
    python backend/run_app.py
}
else {
    # Mode production
    Write-Host "Mode production"
    python backend/run.py
} 