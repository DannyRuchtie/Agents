"""Scanner agent for document processing and vectorization."""
from pathlib import Path
from typing import Dict, List, Optional
import os
import hashlib
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from PyPDF2 import PdfReader

from config.paths_config import get_path

class ScannerAgent:
    """Agent for handling document processing and vectorization."""
    
    def __init__(self):
        """Initialize the Scanner Agent."""
        # Set up document storage
        self.docs_dir = get_path('documents')
        self.vectordb_dir = get_path('vectorstore')
        
        # Initialize embeddings and vector store
        try:
            print("Initializing OpenAI embeddings...")
            self.embeddings = OpenAIEmbeddings()
            print("Embeddings initialized successfully")
            
            print("Initializing Chroma database...")
            self.db = Chroma(
                persist_directory=str(self.vectordb_dir),
                embedding_function=self.embeddings,
                collection_metadata={"hnsw:space": "cosine"}
            )
            print("Successfully initialized vector store")
        except Exception as e:
            print(f"Error initializing embeddings/db: {str(e)}")
            print(f"Error type: {type(e)}")
            self.embeddings = None
            self.db = None
            
        # Set up file watcher
        self.observer = None
        try:
            self.observer = Observer()
            event_handler = DocumentEventHandler(self)
            self.observer.schedule(
                event_handler,
                str(self.docs_dir),
                recursive=False
            )
            self.observer.start()
        except Exception as e:
            print(f"Error setting up file watcher: {e}")
            
        # Document tracking
        self.document_hashes = {}
        
    def __del__(self):
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
            except Exception as e:
                print(f"Error stopping observer: {e}")
                
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file contents"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest() 

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file."""
        try:
            reader = PdfReader(file_path)
            text = []
            print(f"Processing PDF with {len(reader.pages)} pages...")
            
            for i, page in enumerate(reader.pages):
                try:
                    content = page.extract_text()
                    if content.strip():
                        text.append(content)
                    print(f"✓ Processed page {i+1}")
                except Exception as e:
                    print(f"⚠️ Error on page {i+1}: {str(e)}")
                    continue
            
            if not text:
                return "PDF appears to be empty or unreadable."
                
            return "\n\n".join(text)
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error extracting text from PDF: {error_msg}")
            if "file has not been decrypted" in error_msg.lower():
                return "This PDF is encrypted and cannot be read. Please provide a decrypted version."
            elif "file exists" in error_msg.lower():
                return "Could not access the PDF file. Please check if the file exists and you have permission to read it."
            else:
                return f"Error reading PDF: {error_msg}"

    def process_document(self, file_path: str) -> bool:
        """Process a document and add it to the vector store."""
        if not self.db or not self.embeddings:
            print("Vector store not initialized")
            return False

        try:
            # Compute hash to check if file has changed
            current_hash = self._compute_file_hash(file_path)
            if file_path in self.document_hashes and self.document_hashes[file_path] == current_hash:
                return True  # File hasn't changed

            # Read the file content
            if file_path.lower().endswith('.pdf'):
                text = self._extract_text_from_pdf(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            if not text.strip():
                print(f"No text content found in {file_path}")
                return False

            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_text(text)

            # Create documents with metadata
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "source": file_path,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                ) for i, chunk in enumerate(chunks)
            ]

            # Add to vector store
            self.db.add_documents(documents)
            self.document_hashes[file_path] = current_hash
            print(f"Successfully processed document: {file_path}")
            return True

        except Exception as e:
            print(f"Error processing document {file_path}: {e}")
            return False

    async def process_documents(self, file_path: str) -> str:
        """Process a document file and return its content with analysis.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            A string containing the document content and analysis
        """
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
            
        try:
            # Extract text based on file type
            if file_path.lower().endswith('.pdf'):
                content = self._extract_text_from_pdf(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            if not content.strip():
                return f"No readable content found in {file_path}"
            
            # Process for vector store in background
            self.process_document(file_path)
            
            # Return content summary
            return f"Document Content:\n\n{content[:1000]}..." if len(content) > 1000 else content
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return f"Error processing document: {str(e)}"

    def remove_document(self, file_path: str) -> bool:
        """Remove a document from the vector store."""
        if not self.db:
            print("Vector store not initialized")
            return False

        try:
            # Remove from vector store
            self.db.delete({"source": file_path})
            # Remove from hash tracking
            self.document_hashes.pop(file_path, None)
            return True
        except Exception as e:
            print(f"Error removing document {file_path}: {e}")
            return False

    async def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant document chunks."""
        if not self.db:
            print("Vector store not initialized")
            return []

        try:
            results = self.db.similarity_search_with_relevance_scores(query, k=limit)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
                for doc, score in results
            ]
        except Exception as e:
            print(f"Error searching documents: {e}")
            return [] 

    def _on_file_created(self, file_path: str) -> None:
        """Handle file creation event."""
        print(f"Processing new document: {file_path}")
        self.process_document(file_path)

    def _on_file_modified(self, file_path: str) -> None:
        """Handle file modification event."""
        print(f"Processing modified document: {file_path}")
        self.process_document(file_path)

    def _on_file_deleted(self, file_path: str) -> None:
        """Handle file deletion event."""
        print(f"Removing document: {file_path}")
        self.remove_document(file_path)

class DocumentEventHandler(FileSystemEventHandler):
    def __init__(self, scanner_agent: ScannerAgent):
        self.scanner_agent = scanner_agent

    def on_created(self, event):
        if not event.is_directory:
            self.scanner_agent._on_file_created(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.scanner_agent._on_file_modified(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.scanner_agent._on_file_deleted(event.src_path) 