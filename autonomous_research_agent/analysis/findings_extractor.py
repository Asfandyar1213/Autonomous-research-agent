"""
Findings Extractor Module

This module extracts key findings, results, and conclusions from research papers,
enabling synthesis and comparison across multiple studies.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

import nltk
from nltk.tokenize import sent_tokenize
from transformers import pipeline

from autonomous_research_agent.core.exceptions import ModelError

logger = logging.getLogger(__name__)

class FindingsExtractor:
    """
    Extracts key findings and results from research papers
    """
    
    def __init__(self, use_transformer: bool = True):
        """
        Initialize the findings extractor
        
        Args:
            use_transformer: Whether to use transformer models (True) or rule-based approach (False)
        """
        self.use_transformer = use_transformer
        self.summarizer = None
        self.qa_model = None
        
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        # Initialize models if using transformer approach
        if self.use_transformer:
            self._initialize_models()
        
        # Patterns for finding statements
        self.finding_patterns = [
            r'(?:we|our|this study|this paper|this research|this work)\s+(?:found|show(?:s|ed)|demonstrat(?:e|es|ed)|indicat(?:e|es|ed)|reveal(?:s|ed)|confirm(?:s|ed)|identif(?:y|ies|ied))',
            r'(?:results|findings|data|analysis|experiments|observations)\s+(?:show|demonstrate|indicate|reveal|confirm|suggest)',
            r'(?:significant|important|key|main|major|critical)\s+(?:finding|result|outcome|discovery)',
            r'(?:we|our|this study|this paper|this research|this work)\s+(?:conclud(?:e|es|ed)|determin(?:e|es|ed))',
            r'(?:in conclusion|to conclude|to summarize|to sum up|in summary)',
            r'(?:the|our|main|key)\s+(?:contribution|achievement|advancement|improvement)'
        ]
        
        # Questions for QA model
        self.finding_questions = [
            "What are the main findings of this research?",
            "What are the key results of this study?",
            "What did the researchers discover?",
            "What are the main conclusions of this paper?",
            "What is the main contribution of this research?",
            "What is the significance of these findings?"
        ]
    
    def _initialize_models(self):
        """Initialize transformer models for findings extraction"""
        try:
            # Initialize summarizer
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1  # Use CPU
            )
            
            # Initialize QA model
            self.qa_model = pipeline(
                "question-answering",
                model="deepset/roberta-base-squad2",
                device=-1  # Use CPU
            )
            
            logger.info("Initialized transformer models for findings extraction")
            
        except Exception as e:
            logger.error(f"Error initializing findings extractor models: {str(e)}")
            logger.warning("Falling back to rule-based extraction")
            self.use_transformer = False
    
    def extract_findings(self, content: str, sections: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Extract key findings from paper content
        
        Args:
            content: Full paper content
            sections: Dictionary of paper sections
            
        Returns:
            List of findings with metadata
        """
        # First try to extract from results and conclusion sections
        findings = []
        
        # Extract from results section
        if 'results' in sections and sections['results']:
            results_findings = self._extract_from_section(
                sections['results'], 'results'
            )
            findings.extend(results_findings)
        
        # Extract from conclusion section
        if 'conclusion' in sections and sections['conclusion']:
            conclusion_findings = self._extract_from_section(
                sections['conclusion'], 'conclusion'
            )
            findings.extend(conclusion_findings)
        
        # If no findings extracted from specific sections, try abstract
        if not findings and 'abstract' in sections and sections['abstract']:
            abstract_findings = self._extract_from_section(
                sections['abstract'], 'abstract'
            )
            findings.extend(abstract_findings)
        
        # If still no findings, try full text
        if not findings and content:
            # Use a more aggressive approach with full text
            full_text_findings = self._extract_from_full_text(content)
            findings.extend(full_text_findings)
        
        # Deduplicate findings
        unique_findings = self._deduplicate_findings(findings)
        
        return unique_findings
    
    def _extract_from_section(self, section_text: str, section_name: str) -> List[Dict[str, str]]:
        """
        Extract findings from a specific section
        
        Args:
            section_text: Text of the section
            section_name: Name of the section
            
        Returns:
            List of findings with metadata
        """
        if self.use_transformer and self.summarizer and self.qa_model:
            return self._extract_with_transformer(section_text, section_name)
        else:
            return self._extract_with_rules(section_text, section_name)
    
    def _extract_with_transformer(self, text: str, section_name: str) -> List[Dict[str, str]]:
        """
        Extract findings using transformer models
        
        Args:
            text: Text to extract findings from
            section_name: Name of the section
            
        Returns:
            List of findings with metadata
        """
        findings = []
        
        try:
            # Truncate text if too long
            max_length = 1024
            words = text.split()
            if len(words) > max_length:
                text = ' '.join(words[:max_length])
            
            # Use QA model to extract findings
            for question in self.finding_questions:
                try:
                    answer = self.qa_model(
                        question=question,
                        context=text
                    )
                    
                    if answer and answer['score'] > 0.3:
                        findings.append({
                            'text': answer['answer'],
                            'confidence': answer['score'],
                            'source': section_name,
                            'extraction_method': 'qa_model'
                        })
                except Exception as e:
                    logger.warning(f"Error with QA model for question '{question}': {str(e)}")
            
            # Use summarizer to extract key points
            if len(text.split()) > 50:  # Only summarize if text is long enough
                try:
                    summary = self.summarizer(
                        text, 
                        max_length=150, 
                        min_length=30, 
                        do_sample=False
                    )
                    
                    summary_text = summary[0]['summary_text']
                    
                    # Split summary into sentences
                    summary_sentences = sent_tokenize(summary_text)
                    
                    for sentence in summary_sentences:
                        # Check if sentence looks like a finding
                        if self._is_finding_sentence(sentence):
                            findings.append({
                                'text': sentence,
                                'confidence': 0.8,  # Arbitrary confidence for summarizer
                                'source': section_name,
                                'extraction_method': 'summarizer'
                            })
                except Exception as e:
                    logger.warning(f"Error with summarizer: {str(e)}")
            
            return findings
            
        except Exception as e:
            logger.error(f"Error extracting findings with transformer: {str(e)}")
            logger.warning("Falling back to rule-based extraction")
            return self._extract_with_rules(text, section_name)
    
    def _extract_with_rules(self, text: str, section_name: str) -> List[Dict[str, str]]:
        """
        Extract findings using rule-based approach
        
        Args:
            text: Text to extract findings from
            section_name: Name of the section
            
        Returns:
            List of findings with metadata
        """
        findings = []
        
        # Split text into sentences
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            # Check if sentence contains finding patterns
            if self._is_finding_sentence(sentence):
                findings.append({
                    'text': sentence,
                    'confidence': 0.6,  # Arbitrary confidence for rule-based approach
                    'source': section_name,
                    'extraction_method': 'rule_based'
                })
        
        return findings
    
    def _is_finding_sentence(self, sentence: str) -> bool:
        """
        Check if a sentence contains finding patterns
        
        Args:
            sentence: Sentence to check
            
        Returns:
            True if sentence contains finding patterns, False otherwise
        """
        # Check if sentence matches any finding pattern
        for pattern in self.finding_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_from_full_text(self, content: str) -> List[Dict[str, str]]:
        """
        Extract findings from full text
        
        Args:
            content: Full text content
            
        Returns:
            List of findings with metadata
        """
        findings = []
        
        # Try to identify results and conclusion sections in full text
        results_pattern = r'(?:^|\n)(?:results|findings)(?:\s|:|\n)+(.*?)(?=(?:^|\n)(?:discussion|conclusion|references))'
        conclusion_pattern = r'(?:^|\n)(?:conclusion|conclusions|summary)(?:\s|:|\n)+(.*?)(?=(?:^|\n)(?:references|acknowledgments|bibliography))'
        
        # Extract results section
        results_match = re.search(results_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if results_match:
            results_text = results_match.group(1)
            results_findings = self._extract_from_section(results_text, 'results')
            findings.extend(results_findings)
        
        # Extract conclusion section
        conclusion_match = re.search(conclusion_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if conclusion_match:
            conclusion_text = conclusion_match.group(1)
            conclusion_findings = self._extract_from_section(conclusion_text, 'conclusion')
            findings.extend(conclusion_findings)
        
        # If still no findings, search for finding sentences in the entire text
        if not findings:
            # Split text into sentences
            sentences = sent_tokenize(content)
            
            for sentence in sentences:
                # Check if sentence contains finding patterns
                if self._is_finding_sentence(sentence):
                    findings.append({
                        'text': sentence,
                        'confidence': 0.4,  # Lower confidence for full text extraction
                        'source': 'full_text',
                        'extraction_method': 'rule_based'
                    })
        
        return findings
    
    def _deduplicate_findings(self, findings: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Deduplicate findings based on text similarity
        
        Args:
            findings: List of findings to deduplicate
            
        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []
        
        # Sort findings by confidence
        sorted_findings = sorted(findings, key=lambda x: x['confidence'], reverse=True)
        
        # Keep track of unique findings
        unique_findings = []
        finding_texts = set()
        
        for finding in sorted_findings:
            # Normalize text for comparison
            normalized_text = self._normalize_text(finding['text'])
            
            # Check if similar text already exists
            is_duplicate = False
            for existing_text in finding_texts:
                if self._is_similar(normalized_text, existing_text):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_findings.append(finding)
                finding_texts.add(normalized_text)
        
        return unique_findings
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _is_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """
        Check if two texts are similar
        
        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold
            
        Returns:
            True if texts are similar, False otherwise
        """
        # Simple Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return False
        
        similarity = len(intersection) / len(union)
        
        return similarity >= threshold
    
    def categorize_findings(self, findings: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Categorize findings by type
        
        Args:
            findings: List of findings to categorize
            
        Returns:
            Dictionary mapping categories to lists of findings
        """
        categories = {
            'results': [],
            'conclusions': [],
            'contributions': [],
            'limitations': [],
            'other': []
        }
        
        for finding in findings:
            text = finding['text'].lower()
            
            # Check for result patterns
            if re.search(r'(result|found|show|demonstrate|indicate|reveal)', text):
                categories['results'].append(finding)
            
            # Check for conclusion patterns
            elif re.search(r'(conclude|conclusion|summary|therefore|thus)', text):
                categories['conclusions'].append(finding)
            
            # Check for contribution patterns
            elif re.search(r'(contribution|advance|improve|enhance|novel|new)', text):
                categories['contributions'].append(finding)
            
            # Check for limitation patterns
            elif re.search(r'(limitation|drawback|shortcoming|constraint|future work)', text):
                categories['limitations'].append(finding)
            
            # Default to other
            else:
                categories['other'].append(finding)
        
        return categories
    
    def extract_numerical_results(self, findings: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Extract findings with numerical results
        
        Args:
            findings: List of findings
            
        Returns:
            List of findings with numerical results
        """
        numerical_findings = []
        
        # Pattern for numerical values with potential units or metrics
        numerical_pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:%|percent|p[<>=]\d+(?:\.\d+)?|±\s*\d+(?:\.\d+)?|accuracy|precision|recall|f1|auc|mae|mse|rmse))?'
        
        for finding in findings:
            text = finding['text']
            
            # Check if finding contains numerical values
            if re.search(numerical_pattern, text):
                numerical_findings.append(finding)
        
        return numerical_findings
    
    def extract_comparative_findings(self, findings: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Extract findings with comparative statements
        
        Args:
            findings: List of findings
            
        Returns:
            List of findings with comparative statements
        """
        comparative_findings = []
        
        # Pattern for comparative statements
        comparative_pattern = r'\b(better|worse|higher|lower|more|less|increase|decrease|improve|reduce|outperform|exceed|surpass|compared to|than|versus|vs\.)\b'
        
        for finding in findings:
            text = finding['text']
            
            # Check if finding contains comparative statements
            if re.search(comparative_pattern, text, re.IGNORECASE):
                comparative_findings.append(finding)
        
        return comparative_findings
    
    def summarize_findings(self, findings: List[Dict[str, str]], max_length: int = 3) -> str:
        """
        Generate a summary of key findings
        
        Args:
            findings: List of findings
            max_length: Maximum number of findings to include
            
        Returns:
            Summary text
        """
        if not findings:
            return "No findings extracted."
        
        # Sort findings by confidence
        sorted_findings = sorted(findings, key=lambda x: x['confidence'], reverse=True)
        
        # Select top findings
        top_findings = sorted_findings[:max_length]
        
        # Generate summary
        summary = "Key findings:\n\n"
        for i, finding in enumerate(top_findings, 1):
            summary += f"{i}. {finding['text']}\n"
        
        return summary
