import warnings

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

warnings.filterwarnings("ignore", message=".*position_ids.*")
warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")


class LegalEmbedder:
    def __init__(self, model_name: str, device: str = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            self.model = SentenceTransformer(model_name, device=device)
        if hasattr(self.model, "get_embedding_dimension"):
            self.dim = self.model.get_embedding_dimension()
        else:
            self.dim = self.model.get_sentence_embedding_dimension()
        print(f"[OK] Loaded embedding model: {model_name} (dim={self.dim}, device={device})")

    def embed(self, texts: list, batch_size: int = 32) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10,
        )

    def embed_single(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
