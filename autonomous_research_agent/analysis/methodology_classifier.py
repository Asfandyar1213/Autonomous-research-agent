"""
Methodology Classifier Module

This module identifies and classifies research methodologies used in academic papers,
enabling comparison of approaches across different studies.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from autonomous_research_agent.core.exceptions import ModelError

logger = logging.getLogger(__name__)

class MethodologyClassifier:
    """
    Classifier for research methodologies
    """
    
    def __init__(self, use_transformer: bool = True):
        """
        Initialize the methodology classifier
        
        Args:
            use_transformer: Whether to use transformer model (True) or rule-based approach (False)
        """
        self.use_transformer = use_transformer
        self.classifier = None
        self.tokenizer = None
        
        # Methodology categories and associated keywords
        self.methodology_categories = {
            'quantitative': {
                'name': 'Quantitative Research',
                'description': 'Research that uses numerical data and statistical analysis',
                'keywords': [
                    'quantitative', 'statistical analysis', 'regression', 'correlation',
                    'survey', 'questionnaire', 'statistical significance', 'p-value',
                    'sample size', 'hypothesis testing', 'statistical model', 'variables',
                    'measurement', 'numerical data', 'statistical test', 'quantitative data',
                    'statistical method', 'anova', 't-test', 'chi-square'
                ]
            },
            'qualitative': {
                'name': 'Qualitative Research',
                'description': 'Research that uses non-numerical data and interpretive methods',
                'keywords': [
                    'qualitative', 'interview', 'focus group', 'ethnography', 'case study',
                    'thematic analysis', 'content analysis', 'discourse analysis', 'grounded theory',
                    'phenomenology', 'narrative', 'qualitative data', 'participant observation',
                    'field notes', 'textual analysis', 'interpretive', 'hermeneutic'
                ]
            },
            'mixed_methods': {
                'name': 'Mixed Methods Research',
                'description': 'Research that combines quantitative and qualitative approaches',
                'keywords': [
                    'mixed methods', 'mixed-methods', 'multi-method', 'triangulation',
                    'qualitative and quantitative', 'quantitative and qualitative',
                    'mixed approach', 'mixed research', 'integrated methods', 'combined methods'
                ]
            },
            'experimental': {
                'name': 'Experimental Research',
                'description': 'Research that manipulates variables to establish cause-effect relationships',
                'keywords': [
                    'experiment', 'experimental', 'control group', 'treatment group',
                    'random assignment', 'randomized', 'controlled experiment', 'manipulation',
                    'experimental condition', 'laboratory experiment', 'field experiment',
                    'quasi-experiment', 'experimental design', 'between-subjects', 'within-subjects'
                ]
            },
            'observational': {
                'name': 'Observational Research',
                'description': 'Research that observes subjects without intervention',
                'keywords': [
                    'observational', 'observation', 'naturalistic observation', 'field observation',
                    'longitudinal', 'cross-sectional', 'cohort study', 'case-control',
                    'prospective', 'retrospective', 'epidemiological', 'correlational',
                    'descriptive study', 'ecological study', 'observational data'
                ]
            },
            'review': {
                'name': 'Literature Review',
                'description': 'Research that synthesizes existing literature',
                'keywords': [
                    'literature review', 'systematic review', 'meta-analysis', 'scoping review',
                    'narrative review', 'integrative review', 'review of literature',
                    'critical review', 'state of the art', 'review article', 'survey paper',
                    'literature survey', 'systematic literature review', 'meta-synthesis'
                ]
            },
            'case_study': {
                'name': 'Case Study',
                'description': 'In-depth analysis of a specific case or instance',
                'keywords': [
                    'case study', 'case-study', 'case report', 'case analysis',
                    'case description', 'case series', 'case history', 'case method',
                    'single case', 'multiple case', 'collective case', 'instrumental case'
                ]
            },
            'simulation': {
                'name': 'Simulation Research',
                'description': 'Research using computational models to simulate phenomena',
                'keywords': [
                    'simulation', 'computer simulation', 'agent-based model', 'monte carlo',
                    'discrete event simulation', 'system dynamics', 'numerical simulation',
                    'computational model', 'mathematical model', 'stochastic model',
                    'simulation experiment', 'simulated data', 'simulation study'
                ]
            },
            'theoretical': {
                'name': 'Theoretical Research',
                'description': 'Research focused on developing or refining theories',
                'keywords': [
                    'theoretical', 'theory', 'conceptual framework', 'theoretical framework',
                    'conceptual model', 'theoretical model', 'theory development',
                    'theory building', 'conceptual analysis', 'philosophical analysis',
                    'theoretical analysis', 'conceptual paper', 'theoretical contribution'
                ]
            },
            'action_research': {
                'name': 'Action Research',
                'description': 'Research aimed at solving practical problems while generating knowledge',
                'keywords': [
                    'action research', 'participatory action research', 'community-based research',
                    'participatory research', 'action learning', 'collaborative inquiry',
                    'action science', 'cooperative inquiry', 'practitioner research',
                    'action inquiry', 'participatory rural appraisal'
                ]
            },
            'machine_learning': {
                'name': 'Machine Learning Research',
                'description': 'Research using machine learning techniques',
                'keywords': [
                    'machine learning', 'deep learning', 'neural network', 'supervised learning',
                    'unsupervised learning', 'reinforcement learning', 'classification',
                    'clustering', 'regression model', 'decision tree', 'random forest',
                    'support vector machine', 'svm', 'cnn', 'rnn', 'lstm', 'transformer',
                    'bert', 'gpt', 'gan', 'autoencoder', 'feature extraction'
                ]
            },
            'data_mining': {
                'name': 'Data Mining Research',
                'description': 'Research extracting patterns from large datasets',
                'keywords': [
                    'data mining', 'knowledge discovery', 'pattern recognition', 'big data',
                    'data analytics', 'text mining', 'web mining', 'association rules',
                    'frequent pattern mining', 'sequence mining', 'anomaly detection',
                    'outlier detection', 'data extraction', 'information extraction'
                ]
            }
        }
        
        # Initialize models if using transformer approach
        if self.use_transformer:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize transformer models for methodology classification"""
        try:
            # Initialize zero-shot classifier
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # Use CPU
            )
            
            logger.info("Initialized zero-shot classifier for methodology classification")
            
        except Exception as e:
            logger.error(f"Error initializing methodology classifier models: {str(e)}")
            logger.warning("Falling back to rule-based classification")
            self.use_transformer = False
    
    def classify_methodology(self, text: str) -> Dict[str, float]:
        """
        Classify the research methodology used in the text
        
        Args:
            text: Text to classify (typically methodology section or abstract)
            
        Returns:
            Dictionary mapping methodology categories to confidence scores
        """
        if self.use_transformer and self.classifier:
            return self._classify_with_transformer(text)
        else:
            return self._classify_with_rules(text)
    
    def _classify_with_transformer(self, text: str) -> Dict[str, float]:
        """
        Classify methodology using transformer model
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary mapping methodology categories to confidence scores
        """
        try:
            # Prepare candidate labels
            labels = list(self.methodology_categories.keys())
            
            # Truncate text if too long
            max_length = 1024
            words = text.split()
            if len(words) > max_length:
                text = ' '.join(words[:max_length])
            
            # Classify text
            result = self.classifier(
                text,
                labels,
                multi_label=True  # Allow multiple methodologies
            )
            
            # Convert to dictionary
            scores = {label: score for label, score in zip(result['labels'], result['scores'])}
            
            return scores
            
        except Exception as e:
            logger.error(f"Error classifying methodology with transformer: {str(e)}")
            logger.warning("Falling back to rule-based classification")
            return self._classify_with_rules(text)
    
    def _classify_with_rules(self, text: str) -> Dict[str, float]:
        """
        Classify methodology using rule-based approach
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary mapping methodology categories to confidence scores
        """
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Initialize scores
        scores = {category: 0.0 for category in self.methodology_categories}
        
        # Count keyword occurrences for each category
        for category, info in self.methodology_categories.items():
            keywords = info['keywords']
            
            # Count occurrences of each keyword
            count = 0
            for keyword in keywords:
                # Use word boundary to match whole words
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text_lower)
                count += len(matches)
            
            # Calculate score based on keyword occurrences
            # Normalize by number of keywords to avoid bias towards categories with more keywords
            if count > 0:
                scores[category] = min(1.0, count / (len(keywords) * 0.5))
        
        return scores
    
    def get_primary_methodology(self, text: str) -> Tuple[str, float]:
        """
        Get the primary methodology used in the text
        
        Args:
            text: Text to classify
            
        Returns:
            Tuple of (methodology_category, confidence_score)
        """
        # Classify methodology
        scores = self.classify_methodology(text)
        
        # Get category with highest score
        if not scores:
            return ('unknown', 0.0)
        
        primary_category = max(scores.items(), key=lambda x: x[1])
        return primary_category
    
    def get_methodology_details(self, category: str) -> Dict:
        """
        Get details about a methodology category
        
        Args:
            category: Methodology category
            
        Returns:
            Dictionary with category details
        """
        if category in self.methodology_categories:
            return self.methodology_categories[category]
        else:
            return {
                'name': 'Unknown Methodology',
                'description': 'Methodology could not be classified',
                'keywords': []
            }
    
    def extract_methodology_section(self, sections: Dict[str, str]) -> str:
        """
        Extract methodology section from paper sections
        
        Args:
            sections: Dictionary of paper sections
            
        Returns:
            Methodology section text
        """
        # Try different section names for methodology
        for section_name in ['methodology', 'methods', 'approach', 'experimental setup']:
            if section_name in sections and sections[section_name]:
                return sections[section_name]
        
        # If no methodology section found, try to extract from other sections
        if 'full_text' in sections and sections['full_text']:
            # Look for methodology subsection
            text = sections['full_text']
            
            # Try to find methodology section using regex
            methodology_patterns = [
                r'(?:^|\n)(?:3|III|3\.0)[\s\.]+(?:methodology|methods|approach).*?(?=(?:^|\n)(?:4|IV|4\.0))',
                r'(?:^|\n)(?:methodology|methods|approach)[\s\n]+(?:[^\n]+\n)+',
                r'(?:^|\n)(?:methodology|methods|approach)\s*\n+([^\n]+(?:\n+[^\n]+)*)'
            ]
            
            for pattern in methodology_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    return match.group(0)
        
        # If still not found, return empty string
        return ""
    
    def compare_methodologies(self, texts: List[str]) -> Dict:
        """
        Compare methodologies across multiple texts
        
        Args:
            texts: List of texts to compare
            
        Returns:
            Dictionary with comparison results
        """
        # Classify each text
        classifications = [self.classify_methodology(text) for text in texts]
        
        # Get primary methodology for each text
        primaries = [max(cls.items(), key=lambda x: x[1]) for cls in classifications]
        
        # Count occurrences of each methodology
        methodology_counts = {}
        for category, score in primaries:
            if category not in methodology_counts:
                methodology_counts[category] = 0
            methodology_counts[category] += 1
        
        # Calculate average scores for each methodology
        methodology_avg_scores = {}
        for category in self.methodology_categories:
            scores = [cls.get(category, 0.0) for cls in classifications]
            methodology_avg_scores[category] = sum(scores) / len(scores) if scores else 0.0
        
        # Prepare comparison results
        comparison = {
            'primary_methodologies': primaries,
            'methodology_counts': methodology_counts,
            'methodology_avg_scores': methodology_avg_scores,
            'most_common_methodology': max(methodology_counts.items(), key=lambda x: x[1]) if methodology_counts else None,
            'methodology_diversity': len([c for c, s in primaries if s > 0.3])
        }
        
        return comparison
