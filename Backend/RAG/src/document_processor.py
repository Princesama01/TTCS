"""
Document processing module for PDF extraction and chunking
Handles text extraction from PDFs and splitting into optimized chunks
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from loguru import logger
from tqdm import tqdm
import json


class PDFProcessor:
    """Process PDF documents for RAG pipeline"""
    
    def __init__(
        self, 
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize PDF processor
        
        Args:
            chunk_size: Size of text chunks (default optimized: 512)
            chunk_overlap: Overlap between chunks (default: 50)
            separators: Custom separators for text splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Optimize separators for Vietnamese and English
        if separators is None:
            separators = [
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentence ends
                "? ",
                "! ",
                "; ",
                ", ",
                " ",
                ""
            ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
        )
        
        logger.info(
            f"Initialized PDFProcessor with chunk_size={chunk_size}, "
            f"overlap={chunk_overlap}"
        )
    
    def extract_text_from_pdf(
        self, 
        pdf_path: Path
    ) -> tuple[str, Dict]:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            
            # Extract metadata
            metadata = {
                "source": str(pdf_path),
                "filename": pdf_path.name,
                "pages": doc.page_count,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
            }
            
            # Extract text from each page
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
            
            doc.close()
            
            full_text = "\n\n".join(text_content)
            logger.info(
                f"Extracted {len(full_text)} characters from "
                f"{metadata['pages']} pages in {pdf_path.name}"
            )
            
            return full_text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            raise
    
    def process_pdf(
        self, 
        pdf_path: Path,
        add_metadata: Optional[Dict] = None
    ) -> List[Document]:
        """
        Process single PDF file into chunks
        
        Args:
            pdf_path: Path to PDF file
            add_metadata: Additional metadata to add to chunks
            
        Returns:
            List of Document objects with chunks
        """
        # Extract text and metadata
        text, metadata = self.extract_text_from_pdf(pdf_path)
        
        # Add custom metadata if provided
        if add_metadata:
            metadata.update(add_metadata)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create Document objects
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy()
            doc_metadata["chunk_id"] = i
            doc_metadata["total_chunks"] = len(chunks)
            
            documents.append(
                Document(
                    page_content=chunk,
                    metadata=doc_metadata
                )
            )
        
        logger.info(
            f"Created {len(documents)} chunks from {pdf_path.name}"
        )
        
        return documents
    
    def process_directory(
        self, 
        directory: Path,
        file_pattern: str = "*.pdf",
        recursive: bool = True
    ) -> List[Document]:
        """
        Process all PDF files in a directory
        
        Args:
            directory: Directory containing PDF files
            file_pattern: Pattern to match PDF files
            recursive: Search subdirectories
            
        Returns:
            List of all Document chunks from all PDFs
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        # Find all PDF files
        if recursive:
            pdf_files = list(directory.rglob(file_pattern))
        else:
            pdf_files = list(directory.glob(file_pattern))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process all PDFs
        all_documents = []
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                documents = self.process_pdf(pdf_path)
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                continue
        
        logger.info(
            f"Processed {len(pdf_files)} PDFs into "
            f"{len(all_documents)} total chunks"
        )
        
        return all_documents
    
    def save_processed_documents(
        self, 
        documents: List[Document],
        output_path: Path
    ):
        """
        Save processed documents to JSON file
        
        Args:
            documents: List of Document objects
            output_path: Path to save JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert documents to serializable format
        docs_data = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in documents
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(documents)} documents to {output_path}")
    
    def load_processed_documents(
        self, 
        input_path: Path
    ) -> List[Document]:
        """
        Load processed documents from JSON file
        
        Args:
            input_path: Path to JSON file
            
        Returns:
            List of Document objects
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        
        documents = [
            Document(
                page_content=doc["content"],
                metadata=doc["metadata"]
            )
            for doc in docs_data
        ]
        
        logger.info(f"Loaded {len(documents)} documents from {input_path}")
        return documents


def optimize_chunk_size(
    pdf_path: Path,
    chunk_sizes: List[int] = [256, 512, 768, 1024],
    overlap_ratio: float = 0.1
) -> Dict:
    """
    Experiment with different chunk sizes to find optimal configuration
    
    Args:
        pdf_path: Path to test PDF file
        chunk_sizes: List of chunk sizes to test
        overlap_ratio: Ratio of overlap to chunk size
        
    Returns:
        Dictionary with results for each chunk size
    """
    results = {}
    
    for chunk_size in chunk_sizes:
        overlap = int(chunk_size * overlap_ratio)
        processor = PDFProcessor(
            chunk_size=chunk_size,
            chunk_overlap=overlap
        )
        
        documents = processor.process_pdf(pdf_path)
        
        # Calculate statistics
        chunk_lengths = [len(doc.page_content) for doc in documents]
        
        results[chunk_size] = {
            "total_chunks": len(documents),
            "avg_chunk_length": sum(chunk_lengths) / len(chunk_lengths),
            "min_chunk_length": min(chunk_lengths),
            "max_chunk_length": max(chunk_lengths),
            "overlap": overlap
        }
        
        logger.info(
            f"Chunk size {chunk_size}: {len(documents)} chunks, "
            f"avg length {results[chunk_size]['avg_chunk_length']:.0f}"
        )
    
    return results
