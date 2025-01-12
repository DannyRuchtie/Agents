"""Configuration file for system paths."""
from pathlib import Path

# Main directory for all agent-related files
AGENTS_DOCS_DIR = Path("agents_docs")

# Ensure the main directory exists
AGENTS_DOCS_DIR.mkdir(exist_ok=True)

# Sub-directories
DIRECTORIES = {
    'screenshots': AGENTS_DOCS_DIR / 'screenshots',
    'shared_images': AGENTS_DOCS_DIR / 'shared_images',
    'documents': AGENTS_DOCS_DIR / 'documents',
    'speech_output': AGENTS_DOCS_DIR / 'speech_output',
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

def ensure_directories() -> None:
    """Create all required directories if they don't exist."""
    for path in DIRECTORIES.values():
        path.mkdir(parents=True, exist_ok=True)

def set_root_dir(new_path: str | Path) -> None:
    """Set a new root directory for all agent files.
    
    Args:
        new_path: New root directory path
    """
    global AGENTS_DOCS_DIR
    AGENTS_DOCS_DIR = Path(new_path)
    
    # Update all sub-directory paths
    for key in DIRECTORIES:
        DIRECTORIES[key] = AGENTS_DOCS_DIR / key
    
    # Ensure all directories exist
    ensure_directories() 