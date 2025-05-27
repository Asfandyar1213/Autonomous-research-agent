"""
Comparative Analysis Module

This module compares methodologies, findings, and results across multiple research papers,
identifying similarities, differences, and trends in the literature.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
from sentence_transformers import SentenceTransformer, util

from autonomous_research_agent.core.exceptions import ModelError

logger = logging.getLogger(__name__)

class ComparativeAnalysis:
    """
    Compares methodologies, findings, and results across research papers
    """
    
    def __init__(self):
        """Initialize the comparative analysis module"""
        self.sentence_transformer = None
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize models for comparative analysis"""
        try:
            # Initialize sentence transformer for semantic similarity
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded Sentence Transformer model: all-MiniLM-L6-v2")
            
        except Exception as e:
            logger.error(f"Error initializing comparative analysis models: {str(e)}")
            raise ModelError("Comparative Analysis", f"Initialization error: {str(e)}")
    
    def compare_methodologies(self, methodologies: List[Dict]) -> Dict:
        """
        Compare methodologies across papers
        
        Args:
            methodologies: List of methodology dictionaries
            
        Returns:
            Dictionary with comparison results
        """
        # Count methodology categories
        category_counts = {}
        for methodology in methodologies:
            for category, score in methodology.items():
                if score > 0.3:  # Only count if confidence is high enough
                    if category not in category_counts:
                        category_counts[category] = 0
                    category_counts[category] += 1
        
        # Calculate methodology diversity
        unique_categories = len(category_counts)
        diversity_score = unique_categories / len(methodologies) if methodologies else 0
        
        # Find most common methodology
        most_common = max(category_counts.items(), key=lambda x: x[1]) if category_counts else (None, 0)
        
        # Calculate consensus score (how much agreement on methodology)
        consensus_score = most_common[1] / len(methodologies) if methodologies else 0
        
        # Prepare comparison results
        comparison = {
            'category_counts': category_counts,
            'most_common_methodology': most_common[0],
            'methodology_diversity': diversity_score,
            'consensus_score': consensus_score,
            'unique_methodologies': unique_categories
        }
        
        return comparison
    
    def compare_findings(self, findings_list: List[List[Dict]]) -> Dict:
        """
        Compare findings across papers
        
        Args:
            findings_list: List of findings lists from different papers
            
        Returns:
            Dictionary with comparison results
        """
        if not self.sentence_transformer:
            raise ModelError("Comparative Analysis", "Sentence Transformer model not initialized")
        
        # Extract all finding texts
        all_findings = []
        for paper_idx, findings in enumerate(findings_list):
            for finding in findings:
                all_findings.append({
                    'paper_idx': paper_idx,
                    'text': finding['text'],
                    'confidence': finding['confidence'],
                    'source': finding.get('source', 'unknown')
                })
        
        # If no findings, return empty comparison
        if not all_findings:
            return {
                'clusters': [],
                'agreement_score': 0,
                'contradiction_score': 0,
                'unique_findings': 0
            }
        
        # Compute embeddings for all findings
        texts = [finding['text'] for finding in all_findings]
        embeddings = self.sentence_transformer.encode(texts, convert_to_tensor=True)
        
        # Compute similarity matrix
        similarity_matrix = util.pytorch_cos_sim(embeddings, embeddings).numpy()
        
        # Cluster similar findings
        clusters = self._cluster_findings(all_findings, similarity_matrix)
        
        # Calculate agreement and contradiction scores
        agreement_score, contradiction_score = self._calculate_agreement_contradiction(clusters)
        
        # Prepare comparison results
        comparison = {
            'clusters': clusters,
            'agreement_score': agreement_score,
            'contradiction_score': contradiction_score,
            'unique_findings': len(clusters)
        }
        
        return comparison
    
    def _cluster_findings(self, findings: List[Dict], similarity_matrix: np.ndarray) -> List[Dict]:
        """
        Cluster similar findings
        
        Args:
            findings: List of finding dictionaries
            similarity_matrix: Matrix of similarity scores between findings
            
        Returns:
            List of cluster dictionaries
        """
        # Set similarity threshold
        threshold = 0.7
        
        # Initialize clusters
        clusters = []
        used_indices = set()
        
        # Cluster similar findings
        for i in range(len(findings)):
            if i in used_indices:
                continue
            
            # Find similar findings
            similar_indices = [j for j in range(len(findings)) 
                             if similarity_matrix[i, j] > threshold and j not in used_indices]
            
            # Create cluster
            cluster = {
                'findings': [findings[i]] + [findings[j] for j in similar_indices],
                'papers': set([findings[i]['paper_idx']] + [findings[j]['paper_idx'] for j in similar_indices]),
                'representative': findings[i]['text'],
                'size': 1 + len(similar_indices)
            }
            
            clusters.append(cluster)
            
            # Mark indices as used
            used_indices.add(i)
            used_indices.update(similar_indices)
        
        # Sort clusters by size
        clusters = sorted(clusters, key=lambda x: x['size'], reverse=True)
        
        return clusters
    
    def _calculate_agreement_contradiction(self, clusters: List[Dict]) -> Tuple[float, float]:
        """
        Calculate agreement and contradiction scores
        
        Args:
            clusters: List of cluster dictionaries
            
        Returns:
            Tuple of (agreement_score, contradiction_score)
        """
        # Calculate agreement score (proportion of findings that appear in multiple papers)
        multi_paper_clusters = [cluster for cluster in clusters if len(cluster['papers']) > 1]
        agreement_score = len(multi_paper_clusters) / len(clusters) if clusters else 0
        
        # Contradiction score is more complex and would require deeper semantic analysis
        # This is a simplified placeholder
        contradiction_score = 0.0
        
        return agreement_score, contradiction_score
    
    def compare_numerical_results(self, papers: List[Dict]) -> Dict:
        """
        Compare numerical results across papers
        
        Args:
            papers: List of paper dictionaries with findings
            
        Returns:
            Dictionary with comparison results
        """
        # Extract numerical results
        numerical_results = {}
        
        for paper_idx, paper in enumerate(papers):
            if 'findings' not in paper:
                continue
            
            for finding in paper['findings']:
                # Look for patterns like "accuracy of X%" or "F1 score of X"
                import re
                
                # Metrics to look for
                metrics = [
                    'accuracy', 'precision', 'recall', 'f1', 'f1 score',
                    'auc', 'roc', 'mae', 'mse', 'rmse', 'error rate'
                ]
                
                for metric in metrics:
                    pattern = rf'{metric}\s+(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?'
                    match = re.search(pattern, finding['text'], re.IGNORECASE)
                    
                    if match:
                        value = float(match.group(1))
                        
                        # Adjust percentage values
                        if '%' in match.group(0) or 'percent' in match.group(0).lower():
                            if value > 1:  # Assume it's already a percentage
                                value = value / 100
                        
                        if metric not in numerical_results:
                            numerical_results[metric] = []
                        
                        numerical_results[metric].append({
                            'paper_idx': paper_idx,
                            'value': value,
                            'text': finding['text']
                        })
        
        # Calculate statistics for each metric
        metric_stats = {}
        for metric, results in numerical_results.items():
            values = [r['value'] for r in results]
            
            if not values:
                continue
            
            metric_stats[metric] = {
                'min': min(values),
                'max': max(values),
                'mean': sum(values) / len(values),
                'std': np.std(values) if len(values) > 1 else 0,
                'count': len(values),
                'results': results
            }
        
        return {
            'metrics': metric_stats,
            'has_comparable_results': len(metric_stats) > 0
        }
    
    def identify_research_gaps(self, papers: List[Dict]) -> List[str]:
        """
        Identify potential research gaps based on paper analysis
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            List of potential research gaps
        """
        gaps = []
        
        # Check methodology coverage
        methodology_counts = {}
        for paper in papers:
            if 'methodologies' not in paper:
                continue
            
            for methodology, score in paper['methodologies'].items():
                if score > 0.3:
                    if methodology not in methodology_counts:
                        methodology_counts[methodology] = 0
                    methodology_counts[methodology] += 1
        
        # Identify underrepresented methodologies
        total_papers = len(papers)
        for methodology, count in methodology_counts.items():
            if count < total_papers * 0.2:  # Less than 20% of papers
                gaps.append(f"Limited research using {methodology} methodology")
        
        # Check for limitations mentioned in papers
        limitation_keywords = [
            'limitation', 'future work', 'further research', 'drawback',
            'shortcoming', 'constraint', 'challenge', 'open problem'
        ]
        
        for paper in papers:
            if 'findings' not in paper:
                continue
            
            for finding in paper['findings']:
                for keyword in limitation_keywords:
                    if keyword in finding['text'].lower():
                        gaps.append(f"Potential gap: {finding['text']}")
                        break
        
        # Identify contradictions as potential areas for further research
        if 'findings_comparison' in papers and 'contradiction_score' in papers['findings_comparison']:
            if papers['findings_comparison']['contradiction_score'] > 0.3:
                gaps.append("Contradictory findings suggest need for further research")
        
        return gaps
    
    def generate_comparison_matrix(self, papers: List[Dict]) -> Dict:
        """
        Generate a comparison matrix of papers
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            Dictionary with comparison matrix data
        """
        # Extract key attributes for comparison
        attributes = [
            'methodologies',
            'datasets',
            'metrics',
            'limitations',
            'future_work'
        ]
        
        # Initialize matrix
        matrix = {
            'papers': [paper.get('title', f"Paper {i}") for i, paper in enumerate(papers)],
            'attributes': {},
            'similarity': np.zeros((len(papers), len(papers)))
        }
        
        # Fill attribute data
        for attr in attributes:
            matrix['attributes'][attr] = []
            
            for paper in papers:
                if attr in paper:
                    matrix['attributes'][attr].append(paper[attr])
                else:
                    matrix['attributes'][attr].append(None)
        
        # Calculate paper similarity if sentence transformer is available
        if self.sentence_transformer:
            # Extract abstracts
            abstracts = [paper.get('abstract', '') for paper in papers]
            
            # Compute embeddings
            embeddings = self.sentence_transformer.encode(abstracts, convert_to_tensor=True)
            
            # Compute similarity matrix
            similarity_matrix = util.pytorch_cos_sim(embeddings, embeddings).numpy()
            
            matrix['similarity'] = similarity_matrix.tolist()
        
        return matrix
