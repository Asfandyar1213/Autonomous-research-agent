"""
Document Parser Module

This module provides functionality to parse different document formats (PDF, HTML, XML)
and extract structured content from research papers.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import PyPDF2
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as pdfminer_extract_text

from autonomous_research_agent.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)

class DocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> str:
        """
        Parse a document and extract its text content
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        pass
    
    @abstractmethod
    def extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from document content
        
        Args:
            content: Document content
            
        Returns:
            Dictionary mapping section names to content
        """
        pass


class PDFParser(DocumentParser):
    """Parser for PDF documents"""
    
    def __init__(self, use_pdfminer: bool = True):
        """
        Initialize PDF parser
        
        Args:
            use_pdfminer: Whether to use PDFMiner (more accurate but slower)
                         or PyPDF2 (faster but less accurate)
        """
        self.use_pdfminer = use_pdfminer
    
    def parse(self, file_path: Union[str, Path]) -> str:
        """
        Parse a PDF document and extract its text content
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentProcessingError("pdf", f"File not found: {file_path}")
        
        try:
            if self.use_pdfminer:
                # Use PDFMiner for better text extraction
                text = pdfminer_extract_text(file_path)
            else:
                # Use PyPDF2 (faster but less accurate)
                text = self._extract_with_pypdf2(file_path)
            
            # Clean up the extracted text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise DocumentProcessingError("pdf", f"Error parsing PDF: {str(e)}")
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2"""
        text = ""
        
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text"""
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove form feed characters
        text = text.replace('\f', '\n\n')
        
        # Remove non-printable characters
        text = ''.join(c for c in text if c.isprintable() or c in ['\n', '\t'])
        
        return text
    
    def extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from PDF content
        
        Args:
            content: PDF content
            
        Returns:
            Dictionary mapping section names to content
        """
        # Common section headers in academic papers
        section_patterns = [
            (r'abstract', 'abstract'),
            (r'introduction', 'introduction'),
            (r'related\s+work', 'related_work'),
            (r'background', 'background'),
            (r'methodology|methods', 'methodology'),
            (r'experiment(s|al setup)?', 'experiments'),
            (r'results(\s+and\s+discussion)?', 'results'),
            (r'discussion', 'discussion'),
            (r'conclusion(s)?', 'conclusion'),
            (r'reference(s)?|bibliography', 'references')
        ]
        
        sections = {}
        
        # Split content into lines
        lines = content.split('\n')
        
        # Find potential section headers
        current_section = 'preamble'
        sections[current_section] = []
        
        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern, section_name in section_patterns:
                if re.search(rf'^\s*(?:\d+\s*\.?\s*)?({pattern})\s*$', line.lower()):
                    current_section = section_name
                    sections[current_section] = []
                    is_header = True
                    break
            
            if not is_header:
                sections[current_section].append(line)
        
        # Join section content
        for section in sections:
            sections[section] = '\n'.join(sections[section])
        
        return sections


class HTMLParser(DocumentParser):
    """Parser for HTML documents"""
    
    def parse(self, file_path: Union[str, Path]) -> str:
        """
        Parse an HTML document and extract its text content
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            Extracted text content
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentProcessingError("html", f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Clean up the text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error parsing HTML {file_path}: {str(e)}")
            raise DocumentProcessingError("html", f"Error parsing HTML: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text"""
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Remove blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from HTML content
        
        Args:
            content: HTML content
            
        Returns:
            Dictionary mapping section names to content
        """
        # For HTML, we would typically use the document structure
        # This is a simplified implementation
        
        # Common section headers in academic papers
        section_patterns = [
            (r'abstract', 'abstract'),
            (r'introduction', 'introduction'),
            (r'related\s+work', 'related_work'),
            (r'background', 'background'),
            (r'methodology|methods', 'methodology'),
            (r'experiment(s|al setup)?', 'experiments'),
            (r'results(\s+and\s+discussion)?', 'results'),
            (r'discussion', 'discussion'),
            (r'conclusion(s)?', 'conclusion'),
            (r'reference(s)?|bibliography', 'references')
        ]
        
        sections = {}
        
        # Split content into lines
        lines = content.split('\n')
        
        # Find potential section headers
        current_section = 'preamble'
        sections[current_section] = []
        
        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern, section_name in section_patterns:
                if re.search(rf'^\s*(?:\d+\s*\.?\s*)?({pattern})\s*$', line.lower()):
                    current_section = section_name
                    sections[current_section] = []
                    is_header = True
                    break
            
            if not is_header:
                sections[current_section].append(line)
        
        # Join section content
        for section in sections:
            sections[section] = '\n'.join(sections[section])
        
        return sections


class XMLParser(DocumentParser):
    """Parser for XML documents"""
    
    def parse(self, file_path: Union[str, Path]) -> str:
        """
        Parse an XML document and extract its text content
        
        Args:
            file_path: Path to the XML file
            
        Returns:
            Extracted text content
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentProcessingError("xml", f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Parse XML with BeautifulSoup
            soup = BeautifulSoup(xml_content, 'xml')
            
            # Get text
            text = soup.get_text()
            
            # Clean up the text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error parsing XML {file_path}: {str(e)}")
            raise DocumentProcessingError("xml", f"Error parsing XML: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from XML content
        
        Args:
            content: XML content
            
        Returns:
            Dictionary mapping section names to content
        """
        # For XML, we would typically use the document structure
        # This is a simplified implementation
        return {'full_text': content}


def get_parser(file_path: Union[str, Path]) -> DocumentParser:
    """
    Get appropriate parser for a file based on its extension
    
    Args:
        file_path: Path to the file
        
    Returns:
        Appropriate DocumentParser instance
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if extension == '.pdf':
        return PDFParser()
    elif extension in ['.html', '.htm']:
        return HTMLParser()
    elif extension == '.xml':
        return XMLParser()
    else:
        raise ValueError(f"Unsupported file format: {extension}")


def parse_document(file_path: Union[str, Path]) -> Tuple[str, Dict[str, str]]:
    """
    Parse a document and extract its content and sections
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Tuple of (full_text, sections)
    """
    parser = get_parser(file_path)
    
    # Parse document
    content = parser.parse(file_path)
    
    # Extract sections
    sections = parser.extract_sections(content)
    
    return content, sections
