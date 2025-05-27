"""
Text Extractor Module

This module provides functionality to extract and clean text from different document sections,
identify key components like figures, tables, and equations, and structure the content.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

from autonomous_research_agent.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


class TextExtractor:
    """
    Extracts and processes text from document content
    """
    
    def __init__(self):
        """Initialize the text extractor"""
        # Common patterns to identify and clean
        self.figure_pattern = re.compile(r'(figure|fig\.?)\s+\d+', re.IGNORECASE)
        self.table_pattern = re.compile(r'(table)\s+\d+', re.IGNORECASE)
        self.equation_pattern = re.compile(r'(equation|eq\.?)\s+\d+', re.IGNORECASE)
        self.citation_pattern = re.compile(r'\[\d+(?:,\s*\d+)*\]|\(\w+\s+et\s+al\.\s*,\s*\d{4}\)')
        self.reference_pattern = re.compile(r'^\[\d+\]\s+', re.MULTILINE)
    
    def extract_clean_text(self, content: str) -> str:
        """
        Extract and clean text from document content
        
        Args:
            content: Raw document content
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', content)
        
        # Remove page numbers
        text = re.sub(r'\s*\-\s*\d+\s*\-\s*', ' ', text)
        
        # Remove headers and footers (simplified approach)
        text = re.sub(r'^\s*.{0,50}$', '', text, flags=re.MULTILINE)
        
        # Clean up the text
        text = text.strip()
        
        return text
    
    def extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text
        
        Args:
            text: Text to extract sentences from
            
        Returns:
            List of sentences
        """
        # Use NLTK's sentence tokenizer
        sentences = sent_tokenize(text)
        
        # Filter out very short sentences (likely noise)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences
    
    def extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract paragraphs from text
        
        Args:
            text: Text to extract paragraphs from
            
        Returns:
            List of paragraphs
        """
        # Split by double newlines or more
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Filter out very short paragraphs (likely noise)
        paragraphs = [p for p in paragraphs if len(p) > 30]
        
        return paragraphs
    
    def extract_section_text(self, sections: Dict[str, str], section_name: str) -> str:
        """
        Extract text from a specific section
        
        Args:
            sections: Dictionary of section names to content
            section_name: Name of section to extract
            
        Returns:
            Cleaned section text
        """
        if section_name not in sections:
            logger.warning(f"Section '{section_name}' not found in document")
            return ""
        
        # Get section text
        section_text = sections[section_name]
        
        # Clean section text
        section_text = self.extract_clean_text(section_text)
        
        return section_text
    
    def extract_abstract(self, sections: Dict[str, str]) -> str:
        """
        Extract abstract from document sections
        
        Args:
            sections: Dictionary of section names to content
            
        Returns:
            Abstract text
        """
        # Try to get abstract from sections
        if 'abstract' in sections:
            return self.extract_section_text(sections, 'abstract')
        
        # If no abstract section, try to find it in the preamble
        if 'preamble' in sections:
            preamble = sections['preamble']
            
            # Look for "Abstract" header
            abstract_match = re.search(r'abstract\s*\n(.*?)(?:\n\s*\n|\Z)', 
                                     preamble, re.IGNORECASE | re.DOTALL)
            
            if abstract_match:
                return self.extract_clean_text(abstract_match.group(1))
        
        logger.warning("Abstract not found in document")
        return ""
    
    def extract_introduction(self, sections: Dict[str, str]) -> str:
        """
        Extract introduction from document sections
        
        Args:
            sections: Dictionary of section names to content
            
        Returns:
            Introduction text
        """
        # Try to get introduction from sections
        if 'introduction' in sections:
            return self.extract_section_text(sections, 'introduction')
        
        logger.warning("Introduction not found in document")
        return ""
    
    def extract_methodology(self, sections: Dict[str, str]) -> str:
        """
        Extract methodology from document sections
        
        Args:
            sections: Dictionary of section names to content
            
        Returns:
            Methodology text
        """
        # Try different section names for methodology
        for section_name in ['methodology', 'methods', 'approach']:
            if section_name in sections:
                return self.extract_section_text(sections, section_name)
        
        logger.warning("Methodology not found in document")
        return ""
    
    def extract_results(self, sections: Dict[str, str]) -> str:
        """
        Extract results from document sections
        
        Args:
            sections: Dictionary of section names to content
            
        Returns:
            Results text
        """
        # Try different section names for results
        for section_name in ['results', 'results_and_discussion', 'evaluation']:
            if section_name in sections:
                return self.extract_section_text(sections, section_name)
        
        logger.warning("Results not found in document")
        return ""
    
    def extract_conclusion(self, sections: Dict[str, str]) -> str:
        """
        Extract conclusion from document sections
        
        Args:
            sections: Dictionary of section names to content
            
        Returns:
            Conclusion text
        """
        # Try different section names for conclusion
        for section_name in ['conclusion', 'conclusions']:
            if section_name in sections:
                return self.extract_section_text(sections, section_name)
        
        logger.warning("Conclusion not found in document")
        return ""
    
    def extract_figures(self, content: str) -> List[Dict[str, str]]:
        """
        Extract figure references from content
        
        Args:
            content: Document content
            
        Returns:
            List of figure information dictionaries
        """
        figures = []
        
        # Find all figure references
        figure_matches = self.figure_pattern.finditer(content)
        
        for match in figure_matches:
            # Get figure reference (e.g., "Figure 1")
            figure_ref = match.group(0)
            
            # Try to find caption
            caption_match = re.search(
                rf'{re.escape(figure_ref)}\.?\s*(.+?)\.(?:\s|$)', 
                content, 
                re.IGNORECASE
            )
            
            caption = caption_match.group(1) if caption_match else ""
            
            # Add figure information
            figures.append({
                'reference': figure_ref,
                'caption': caption
            })
        
        return figures
    
    def extract_tables(self, content: str) -> List[Dict[str, str]]:
        """
        Extract table references from content
        
        Args:
            content: Document content
            
        Returns:
            List of table information dictionaries
        """
        tables = []
        
        # Find all table references
        table_matches = self.table_pattern.finditer(content)
        
        for match in table_matches:
            # Get table reference (e.g., "Table 1")
            table_ref = match.group(0)
            
            # Try to find caption
            caption_match = re.search(
                rf'{re.escape(table_ref)}\.?\s*(.+?)\.(?:\s|$)', 
                content, 
                re.IGNORECASE
            )
            
            caption = caption_match.group(1) if caption_match else ""
            
            # Add table information
            tables.append({
                'reference': table_ref,
                'caption': caption
            })
        
        return tables
    
    def extract_equations(self, content: str) -> List[Dict[str, str]]:
        """
        Extract equation references from content
        
        Args:
            content: Document content
            
        Returns:
            List of equation information dictionaries
        """
        equations = []
        
        # Find all equation references
        equation_matches = self.equation_pattern.finditer(content)
        
        for match in equation_matches:
            # Get equation reference (e.g., "Equation 1")
            equation_ref = match.group(0)
            
            # Add equation information
            equations.append({
                'reference': equation_ref
            })
        
        return equations
    
    def extract_citations(self, content: str) -> Set[str]:
        """
        Extract citation references from content
        
        Args:
            content: Document content
            
        Returns:
            Set of citation references
        """
        # Find all citation references
        citation_matches = self.citation_pattern.findall(content)
        
        # Return unique citations
        return set(citation_matches)
    
    def extract_keywords(self, content: str, top_n: int = 10) -> List[str]:
        """
        Extract potential keywords from content
        
        Args:
            content: Document content
            top_n: Number of top keywords to extract
            
        Returns:
            List of potential keywords
        """
        # Tokenize text
        words = word_tokenize(content.lower())
        
        # Remove stopwords and short words
        from nltk.corpus import stopwords
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords', quiet=True)
            stop_words = set(stopwords.words('english'))
        
        # Filter words
        filtered_words = [
            word for word in words 
            if word.isalpha() and word not in stop_words and len(word) > 3
        ]
        
        # Count word frequencies
        from collections import Counter
        word_counts = Counter(filtered_words)
        
        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(top_n)]
        
        return keywords
    
    def structure_content(self, content: str, sections: Dict[str, str]) -> Dict[str, str]:
        """
        Structure document content into a standardized format
        
        Args:
            content: Full document content
            sections: Dictionary of section names to content
            
        Returns:
            Structured content dictionary
        """
        structured_content = {
            'abstract': self.extract_abstract(sections),
            'introduction': self.extract_introduction(sections),
            'methodology': self.extract_methodology(sections),
            'results': self.extract_results(sections),
            'conclusion': self.extract_conclusion(sections),
            'figures': self.extract_figures(content),
            'tables': self.extract_tables(content),
            'equations': self.extract_equations(content),
            'citations': list(self.extract_citations(content)),
            'keywords': self.extract_keywords(content)
        }
        
        return structured_content
