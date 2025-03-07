import os
import re

def update_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Mettre à jour les imports relatifs
    replacements = {
        'from .models import': 'from ..models.models import',
        'from .utils.': 'from ..utils.',
        'from .audio_fingerprint': 'from .audio_fingerprint',
        'from .database': 'from ..models.database',
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                print(f"Updating imports in {file_path}")
                update_imports(file_path)

if __name__ == '__main__':
    # Mettre à jour les imports dans les dossiers principaux
    directories = [
        'backend/detection',
        'backend/processing',
        'backend/models',
        'backend/utils'
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            process_directory(directory)
            print(f"✅ Updated imports in {directory}")
        else:
            print(f"⚠️ Directory {directory} does not exist")

print("Import updates completed!") 