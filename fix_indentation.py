#!/usr/bin/env python3
"""
Script pour corriger l'erreur d'indentation dans le fichier core.py.
"""

import re
import sys

def fix_indentation(file_path):
    """
    Corrige l'erreur d'indentation dans le fichier spécifié.
    """
    print(f"Correction de l'indentation dans {file_path}")
    
    # Lire le fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Chercher la ligne problématique
    async_def_pattern = re.compile(r'^\s*async\s+def\s+process_stream\s*\(')
    fixed_lines = []
    in_async_def = False
    needs_indentation = False
    
    for i, line in enumerate(lines):
        if async_def_pattern.match(line):
            in_async_def = True
            needs_indentation = True
            fixed_lines.append(line)
            print(f"Ligne problématique trouvée à la ligne {i+1}: {line.strip()}")
        elif in_async_def and needs_indentation and line.strip() and not line.startswith(' '):
            # Ajouter une indentation de 4 espaces
            fixed_lines.append('    ' + line)
            needs_indentation = False
            print(f"Indentation ajoutée à la ligne {i+1}")
        else:
            fixed_lines.append(line)
    
    # Écrire le fichier corrigé
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Correction terminée pour {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_indentation.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    fix_indentation(file_path) 