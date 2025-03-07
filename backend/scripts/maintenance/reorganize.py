import os
import shutil

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Définition de la structure
dirs = [
    'backend/detection',
    'backend/processing',
    'backend/reports',
    'backend/logs',
    'backend/analytics',
    'backend/models',
    'backend/utils',
    'backend/tests',
    'frontend/src/components',
    'frontend/src/pages',
    'frontend/src/services',
    'frontend/src/theme',
    'frontend/src/utils',
    'frontend/public',
    'scripts',
    'docker'
]

# Création des dossiers
for d in dirs:
    ensure_dir(d)

# Définition des fichiers à déplacer
file_moves = {
    'backend/detection/': [
        'backend/audio_fingerprint.py',
        'backend/audio_processor.py',
        'backend/detect_music.py',
        'backend/fingerprint.py',
        'backend/fingerprint_generator.py',
        'backend/music_recognition.py'
    ],
    'backend/processing/': [
        'backend/radio_manager.py'
    ],
    'backend/models/': [
        'backend/models.py',
        'backend/database.py'
    ],
    'backend/utils/': [
        'backend/config.py',
        'backend/redis_config.py'
    ],
    'backend/tests/': [
        'backend/test_*.py'
    ],
    'docker/': [
        'Dockerfile',
        'nginx.conf',
        'default.conf'
    ]
}

# Déplacement des fichiers
for dest, files in file_moves.items():
    ensure_dir(dest)
    for file_pattern in files:
        if '*' in file_pattern:
            # Pour les patterns avec wildcard
            base_dir = os.path.dirname(file_pattern)
            pattern = os.path.basename(file_pattern)
            for file in os.listdir(base_dir):
                if file.startswith(pattern.replace('*', '')):
                    src = os.path.join(base_dir, file)
                    if os.path.isfile(src):
                        shutil.move(src, os.path.join(dest, file))
        else:
            # Pour les fichiers spécifiques
            if os.path.exists(file_pattern):
                shutil.move(file_pattern, os.path.join(dest, os.path.basename(file_pattern)))

print("Réorganisation terminée !") 