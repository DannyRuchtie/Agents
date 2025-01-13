"""Configuration for file paths used in the application."""

import os
from pathlib import Path

# Base directories
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
AGENTS_DIR = ROOT_DIR / "agents"
MODELS_DIR = ROOT_DIR / "models"
UTILS_DIR = ROOT_DIR / "utils"

# Agent-specific directories
AGENTS_DOCS_DIR = ROOT_DIR / "agents_docs"

# Sub-directories
DIRECTORIES = {
    'screenshots': AGENTS_DOCS_DIR / 'screenshots',
    'shared_images': AGENTS_DOCS_DIR / 'shared_images',
    'documents': AGENTS_DOCS_DIR / 'documents',
    'vectorstore': AGENTS_DOCS_DIR / 'vectorstore',
    'learning_data': AGENTS_DOCS_DIR / 'learning_data',
    'static': AGENTS_DOCS_DIR / 'static',
    'templates': AGENTS_DOCS_DIR / 'templates'
}

def get_path(directory_name: str) -> Path:
    """Get the path for a specific directory.
    
    Args:
        directory_name: Name of the directory to get path for
        
    Returns:
        Path object for the requested directory
    """
    if directory_name not in DIRECTORIES:
        raise ValueError(f"Unknown directory: {directory_name}")
    return DIRECTORIES[directory_name]

def ensure_directories():
    """Ensure all required directories exist."""
    # Create base directories
    base_dirs = [
        CONFIG_DIR,
        AGENTS_DIR,
        MODELS_DIR,
        UTILS_DIR,
        AGENTS_DOCS_DIR,
    ]
    
    for directory in base_dirs:
        directory.mkdir(exist_ok=True)
    
    # Create sub-directories
    for path in DIRECTORIES.values():
        path.mkdir(parents=True, exist_ok=True)
        
    return True 