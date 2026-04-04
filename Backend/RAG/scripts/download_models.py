"""
Script to download required models
"""
import os
from pathlib import Path
from loguru import logger
import requests
from tqdm import tqdm

from config import settings


def download_file(url: str, destination: Path):
    """Download file with progress bar"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as file, tqdm(
        desc=destination.name,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)


def download_llama_model():
    """Download Llama 3 8B Instruct quantized model"""
    logger.info("Downloading Llama 3 8B Instruct (4-bit GGUF)...")
    
    # Model URL (TheBloke's quantized version)
    model_url = "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct-q4_K_M.gguf"
    
    destination = Path(settings.LLAMA_MODEL_PATH)
    
    if destination.exists():
        logger.info(f"Model already exists at {destination}")
        return
    
    logger.info(f"Downloading from: {model_url}")
    logger.info(f"Saving to: {destination}")
    logger.info("This may take a while (file size: ~4.5GB)...")
    
    try:
        download_file(model_url, destination)
        logger.info(f"✓ Successfully downloaded model to {destination}")
    except Exception as e:
        logger.error(f"Failed to download model: {str(e)}")
        logger.info(
            "\nAlternative: Download manually from:\n"
            "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF\n"
            f"And place it at: {destination}"
        )


def verify_models():
    """Verify all required models are available"""
    logger.info("Verifying models...")
    
    # Check Llama model
    llama_path = Path(settings.LLAMA_MODEL_PATH)
    if llama_path.exists():
        size_gb = llama_path.stat().st_size / (1024**3)
        logger.info(f"✓ Llama 3 model found ({size_gb:.2f} GB)")
    else:
        logger.warning(f"✗ Llama 3 model not found at {llama_path}")
        return False
    
    logger.info("✓ All models verified")
    return True


def main():
    """Main function to download all models"""
    logger.info("="*50)
    logger.info("Model Download Script")
    logger.info("="*50)
    
    # Create models directory
    Path(settings.LLAMA_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    # Download Llama model
    download_llama_model()
    
    # Verify
    if verify_models():
        logger.info("\n✓ All models ready to use!")
        logger.info("\nNote: Embedding and reranking models will be downloaded")
        logger.info("automatically on first use via HuggingFace transformers.")
    else:
        logger.error("\n✗ Some models are missing. Please download them manually.")


if __name__ == "__main__":
    main()
