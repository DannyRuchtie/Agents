"""Scanner Agent for document vectorization and management."""
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .base_agent import BaseAgent

SCANNER_SYSTEM_PROMPT = """You are a Document Scanner Agent responsible for:
1. Processing and vectorizing documents
2. Maintaining a vector database of document contents
3. Tracking document changes and deletions
4. Providing semantic search capabilities
Focus on efficient document management and quick retrieval."""

class DocumentChangeHandler(FileSystemEventHandler):
    def __init__(self, scanner_agent):
        self.scanner_agent = scanner_agent
        
    def on_modified(self, event):
        if not event.is_directory:
            self.scanner_agent.process_document(event.src_path)
            
    def on_deleted(self, event):
        if not event.is_directory:
            self.scanner_agent.remove_document(event.src_path)

class ScannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type="scanner",
            system_prompt=SCANNER_SYSTEM_PROMPT
        )
        self.docs_dir = Path("documents")
        self.docs_dir.mkdir(exist_ok=True)
        
        # Initialize vector store with basic configuration
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        self.vectorstore = Chroma(
            persist_directory="vectorstore",
            embedding_function=self.embeddings
        )
        
        # Initialize file watcher
        self.observer = Observer()
        self.observer.schedule(
            DocumentChangeHandler(self),
            str(self.docs_dir),
            recursive=False
        )
        self.observer.start()
        
        # Document tracking
        self.document_map: Dict[str, str] = {}  # path -> hash
        
    def __del__(self):
        self.observer.stop()
        self.observer.join()
        
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file contents."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def process_document(self, original_path: str) -> None:
        """Process a document and add it to the vector store."""
        # Copy document to managed directory
        file_name = Path(original_path).name
        new_path = self.docs_dir / file_name
        shutil.copy2(original_path, new_path)
        
        # Check if document has changed
        file_hash = self._compute_file_hash(str(new_path))
        if self.document_map.get(str(new_path)) == file_hash:
            return
            
        # Process document
        with open(new_path, 'r') as f:
            text = f.read()
            
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)
        
        # Create documents with metadata
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "source": str(new_path),
                    "filename": file_name,
                    "timestamp": datetime.now().isoformat(),
                }
            ) for chunk in chunks
        ]
        
        # Remove old vectors if they exist
        if str(new_path) in self.document_map:
            self.remove_document(str(new_path))
            
        # Add to vector store
        self.vectorstore.add_documents(docs)
        self.document_map[str(new_path)] = file_hash
        
    def remove_document(self, path: str) -> None:
        """Remove a document from the vector store."""
        if path in self.document_map:
            # Remove from vector store
            self.vectorstore.delete(
                where={"source": path}
            )
            # Remove from tracking
            del self.document_map[path]
            # Remove file if it exists
            if Path(path).exists():
                Path(path).unlink()
                
    async def search_documents(self, query: str, k: int = 5) -> List[Dict]:
        """Search for documents similar to the query."""
        results = self.vectorstore.similarity_search(
            query,
            k=k,
            include_metadata=True
        )
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ] 