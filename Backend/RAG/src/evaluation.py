"""
Evaluation module using RAGAS metrics
"""
from typing import List, Dict, Optional
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_relevancy
)
from loguru import logger
import pandas as pd
import json
from pathlib import Path

from src.rag_pipeline import RAGPipeline


class RAGEvaluator:
    """
    Evaluate RAG system using RAGAS metrics
    """
    
    def __init__(self, rag_pipeline: RAGPipeline):
        """
        Initialize evaluator
        
        Args:
            rag_pipeline: RAGPipeline instance to evaluate
        """
        self.rag = rag_pipeline
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            context_relevancy
        ]
        
        logger.info("Initialized RAGEvaluator")
    
    def evaluate_single(
        self,
        question: str,
        ground_truth: str,
        language: str = "vi"
    ) -> Dict:
        """
        Evaluate a single question-answer pair
        
        Args:
            question: Question text
            ground_truth: Expected answer
            language: Language for generation
            
        Returns:
            Dictionary with evaluation results
        """
        # Get answer from RAG system
        result = self.rag.query(
            question=question,
            return_source_documents=True,
            language=language
        )
        
        # Extract contexts
        contexts = [
            doc["content"] 
            for doc in result["source_documents"]
        ]
        
        # Prepare data for RAGAS
        data = {
            "question": [question],
            "answer": [result["answer"]],
            "contexts": [contexts],
            "ground_truth": [ground_truth]
        }
        
        dataset = Dataset.from_dict(data)
        
        # Evaluate
        try:
            scores = evaluate(dataset, metrics=self.metrics)
            
            return {
                "question": question,
                "answer": result["answer"],
                "ground_truth": ground_truth,
                "metrics": {
                    "faithfulness": scores["faithfulness"],
                    "answer_relevancy": scores["answer_relevancy"],
                    "context_precision": scores["context_precision"],
                    "context_recall": scores["context_recall"],
                    "context_relevancy": scores["context_relevancy"]
                },
                "performance": {
                    "retrieval_time": result["retrieval_time"],
                    "generation_time": result["generation_time"],
                    "total_time": result["total_time"]
                }
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {
                "question": question,
                "error": str(e)
            }
    
    def evaluate_dataset(
        self,
        test_dataset: List[Dict],
        language: str = "vi"
    ) -> Dict:
        """
        Evaluate RAG system on a test dataset
        
        Args:
            test_dataset: List of {question, ground_truth} dicts
            language: Language for generation
            
        Returns:
            Dictionary with aggregated results
        """
        logger.info(f"Evaluating on {len(test_dataset)} questions...")
        
        results = []
        
        for i, item in enumerate(test_dataset, 1):
            logger.info(f"Evaluating question {i}/{len(test_dataset)}")
            
            result = self.evaluate_single(
                question=item["question"],
                ground_truth=item["ground_truth"],
                language=language
            )
            
            results.append(result)
        
        # Calculate aggregate metrics
        valid_results = [r for r in results if "error" not in r]
        
        if not valid_results:
            logger.error("No valid evaluation results")
            return {"error": "All evaluations failed"}
        
        aggregate = {
            "total_questions": len(test_dataset),
            "successful_evaluations": len(valid_results),
            "average_metrics": self._calculate_averages(valid_results),
            "average_performance": self._calculate_avg_performance(valid_results),
            "detailed_results": results
        }
        
        logger.info(f"✓ Evaluation complete: {len(valid_results)}/{len(test_dataset)} successful")
        logger.info(f"Average metrics: {aggregate['average_metrics']}")
        
        return aggregate
    
    def _calculate_averages(self, results: List[Dict]) -> Dict:
        """Calculate average metrics across results"""
        metric_names = [
            "faithfulness",
            "answer_relevancy", 
            "context_precision",
            "context_recall",
            "context_relevancy"
        ]
        
        averages = {}
        for metric in metric_names:
            values = [
                r["metrics"][metric] 
                for r in results 
                if metric in r.get("metrics", {})
            ]
            averages[metric] = sum(values) / len(values) if values else 0.0
        
        # Calculate overall RAGAS score (average of all metrics)
        averages["overall_ragas_score"] = sum(averages.values()) / len(averages)
        
        return averages
    
    def _calculate_avg_performance(self, results: List[Dict]) -> Dict:
        """Calculate average performance metrics"""
        perf_metrics = ["retrieval_time", "generation_time", "total_time"]
        
        averages = {}
        for metric in perf_metrics:
            values = [
                r["performance"][metric]
                for r in results
                if metric in r.get("performance", {})
            ]
            averages[metric] = sum(values) / len(values) if values else 0.0
        
        return averages
    
    def save_results(
        self,
        results: Dict,
        output_path: Path
    ):
        """
        Save evaluation results to JSON file
        
        Args:
            results: Evaluation results dictionary
            output_path: Path to save results
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Saved evaluation results to {output_path}")
    
    def create_report(
        self,
        results: Dict,
        output_path: Path
    ):
        """
        Create evaluation report as CSV
        
        Args:
            results: Evaluation results dictionary
            output_path: Path to save CSV report
        """
        detailed = results.get("detailed_results", [])
        
        if not detailed:
            logger.warning("No detailed results to create report")
            return
        
        # Create DataFrame
        rows = []
        for result in detailed:
            if "error" in result:
                continue
            
            row = {
                "question": result["question"],
                "answer_length": len(result["answer"]),
                **result["metrics"],
                **result["performance"]
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save to CSV
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"✓ Saved evaluation report to {output_path}")
        
        # Print summary statistics
        logger.info("\n" + "="*50)
        logger.info("EVALUATION SUMMARY")
        logger.info("="*50)
        logger.info(f"\nMetric Averages:")
        for col in df.columns:
            if col != "question":
                logger.info(f"  {col}: {df[col].mean():.4f}")


def load_test_dataset(file_path: Path) -> List[Dict]:
    """
    Load test dataset from JSON file
    
    Args:
        file_path: Path to JSON file with test questions
        
    Returns:
        List of test items
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data)} test questions from {file_path}")
    
    return data


def create_sample_test_dataset() -> List[Dict]:
    """
    Create a sample test dataset for demonstration
    
    Returns:
        List of sample test items
    """
    return [
        {
            "question": "Quy trình onboarding nhân viên mới là gì?",
            "ground_truth": "Quy trình onboarding bao gồm: đăng ký thông tin, training, setup tài khoản, và orientation với team."
        },
        {
            "question": "Chính sách nghỉ phép của công ty như thế nào?",
            "ground_truth": "Nhân viên được hưởng 12 ngày phép năm, cộng thêm ngày lễ theo quy định."
        },
        {
            "question": "Làm thế nào để đăng ký đào tạo nội bộ?",
            "ground_truth": "Đăng ký đào tạo qua portal nội bộ, chọn khóa học và submit form đăng ký."
        }
    ]
