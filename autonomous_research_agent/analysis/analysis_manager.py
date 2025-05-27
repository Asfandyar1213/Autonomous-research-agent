"""
Analysis Manager Module

This module coordinates the analysis of research papers, including NLP processing,
topic modeling, methodology classification, findings extraction, and comparative analysis.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union

from autonomous_research_agent.core.exceptions import AnalysisError
from autonomous_research_agent.core.query_processor import StructuredQuery
from autonomous_research_agent.content_processing.processing_manager import ProcessedPaper
from autonomous_research_agent.analysis.nlp_pipeline import NLPPipeline
from autonomous_research_agent.analysis.topic_modeling import TopicModeler
from autonomous_research_agent.analysis.methodology_classifier import MethodologyClassifier
from autonomous_research_agent.analysis.findings_extractor import FindingsExtractor
from autonomous_research_agent.analysis.comparative_analysis import ComparativeAnalysis

logger = logging.getLogger(__name__)

class AnalysisManager:
    """
    Manages the analysis of research papers
    """
    
    def __init__(self):
        """Initialize the analysis manager"""
        self.nlp_pipeline = NLPPipeline()
        self.topic_modeler = TopicModeler()
        self.methodology_classifier = MethodologyClassifier()
        self.findings_extractor = FindingsExtractor()
        self.comparative_analysis = ComparativeAnalysis()
    
    def analyze(self, papers: List[ProcessedPaper], query: StructuredQuery) -> Dict:
        """
        Analyze a collection of research papers
        
        Args:
            papers: List of processed papers
            query: Structured query that initiated the research
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing {len(papers)} papers")
        
        try:
            # Step 1: Analyze individual papers
            analyzed_papers = self._analyze_papers(papers)
            
            # Step 2: Perform topic modeling
            topic_analysis = self._perform_topic_modeling(analyzed_papers)
            
            # Step 3: Compare methodologies
            methodology_comparison = self._compare_methodologies(analyzed_papers)
            
            # Step 4: Compare findings
            findings_comparison = self._compare_findings(analyzed_papers)
            
            # Step 5: Identify research gaps
            research_gaps = self.comparative_analysis.identify_research_gaps(analyzed_papers)
            
            # Step 6: Generate comparison matrix
            comparison_matrix = self.comparative_analysis.generate_comparison_matrix(analyzed_papers)
            
            # Combine all analysis results
            analysis_results = {
                'papers': analyzed_papers,
                'topic_analysis': topic_analysis,
                'methodology_comparison': methodology_comparison,
                'findings_comparison': findings_comparison,
                'research_gaps': research_gaps,
                'comparison_matrix': comparison_matrix,
                'query': query.to_dict()
            }
            
            logger.info("Analysis completed successfully")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing papers: {str(e)}")
            raise AnalysisError(f"Analysis failed: {str(e)}")
    
    def _analyze_papers(self, papers: List[ProcessedPaper]) -> List[Dict]:
        """
        Analyze individual papers
        
        Args:
            papers: List of processed papers
            
        Returns:
            List of dictionaries with paper analysis results
        """
        analyzed_papers = []
        
        for paper in papers:
            try:
                # Create base paper dictionary
                analyzed_paper = {
                    'id': paper.id,
                    'title': paper.title,
                    'abstract': paper.abstract,
                    'authors': paper.authors,
                    'year': paper.year,
                    'venue': paper.venue,
                    'doi': paper.doi,
                    'url': paper.url,
                    'source': paper.source,
                    'keywords': paper.keywords,
                    'categories': paper.categories,
                    'citation_count': paper.citation_count
                }
                
                # Extract entities from abstract
                if paper.abstract:
                    analyzed_paper['entities'] = self.nlp_pipeline.extract_entities(paper.abstract)
                
                # Classify methodology
                methodology_text = ""
                if paper.structured_content and 'methodology' in paper.structured_content:
                    methodology_text = paper.structured_content['methodology']
                elif paper.abstract:
                    methodology_text = paper.abstract
                
                if methodology_text:
                    analyzed_paper['methodologies'] = self.methodology_classifier.classify_methodology(methodology_text)
                    analyzed_paper['primary_methodology'] = self.methodology_classifier.get_primary_methodology(methodology_text)
                
                # Extract findings
                if paper.structured_content:
                    analyzed_paper['findings'] = self.findings_extractor.extract_findings(
                        paper.full_text or "", paper.sections
                    )
                    
                    # Categorize findings
                    if analyzed_paper['findings']:
                        analyzed_paper['categorized_findings'] = self.findings_extractor.categorize_findings(
                            analyzed_paper['findings']
                        )
                
                # Extract numerical results
                if 'findings' in analyzed_paper:
                    analyzed_paper['numerical_results'] = self.findings_extractor.extract_numerical_results(
                        analyzed_paper['findings']
                    )
                
                # Extract comparative findings
                if 'findings' in analyzed_paper:
                    analyzed_paper['comparative_findings'] = self.findings_extractor.extract_comparative_findings(
                        analyzed_paper['findings']
                    )
                
                # Add to analyzed papers
                analyzed_papers.append(analyzed_paper)
                
            except Exception as e:
                logger.error(f"Error analyzing paper {paper.id}: {str(e)}")
                # Add basic paper info even if analysis fails
                analyzed_papers.append({
                    'id': paper.id,
                    'title': paper.title,
                    'abstract': paper.abstract,
                    'authors': paper.authors,
                    'year': paper.year,
                    'analysis_error': str(e)
                })
        
        return analyzed_papers
    
    def _perform_topic_modeling(self, papers: List[Dict]) -> Dict:
        """
        Perform topic modeling on papers
        
        Args:
            papers: List of analyzed papers
            
        Returns:
            Dictionary with topic modeling results
        """
        # Extract text for topic modeling
        texts = []
        for paper in papers:
            if paper.get('abstract'):
                texts.append(paper['abstract'])
            else:
                # Use title as fallback
                texts.append(paper.get('title', ''))
        
        # Skip if no texts available
        if not texts:
            return {
                'success': False,
                'error': 'No text available for topic modeling'
            }
        
        try:
            # Fit topic model
            topic_results = self.topic_modeler.fit(texts, num_topics=min(5, len(texts)))
            
            # Add paper information to topics
            if 'topic_docs' in topic_results:
                for topic, doc_indices in topic_results['topic_docs'].items():
                    if isinstance(topic, int) or topic.isdigit():
                        topic_idx = int(topic)
                        topic_papers = [papers[i]['title'] for i in doc_indices if i < len(papers)]
                        topic_results.setdefault('topic_papers', {})[topic_idx] = topic_papers
            
            return {
                'success': True,
                'results': topic_results
            }
            
        except Exception as e:
            logger.error(f"Error performing topic modeling: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _compare_methodologies(self, papers: List[Dict]) -> Dict:
        """
        Compare methodologies across papers
        
        Args:
            papers: List of analyzed papers
            
        Returns:
            Dictionary with methodology comparison results
        """
        # Extract methodologies
        methodologies = []
        for paper in papers:
            if 'methodologies' in paper:
                methodologies.append(paper['methodologies'])
        
        # Skip if no methodologies available
        if not methodologies:
            return {
                'success': False,
                'error': 'No methodologies available for comparison'
            }
        
        try:
            # Compare methodologies
            comparison = self.comparative_analysis.compare_methodologies(methodologies)
            
            return {
                'success': True,
                'results': comparison
            }
            
        except Exception as e:
            logger.error(f"Error comparing methodologies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _compare_findings(self, papers: List[Dict]) -> Dict:
        """
        Compare findings across papers
        
        Args:
            papers: List of analyzed papers
            
        Returns:
            Dictionary with findings comparison results
        """
        # Extract findings
        findings_list = []
        for paper in papers:
            if 'findings' in paper:
                findings_list.append(paper['findings'])
            else:
                findings_list.append([])  # Empty list for papers without findings
        
        # Skip if no findings available
        if not any(findings_list):
            return {
                'success': False,
                'error': 'No findings available for comparison'
            }
        
        try:
            # Compare findings
            comparison = self.comparative_analysis.compare_findings(findings_list)
            
            # Compare numerical results
            numerical_comparison = self.comparative_analysis.compare_numerical_results(papers)
            
            return {
                'success': True,
                'results': comparison,
                'numerical_comparison': numerical_comparison
            }
            
        except Exception as e:
            logger.error(f"Error comparing findings: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
