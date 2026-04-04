"""
Demo script to showcase RAG system capabilities
Run this after ingesting documents
"""
from src.rag_pipeline import RAGPipeline
from loguru import logger
import time


def print_separator():
    """Print a visual separator"""
    print("\n" + "="*70 + "\n")


def demo_basic_query():
    """Demo basic Q&A"""
    print_separator()
    logger.info("DEMO 1: Basic Question Answering")
    print_separator()
    
    rag = RAGPipeline(load_existing=True)
    
    questions = [
        "Quy trình onboarding nhân viên mới là gì?",
        "Chính sách nghỉ phép như thế nào?",
        "Làm thế nào để đăng ký training?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}] {question}")
        print("-" * 70)
        
        result = rag.query(
            question=question,
            return_source_documents=True,
            language="vi"
        )
        
        print(f"\n[Answer]\n{result['answer']}")
        print(f"\n[Performance]")
        print(f"  Retrieval: {result['retrieval_time']:.2f}s")
        print(f"  Generation: {result['generation_time']:.2f}s")
        print(f"  Total: {result['total_time']:.2f}s")
        
        if result.get('source_documents'):
            print(f"\n[Sources]")
            for j, doc in enumerate(result['source_documents'][:2], 1):
                print(f"  {j}. {doc['metadata'].get('filename', 'Unknown')}")
        
        print("\n" + "-" * 70)
        time.sleep(1)


def demo_conversation():
    """Demo conversation with context"""
    print_separator()
    logger.info("DEMO 2: Multi-turn Conversation")
    print_separator()
    
    rag = RAGPipeline(load_existing=True)
    conversation_id = "demo_conversation"
    
    conversation = [
        "Quy định về thời gian làm việc là gì?",
        "Có thể flexible không?",
        "Thời gian làm việc từ xa được không?"
    ]
    
    for i, question in enumerate(conversation, 1):
        print(f"\n[Turn {i}] User: {question}")
        print("-" * 70)
        
        result = rag.query(
            question=question,
            conversation_id=conversation_id,
            language="vi"
        )
        
        print(f"Assistant: {result['answer']}")
        print(f"(Time: {result['total_time']:.2f}s)")
        print("-" * 70)
        time.sleep(1)
    
    # Clear conversation
    rag.clear_conversation(conversation_id)


def demo_sources():
    """Demo source retrieval"""
    print_separator()
    logger.info("DEMO 3: Source Document Retrieval")
    print_separator()
    
    rag = RAGPipeline(load_existing=True)
    
    question = "Chính sách đào tạo và phát triển của công ty"
    print(f"\n[Query] {question}")
    print("-" * 70)
    
    sources = rag.get_sources(question)
    
    print(f"\n[Found {len(sources)} relevant sources]")
    for i, source in enumerate(sources, 1):
        print(f"\n{i}. {source['filename']}")
        print(f"   Page: {source['page']}")
        print(f"   Score: {source['score']:.4f}")
        print(f"   Preview: {source['preview'][:100]}...")


def demo_statistics():
    """Demo system statistics"""
    print_separator()
    logger.info("DEMO 4: System Statistics")
    print_separator()
    
    rag = RAGPipeline(load_existing=True)
    stats = rag.get_statistics()
    
    print("\n[Vector Store]")
    for key, value in stats['vector_store'].items():
        print(f"  {key}: {value}")
    
    print("\n[LLM]")
    for key, value in stats['llm'].items():
        print(f"  {key}: {value}")
    
    print("\n[Conversations]")
    print(f"  Active conversations: {stats['active_conversations']}")
    print(f"  Total turns: {stats['total_conversation_turns']}")


def demo_performance_comparison():
    """Demo performance metrics"""
    print_separator()
    logger.info("DEMO 5: Performance Benchmarking")
    print_separator()
    
    rag = RAGPipeline(load_existing=True)
    
    test_questions = [
        "What is the onboarding process?",
        "How to request vacation?",
        "Remote work policy?"
    ]
    
    print(f"\nTesting with {len(test_questions)} questions...")
    print("-" * 70)
    
    total_time = 0
    retrieval_times = []
    generation_times = []
    
    for question in test_questions:
        result = rag.query(question, language="en")
        total_time += result['total_time']
        retrieval_times.append(result['retrieval_time'])
        generation_times.append(result['generation_time'])
    
    print(f"\n[Results]")
    print(f"  Total queries: {len(test_questions)}")
    print(f"  Average total time: {total_time/len(test_questions):.2f}s")
    print(f"  Average retrieval: {sum(retrieval_times)/len(retrieval_times):.2f}s")
    print(f"  Average generation: {sum(generation_times)/len(generation_times):.2f}s")
    print(f"\n  Target: < 1.5s per query")
    
    if total_time/len(test_questions) < 1.5:
        print("  ✅ PASSED")
    else:
        print("  ⚠️  Consider optimization")


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("RAG SYSTEM DEMONSTRATION")
    print("="*70)
    
    try:
        # Check if system is ready
        rag = RAGPipeline(load_existing=True)
        stats = rag.get_statistics()
        
        if stats['vector_store'].get('total_vectors', 0) == 0:
            logger.warning(
                "\n⚠️  No documents found in vector store!\n"
                "Please run: python scripts/ingest_documents.py\n"
            )
            return
        
        logger.info(f"✓ System ready with {stats['vector_store']['total_vectors']} document chunks")
        
        # Run demos
        demo_basic_query()
        demo_conversation()
        demo_sources()
        demo_statistics()
        demo_performance_comparison()
        
        print_separator()
        logger.info("✓ All demos completed successfully!")
        print_separator()
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        logger.info(
            "\nMake sure:\n"
            "1. Documents are ingested (python scripts/ingest_documents.py)\n"
            "2. Model is downloaded (python scripts/download_models.py)\n"
            "3. Dependencies are installed (pip install -r requirements.txt)\n"
        )


if __name__ == "__main__":
    main()
