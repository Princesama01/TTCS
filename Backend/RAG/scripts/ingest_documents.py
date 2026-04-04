"""
Script to ingest PDF documents into the RAG system
"""
import argparse
from pathlib import Path
from loguru import logger

from src.rag_pipeline import RAGPipeline
from config import settings


def main():
    """Main function for document ingestion"""
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into RAG system"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=settings.PDF_DATA_DIR,
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=settings.CHUNK_SIZE,
        help="Size of text chunks"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=settings.CHUNK_OVERLAP,
        help="Overlap between chunks"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate index from scratch"
    )
    
    args = parser.parse_args()
    
    # Validate directory
    pdf_dir = Path(args.directory)
    if not pdf_dir.exists():
        logger.error(f"Directory not found: {pdf_dir}")
        logger.info(f"Creating directory: {pdf_dir}")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        logger.warning("Please add PDF files to the directory and run again")
        return
    
    # Check for PDF files
    pdf_files = list(pdf_dir.glob("**/*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {pdf_dir}")
        logger.info("Please add PDF files to the directory and run again")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Initialize RAG pipeline
    logger.info("Initializing RAG pipeline...")
    rag = RAGPipeline(load_existing=not args.recreate)
    
    # Ingest documents
    logger.info("Starting document ingestion...")
    logger.info(f"Chunk size: {args.chunk_size}, Overlap: {args.chunk_overlap}")
    
    try:
        rag.ingest_documents(
            pdf_directory=pdf_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        
        # Print statistics
        stats = rag.get_statistics()
        logger.info("\n" + "="*50)
        logger.info("INGESTION COMPLETE")
        logger.info("="*50)
        logger.info(f"Total vectors in index: {stats['vector_store']['total_vectors']}")
        logger.info(f"Index path: {stats['vector_store']['index_path']}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
