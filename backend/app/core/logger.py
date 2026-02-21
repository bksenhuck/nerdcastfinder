"""
Centralized logging for Nerdcast Finder - Backend re-export
This module re-exports the logger from utils for backward compatibility.
All logger code is maintained in utils/logger.py
"""
from utils.logger import logger, Logger

__all__ = ['logger', 'Logger']
