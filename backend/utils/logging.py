"""
Module de logging pour SODAV Monitor.

Ce module fournit des fonctions utilitaires pour la journalisation.
"""

import logging
from typing import Optional


def log_with_category(
    logger: logging.Logger, category: str, level: str, message: str, exc_info: Optional[bool] = None
):
    """
    Journalise un message avec une catégorie spécifique.

    Args:
        logger: Logger à utiliser
        category: Catégorie du message (ex: 'DETECTION', 'TRACK_MANAGER')
        level: Niveau de log ('debug', 'info', 'warning', 'error', 'critical')
        message: Message à journaliser
        exc_info: Si True, inclut les informations d'exception
    """
    formatted_message = f"[{category}] {message}"

    if level.lower() == "debug":
        logger.debug(formatted_message, exc_info=exc_info)
    elif level.lower() == "info":
        logger.info(formatted_message, exc_info=exc_info)
    elif level.lower() == "warning":
        logger.warning(formatted_message, exc_info=exc_info)
    elif level.lower() == "error":
        logger.error(formatted_message, exc_info=exc_info)
    elif level.lower() == "critical":
        logger.critical(formatted_message, exc_info=exc_info)
    else:
        # Par défaut, utiliser info
        logger.info(formatted_message, exc_info=exc_info)
