"""Tests pour le script de réorganisation du projet."""

import os
import sys
import pytest
import shutil
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

# Add the backend directory to the path so we can import from it
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from reorganize_project import ProjectReorganizer

@pytest.fixture
def temp_project_dir():
    """Crée un répertoire temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        # Créer la structure minimale du projet
        os.makedirs("backend")
        os.makedirs("frontend")
        os.makedirs("docs")
        
        yield tmpdir
        
        os.chdir(original_dir)

@pytest.fixture
def reorganizer(temp_project_dir):
    """Crée une instance de ProjectReorganizer pour les tests."""
    with patch('backend.config.PATHS', {
        'BACKEND_DIR': 'backend',
        'DATA_DIR': 'backend/data',
        'LOG_DIR': 'backend/logs',
        'REPORT_DIR': 'backend/reports',
        'STATIC_DIR': 'backend/static'
    }):
        return ProjectReorganizer()

def test_ensure_dir(reorganizer, temp_project_dir):
    """Teste la création de répertoire."""
    test_dir = "test_directory"
    reorganizer.ensure_dir(test_dir)
    assert os.path.exists(test_dir)
    assert os.path.isdir(test_dir)

def test_update_init_file(reorganizer, temp_project_dir):
    """Teste la création de fichier __init__.py."""
    test_dir = "test_module"
    os.makedirs(test_dir)
    reorganizer.update_init_file(test_dir)
    
    init_file = os.path.join(test_dir, "__init__.py")
    assert os.path.exists(init_file)
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    assert "Module d'initialisation pour test_module" in content

def test_move_file(reorganizer, temp_project_dir):
    """Teste le déplacement de fichier."""
    # Créer un fichier source
    src_dir = "src_dir"
    dest_dir = "dest_dir"
    os.makedirs(src_dir)
    os.makedirs(dest_dir)
    
    test_file = os.path.join(src_dir, "test.py")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    reorganizer.move_file(test_file, dest_dir)
    
    assert not os.path.exists(test_file)
    assert os.path.exists(os.path.join(dest_dir, "test.py"))

def test_move_file_with_wildcard(reorganizer, temp_project_dir):
    """Teste le déplacement de fichiers avec wildcard."""
    # Créer des fichiers sources
    src_dir = "src_dir"
    dest_dir = "dest_dir"
    os.makedirs(src_dir)
    os.makedirs(dest_dir)
    
    # Créer quelques fichiers de test
    for i in range(3):
        with open(os.path.join(src_dir, f"test_{i}.py"), 'w') as f:
            f.write(f"test content {i}")
    
    reorganizer.move_file(os.path.join(src_dir, "test_*.py"), dest_dir)
    
    # Vérifier que tous les fichiers ont été déplacés
    assert len(os.listdir(src_dir)) == 0
    assert len(os.listdir(dest_dir)) == 3
    for i in range(3):
        assert os.path.exists(os.path.join(dest_dir, f"test_{i}.py"))

def test_test_path_consistency(reorganizer, temp_project_dir):
    """Teste la vérification de cohérence des chemins."""
    # Créer les répertoires nécessaires
    for path in reorganizer.config_paths.values():
        os.makedirs(path, exist_ok=True)
    
    errors = reorganizer.test_path_consistency()
    assert len(errors) == 0

def test_test_path_consistency_with_missing_paths(reorganizer, temp_project_dir):
    """Teste la vérification de cohérence avec des chemins manquants."""
    errors = reorganizer.test_path_consistency()
    assert len(errors) > 0
    assert any("Chemin manquant" in error for error in errors)

def test_reorganize_creates_all_directories(reorganizer, temp_project_dir):
    """Teste que la réorganisation crée tous les répertoires nécessaires."""
    with patch.object(reorganizer, 'test_path_consistency', return_value=[]):
        reorganizer.reorganize()
        
        # Vérifier que tous les répertoires ont été créés
        for base_dir, subdirs in reorganizer.base_dirs.items():
            for subdir in subdirs:
                full_path = os.path.join(base_dir, subdir) if base_dir else subdir
                assert os.path.exists(full_path)
                if base_dir == 'backend':
                    assert os.path.exists(os.path.join(full_path, '__init__.py'))

def test_update_reorganisation_doc(reorganizer, temp_project_dir):
    """Teste la mise à jour du fichier de documentation."""
    os.makedirs("docs")
    reorganizer.update_reorganisation_doc()
    
    assert os.path.exists("docs/REORGANISATION.md")
    with open("docs/REORGANISATION.md", 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "Réorganisation Unifiée du Projet" in content
    assert "Structure des Dossiers" in content
    assert "Déplacements de Fichiers" in content
    assert "Tests de Cohérence" in content 