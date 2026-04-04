"""
Script to evaluate the RAG system using RAGAS
"""
import argparse
from pathlib import Path
from loguru import logger
import json

from src.rag_pipeline import RAGPipeline
from src.evaluation import RAGEvaluator, load_test_dataset, create_sample_test_dataset
from config import settings


def main():
    """Main evaluation function"""
    parser = argparse.ArgumentParser(
        description="Evaluate RAG system using RAGAS metrics"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Path to test dataset JSON file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="vi",
        choices=["vi", "en"],
        help="Language for responses"
    )
    parser.add_argument(
        "--use-sample",
        action="store_true",
        help="Use sample test dataset"
    )
    
    args = parser.parse_args()
    
    # Load test dataset
    if args.use_sample:
        logger.info("Using sample test dataset")
        test_dataset = create_sample_test_dataset()
    elif args.dataset:
        logger.info(f"Loading test dataset from: {args.dataset}")
        test_dataset = load_test_dataset(Path(args.dataset))
    else:
        logger.error("Please provide --dataset or use --use-sample")
        return
    
    logger.info(f"Loaded {len(test_dataset)} test questions")
    
    # Initialize RAG pipeline
    logger.info("Initializing RAG pipeline...")
    rag = RAGPipeline(load_existing=True)
    
    # Initialize evaluator
    evaluator = RAGEvaluator(rag)
    
    # Run evaluation
    logger.info("Starting evaluation...")
    results = evaluator.evaluate_dataset(
        test_dataset=test_dataset,
        language=args.language
    )
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save results
    results_path = output_dir / "evaluation_results.json"
    evaluator.save_results(results, results_path)
    
    # Create report
    report_path = output_dir / "evaluation_report.csv"
    evaluator.create_report(results, report_path)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("EVALUATION SUMMARY")
    logger.info("="*60)
    
    if "average_metrics" in results:
        logger.info("\nAverage Metrics:")
        for metric, value in results["average_metrics"].items():
            logger.info(f"  {metric}: {value:.4f}")
        
        logger.info("\nAverage Performance:")
        for metric, value in results["average_performance"].items():
            logger.info(f"  {metric}: {value:.4f}s")
    
    logger.info(f"\nResults saved to: {output_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    main()
