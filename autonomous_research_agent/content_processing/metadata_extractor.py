"""
Metadata Extractor Module

This module extracts metadata from research papers, including author information,
publication details, keywords, and research methodologies.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Extracts metadata from research papers
    """
    
    def __init__(self):
        """Initialize the metadata extractor"""
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        # Patterns for extracting metadata
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        self.url_pattern = re.compile(r'https?://\S+')
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        
        # Research methodology patterns
        self.methodology_patterns = {
            'survey': [r'\bsurvey\b', r'\breview\b', r'\bmeta-analysis\b'],
            'experiment': [r'\bexperiment\b', r'\bcontrol group\b', r'\brandomized\b'],
            'case_study': [r'\bcase study\b', r'\bcase-study\b', r'\bcase series\b'],
            'simulation': [r'\bsimulation\b', r'\bmodel\b', r'\bemulate\b'],
            'qualitative': [r'\bqualitative\b', r'\binterview\b', r'\bethno\w+\b'],
            'quantitative': [r'\bquantitative\b', r'\bstatistic\w+\b', r'\bregression\b'],
            'mixed_methods': [r'\bmixed method\b', r'\bmulti-method\b'],
            'theoretical': [r'\btheoretical\b', r'\bframework\b', r'\bconcept\w+\b'],
            'machine_learning': [r'\bmachine learning\b', r'\bdeep learning\b', r'\bneural network\b'],
            'data_mining': [r'\bdata mining\b', r'\bcluster\w+\b', r'\bclassif\w+\b']
        }
    
    def extract_metadata(self, content: str, structured_content: Dict) -> Dict:
        """
        Extract metadata from paper content
        
        Args:
            content: Full paper content
            structured_content: Structured content from text extractor
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        # Extract emails
        metadata['emails'] = self._extract_emails(content)
        
        # Extract URLs
        metadata['urls'] = self._extract_urls(content)
        
        # Extract years
        metadata['years'] = self._extract_years(content)
        
        # Extract research methodologies
        metadata['methodologies'] = self._extract_methodologies(content)
        
        # Extract keywords if not already in structured content
        if 'keywords' not in structured_content or not structured_content['keywords']:
            metadata['keywords'] = self._extract_keywords(content)
        else:
            metadata['keywords'] = structured_content['keywords']
        
        # Extract dataset information
        metadata['datasets'] = self._extract_datasets(content)
        
        # Extract software/tools
        metadata['tools'] = self._extract_tools(content)
        
        # Extract funding information
        metadata['funding'] = self._extract_funding(content)
        
        return metadata
    
    def extract_metadata_from_abstract(self, abstract: str) -> Dict:
        """
        Extract metadata from paper abstract
        
        Args:
            abstract: Paper abstract
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        # Extract keywords
        metadata['keywords'] = self._extract_keywords(abstract)
        
        # Extract research methodologies
        metadata['methodologies'] = self._extract_methodologies(abstract)
        
        # Extract years
        metadata['years'] = self._extract_years(abstract)
        
        return metadata
    
    def _extract_emails(self, content: str) -> List[str]:
        """Extract email addresses from content"""
        emails = self.email_pattern.findall(content)
        return list(set(emails))
    
    def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from content"""
        urls = self.url_pattern.findall(content)
        return list(set(urls))
    
    def _extract_years(self, content: str) -> List[int]:
        """Extract years from content"""
        years = [int(y) for y in self.year_pattern.findall(content)]
        return list(set(years))
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from content
        
        This method looks for explicit keyword sections and falls back to
        extracting important terms if no explicit keywords are found.
        """
        # Try to find explicit keywords section
        keyword_section_pattern = re.compile(
            r'(keywords|key\s+words|index\s+terms)[\s\:]+([^\n\.]+)', 
            re.IGNORECASE
        )
        
        keyword_match = keyword_section_pattern.search(content)
        
        if keyword_match:
            # Extract keywords from explicit section
            keyword_text = keyword_match.group(2)
            
            # Split by common separators
            keywords = re.split(r'[,;]', keyword_text)
            
            # Clean up keywords
            keywords = [k.strip().lower() for k in keywords if k.strip()]
            
            return keywords
        
        # If no explicit keywords, extract important terms
        # This is a simplified implementation
        from collections import Counter
        import string
        
        # Tokenize and clean
        words = content.lower().split()
        words = [w.strip(string.punctuation) for w in words if len(w) > 3]
        
        # Remove common words
        try:
            from nltk.corpus import stopwords
            try:
                stop_words = set(stopwords.words('english'))
            except LookupError:
                nltk.download('stopwords', quiet=True)
                stop_words = set(stopwords.words('english'))
        except:
            # Fallback to a small set of common words
            stop_words = {'the', 'and', 'is', 'of', 'to', 'in', 'that', 'this', 'it', 'with', 'for', 'as', 'was', 'on', 'are', 'be', 'by', 'at', 'or', 'not'}
        
        words = [w for w in words if w not in stop_words]
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(10)]
        
        return keywords
    
    def _extract_methodologies(self, content: str) -> List[str]:
        """
        Extract research methodologies from content
        
        This method looks for methodology-related terms and classifies
        the research approach based on pattern matching.
        """
        methodologies = []
        content_lower = content.lower()
        
        # Check each methodology pattern
        for methodology, patterns in self.methodology_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    methodologies.append(methodology)
                    break
        
        return list(set(methodologies))
    
    def _extract_datasets(self, content: str) -> List[str]:
        """
        Extract dataset information from content
        
        This method looks for mentions of datasets in the content.
        """
        datasets = []
        
        # Look for dataset mentions
        dataset_patterns = [
            r'dataset\s+(?:called|named)?\s+["\']?([A-Za-z0-9\-_]+)["\']?',
            r'data\s+from\s+(?:the\s+)?["\']?([A-Za-z0-9\-_]+)["\']?',
            r'([A-Za-z0-9\-_]+)\s+dataset',
            r'([A-Za-z0-9\-_]+)\s+corpus'
        ]
        
        for pattern in dataset_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                dataset = match.group(1).strip()
                if len(dataset) > 2:  # Filter out very short matches
                    datasets.append(dataset)
        
        return list(set(datasets))
    
    def _extract_tools(self, content: str) -> List[str]:
        """
        Extract software/tools information from content
        
        This method looks for mentions of software tools in the content.
        """
        tools = []
        
        # Common software tools in research
        common_tools = [
            'Python', 'R', 'MATLAB', 'TensorFlow', 'PyTorch', 'Keras', 'scikit-learn',
            'SPSS', 'SAS', 'Stata', 'NLTK', 'spaCy', 'Pandas', 'NumPy', 'Jupyter',
            'GitHub', 'Git', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'LaTeX', 'Overleaf', 'Excel', 'Word', 'PowerPoint', 'Tableau', 'Power BI'
        ]
        
        # Look for tool mentions
        for tool in common_tools:
            if re.search(r'\b' + re.escape(tool) + r'\b', content, re.IGNORECASE):
                tools.append(tool)
        
        # Look for tool mentions with version numbers
        tool_version_pattern = r'([A-Za-z][A-Za-z0-9\-_\.]+)\s+(?:version|v)?\.?\s*([0-9]+(?:\.[0-9]+)*)'
        matches = re.finditer(tool_version_pattern, content)
        
        for match in matches:
            tool = match.group(1).strip()
            version = match.group(2)
            if len(tool) > 2:  # Filter out very short matches
                tools.append(f"{tool} v{version}")
        
        return list(set(tools))
    
    def _extract_funding(self, content: str) -> List[str]:
        """
        Extract funding information from content
        
        This method looks for mentions of funding sources in the content.
        """
        funding_info = []
        
        # Look for funding acknowledgments
        funding_patterns = [
            r'(?:funded|supported|financed)\s+by\s+(?:the\s+)?([^\.]+)',
            r'(?:grant|award|contract)\s+(?:from|by)\s+(?:the\s+)?([^\.]+)',
            r'(?:financial\s+)?support\s+(?:from|by)\s+(?:the\s+)?([^\.]+)',
            r'(?:acknowledge|thank)(?:s|ing)?\s+(?:the\s+)?([^\.]+?)\s+for\s+(?:financial|funding)',
            r'(?:under|through)\s+(?:the\s+)?grant\s+(?:number|#)?\s+([A-Za-z0-9\-_\/]+)'
        ]
        
        for pattern in funding_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                funding = match.group(1).strip()
                if len(funding) > 5:  # Filter out very short matches
                    funding_info.append(funding)
        
        return list(set(funding_info))
