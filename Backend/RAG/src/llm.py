"""
LLM integration with quantized Llama 3 model
"""
from typing import Optional, List, Dict
from langchain_community.llms import LlamaCpp
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from loguru import logger
import time

from config import settings


class LlamaLLM:
    """
    Wrapper for quantized Llama 3 model (4-bit GGUF)
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = None,
        n_gpu_layers: int = None,
        n_batch: int = None,
        temperature: float = None,
        max_tokens: int = None,
        verbose: bool = False,
        streaming: bool = False
    ):
        """
        Initialize Llama 3 LLM
        
        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU (-1 for all)
            n_batch: Batch size for prompt processing
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            verbose: Enable verbose logging
            streaming: Enable streaming output
        """
        # Use settings defaults if not provided
        self.model_path = model_path or settings.LLAMA_MODEL_PATH
        self.n_ctx = n_ctx or settings.N_CTX
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else settings.N_GPU_LAYERS
        self.n_batch = n_batch or settings.N_BATCH
        self.temperature = temperature if temperature is not None else settings.TEMPERATURE
        self.max_tokens = max_tokens or settings.MAX_TOKENS
        
        # Setup callbacks
        callbacks = []
        if streaming:
            callbacks.append(StreamingStdOutCallbackHandler())
        callback_manager = CallbackManager(callbacks) if callbacks else None
        
        logger.info(f"Loading Llama 3 model from: {self.model_path}")
        logger.info(
            f"Config: n_ctx={self.n_ctx}, n_gpu_layers={self.n_gpu_layers}, "
            f"n_batch={self.n_batch}, temperature={self.temperature}"
        )
        
        try:
            # Initialize Llama model
            self.llm = LlamaCpp(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                callback_manager=callback_manager,
                verbose=verbose,
                n_threads=settings.N_THREADS,
            )
            
            logger.info("✓ Llama 3 model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Llama 3 model: {str(e)}")
            logger.error(
                "Make sure you have downloaded the model file. "
                "Run: python scripts/download_models.py"
            )
            raise
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Override max tokens
            temperature: Override temperature
            stop: Stop sequences
            
        Returns:
            Generated text
        """
        start_time = time.time()
        
        # Override parameters if provided
        kwargs = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        if stop is not None:
            kwargs["stop"] = stop
        
        # Generate response
        response = self.llm(prompt, **kwargs)
        
        elapsed = time.time() - start_time
        
        logger.info(
            f"Generated {len(response)} characters in {elapsed:.2f}s "
            f"({len(response)/elapsed:.0f} chars/s)"
        )
        
        return response
    
    def get_model_info(self) -> Dict:
        """
        Get model information
        
        Returns:
            Dictionary with model info
        """
        return {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": self.n_batch,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


def create_rag_prompt(
    question: str,
    context: str,
    language: str = "vi"
) -> str:
    """
    Create RAG prompt for Llama 3
    
    Args:
        question: User question
        context: Retrieved context
        language: Response language ('vi' or 'en')
        
    Returns:
        Formatted prompt
    """
    if language == "vi":
        system_message = """Bạn là trợ lý phân tích và so sánh văn bản pháp lý.
NGUYÊN TẮC TỐI THƯỢNG:
1. KHÔNG CÓ BẰNG CHỨNG -> KHÔNG ĐƯỢC KẾT LUẬN. Chỉ sử dụng thông tin từ CONTEXT.
2. Trích dẫn nguyên văn text gốc từ CONTEXT, TUYỆT ĐỐI KHÔNG paraphrase (diễn đạt lại).
3. Mọi điểm khác biệt phát hiện được BẮT BUỘC phải trình bày theo format sau:
[Doc v1 - <Vị trí Điều/Khoản>]
"...<trích dẫn chính xác text gốc bản v1>..."
[Doc v2 - <Vị trí Điều/Khoản>]
"...<trích dẫn chính xác text gốc bản v2>..."
"""
        
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_message}<|eot_id|><|start_header_id|>user<|end_header_id|>

CONTEXT:
{context}

QUESTION:
{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    else:  # English
        system_message = """You are a legal document analysis and comparison assistant.
SUPREME PRINCIPLES:
1. NO EVIDENCE -> NO CONCLUSION. Use only information from the CONTEXT.
2. Quote the original text exactly from the CONTEXT, ABSOLUTELY DO NOT paraphrase.
3. Any differences found MUST be presented in the following format:
[Doc v1 - <Article/Clause Position>]
"...<exact quote of original text v1>..."
[Doc v2 - <Article/Clause Position>]
"...<exact quote of original text v2>..."
"""
        
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_message}<|eot_id|><|start_header_id|>user<|end_header_id|>

CONTEXT:
{context}

QUESTION:
{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    return prompt


def create_conversation_prompt(
    question: str,
    context: str,
    chat_history: List[Dict[str, str]] = None,
    language: str = "vi"
) -> str:
    """
    Create conversation prompt with chat history
    
    Args:
        question: Current question
        context: Retrieved context
        chat_history: Previous conversation turns
        language: Response language
        
    Returns:
        Formatted conversation prompt
    """
    if language == "vi":
        system_message = """Bạn là trợ lý phân tích và so sánh văn bản pháp lý. NGUYÊN TẮC TỐI THƯỢNG: 1. KHÔNG CÓ BẰNG CHỨNG -> KHÔNG ĐƯỢC KẾT LUẬN. 2. Trích dẫn nguyên văn text gốc, không paraphrase. 3. Trình bày bằng chứng theo format: [Doc vX - Điều/Khoản] "...trích dẫn..."."""
    else:
        system_message = """You are a legal document analysis assistant. SUPREME PRINCIPLES: 1. NO EVIDENCE -> NO CONCLUSION. 2. Quote exactly, do not paraphrase. 3. Present evidence in format: [Doc vX - Article/Clause] "...quote..."."""
    
    prompt_parts = [
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_message}<|eot_id|>"
    ]
    
    # Add chat history
    if chat_history:
        for turn in chat_history[-3:]:  # Last 3 turns
            prompt_parts.append(
                f"<|start_header_id|>user<|end_header_id|>\n\n{turn['question']}<|eot_id|>"
            )
            prompt_parts.append(
                f"<|start_header_id|>assistant<|end_header_id|>\n\n{turn['answer']}<|eot_id|>"
            )
    
    # Add current context and question
    prompt_parts.append(
        f"<|start_header_id|>user<|end_header_id|>\n\nCONTEXT:\n{context}\n\nQUESTION:\n{question}<|eot_id|>"
    )
    prompt_parts.append(
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    
    return "".join(prompt_parts)