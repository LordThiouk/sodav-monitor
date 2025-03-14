"""
Module de gestion des logs pour SODAV Monitor.
Implémente un gestionnaire de logs singleton pour assurer une configuration cohérente.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

class LogManager:
    """
    Gestionnaire de logs singleton pour SODAV Monitor.
    Assure une configuration cohérente des logs à travers l'application.
    """
    
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        """Implémentation du pattern Singleton."""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le gestionnaire de logs."""
        if self._initialized:
            return
            
        # Créer le répertoire de logs s'il n'existe pas
        self.log_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configurer le logger racine
        self.root_logger = logging.getLogger("sodav_monitor")
        self.root_logger.setLevel(logging.DEBUG)
        
        # Éviter la duplication des handlers
        if not self.root_logger.handlers:
            # Formatter pour les fichiers
            file_formatter = logging.Formatter(
                '%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Formatter pour la console
            console_formatter = logging.Formatter(
                '%(levelname)s:%(name)s:%(message)s'
            )
            
            # Handler pour les logs généraux
            general_log_path = os.path.join(self.log_dir, "sodav.log")
            general_handler = RotatingFileHandler(
                general_log_path, 
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            general_handler.setFormatter(file_formatter)
            general_handler.setLevel(logging.INFO)
            
            # Handler pour les erreurs
            error_log_path = os.path.join(self.log_dir, "error.log")
            error_handler = RotatingFileHandler(
                error_log_path, 
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            error_handler.setFormatter(file_formatter)
            error_handler.setLevel(logging.ERROR)
            
            # Handler pour la console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.DEBUG if self._is_development() else logging.INFO)
            
            # Ajouter les handlers au logger racine
            self.root_logger.addHandler(general_handler)
            self.root_logger.addHandler(error_handler)
            self.root_logger.addHandler(console_handler)
        
        self._initialized = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtient un logger nommé avec la configuration appropriée.
        
        Args:
            name: Nom du logger
            
        Returns:
            Logger configuré
        """
        if name in self._loggers:
            return self._loggers[name]
            
        # Préfixer avec sodav_monitor pour maintenir la hiérarchie
        full_name = f"sodav_monitor.{name}" if not name.startswith("sodav_monitor") else name
        logger = logging.getLogger(full_name)
        
        # Stocker dans le cache
        self._loggers[name] = logger
        
        return logger
    
    def _is_development(self) -> bool:
        """Vérifie si l'environnement est en développement."""
        return os.environ.get("ENV", "development").lower() == "development" 