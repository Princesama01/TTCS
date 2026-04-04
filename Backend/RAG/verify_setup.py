"""
System verification and health check script
"""
import sys
from pathlib import Path
from loguru import logger
import importlib.util


class SystemVerifier:
    """Verify RAG system setup and dependencies"""
    
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def check_python_version(self):
        """Check Python version"""
        logger.info("Checking Python version...")
        version = sys.version_info
        
        if version.major == 3 and version.minor >= 8:
            self.passed.append(f"✓ Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.failed.append(f"✗ Python version too old: {version.major}.{version.minor}")
            return False
    
    def check_dependencies(self):
        """Check required Python packages"""
        logger.info("Checking dependencies...")
        
        required_packages = [
            "langchain",
            "sentence_transformers",
            "faiss",
            "fitz",  # PyMuPDF
            "fastapi",
            "uvicorn",
            "pydantic",
            "loguru",
            "torch",
            "transformers",
            "ragas"
        ]
        
        for package in required_packages:
            try:
                if package == "fitz":
                    importlib.import_module("fitz")
                    self.passed.append(f"✓ PyMuPDF (fitz)")
                else:
                    importlib.import_module(package)
                    self.passed.append(f"✓ {package}")
            except ImportError:
                self.failed.append(f"✗ {package} not installed")
    
    def check_directories(self):
        """Check required directories exist"""
        logger.info("Checking directory structure...")
        
        required_dirs = [
            "src",
            "api",
            "utils",
            "scripts",
            "data",
            "data/documents",
            "data/processed",
            "logs",
            "models"
        ]
        
        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                self.passed.append(f"✓ Directory: {dir_path}")
            else:
                self.warnings.append(f"⚠ Directory missing: {dir_path}")
    
    def check_config(self):
        """Check configuration files"""
        logger.info("Checking configuration...")
        
        config_files = [
            "config.py",
            ".env",
            "requirements.txt",
            "README.md"
        ]
        
        for file_path in config_files:
            path = Path(file_path)
            if path.exists():
                self.passed.append(f"✓ Config file: {file_path}")
            else:
                if file_path == ".env":
                    self.warnings.append(f"⚠ {file_path} not found (copy from .env.example)")
                else:
                    self.failed.append(f"✗ {file_path} missing")
    
    def check_model(self):
        """Check if Llama model is downloaded"""
        logger.info("Checking model files...")
        
        try:
            from config import settings
            model_path = Path(settings.LLAMA_MODEL_PATH)
            
            if model_path.exists():
                size_gb = model_path.stat().st_size / (1024**3)
                self.passed.append(f"✓ Llama model found ({size_gb:.2f} GB)")
            else:
                self.warnings.append(
                    f"⚠ Llama model not found at {model_path}\n"
                    "  Run: python scripts/download_models.py"
                )
        except Exception as e:
            self.failed.append(f"✗ Error checking model: {str(e)}")
    
    def check_vector_store(self):
        """Check if vector store exists"""
        logger.info("Checking vector store...")
        
        try:
            from config import settings
            index_path = Path(settings.FAISS_INDEX_PATH)
            
            if index_path.exists():
                self.passed.append(f"✓ FAISS index found")
            else:
                self.warnings.append(
                    f"⚠ FAISS index not found\n"
                    "  Run: python scripts/ingest_documents.py"
                )
        except Exception as e:
            self.failed.append(f"✗ Error checking vector store: {str(e)}")
    
    def check_documents(self):
        """Check if documents exist"""
        logger.info("Checking documents...")
        
        try:
            from config import settings
            docs_dir = Path(settings.PDF_DATA_DIR)
            
            if docs_dir.exists():
                pdf_files = list(docs_dir.glob("**/*.pdf"))
                if pdf_files:
                    self.passed.append(f"✓ Found {len(pdf_files)} PDF documents")
                else:
                    self.warnings.append(
                        f"⚠ No PDF files in {docs_dir}\n"
                        "  Add PDF files to data/documents/"
                    )
            else:
                self.warnings.append(f"⚠ Documents directory not found")
        except Exception as e:
            self.failed.append(f"✗ Error checking documents: {str(e)}")
    
    def check_gpu(self):
        """Check GPU availability"""
        logger.info("Checking GPU availability...")
        
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                self.passed.append(f"✓ GPU available: {gpu_name}")
            else:
                self.warnings.append(
                    "⚠ No GPU detected (will use CPU)\n"
                    "  GPU recommended for faster performance"
                )
        except Exception as e:
            self.warnings.append(f"⚠ Could not check GPU: {str(e)}")
    
    def run_all_checks(self):
        """Run all verification checks"""
        print("\n" + "="*70)
        print("RAG SYSTEM VERIFICATION")
        print("="*70 + "\n")
        
        self.check_python_version()
        self.check_dependencies()
        self.check_directories()
        self.check_config()
        self.check_model()
        self.check_vector_store()
        self.check_documents()
        self.check_gpu()
        
        self.print_results()
    
    def print_results(self):
        """Print verification results"""
        print("\n" + "="*70)
        print("VERIFICATION RESULTS")
        print("="*70 + "\n")
        
        if self.passed:
            print("PASSED:")
            for item in self.passed[:10]:  # Show first 10
                print(f"  {item}")
            if len(self.passed) > 10:
                print(f"  ... and {len(self.passed) - 10} more")
        
        if self.warnings:
            print("\nWARNINGS:")
            for item in self.warnings:
                print(f"  {item}")
        
        if self.failed:
            print("\nFAILED:")
            for item in self.failed:
                print(f"  {item}")
        
        print("\n" + "="*70)
        print(f"Summary: {len(self.passed)} passed, {len(self.warnings)} warnings, {len(self.failed)} failed")
        print("="*70 + "\n")
        
        if self.failed:
            print("❌ System verification FAILED")
            print("Please fix the failed checks before proceeding.\n")
            return False
        elif self.warnings:
            print("⚠️  System verification PASSED with warnings")
            print("System will work but some features may not be available.\n")
            return True
        else:
            print("✅ System verification PASSED")
            print("All checks passed! Your RAG system is ready to use.\n")
            return True


def main():
    """Main verification function"""
    verifier = SystemVerifier()
    success = verifier.run_all_checks()
    
    if success:
        print("Next steps:")
        print("1. Download model: python scripts/download_models.py")
        print("2. Add PDFs to: data/documents/")
        print("3. Ingest docs: python scripts/ingest_documents.py")
        print("4. Start API: python api/main.py")
        print("5. Run demo: python demo.py")
    else:
        print("Please install missing dependencies:")
        print("pip install -r requirements.txt")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
