"""
Processing Manager Module

This module coordinates the processing of research papers, including document parsing,
text extraction, metadata extraction, and citation graph building.
"""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

import requests

from autonomous_research_agent.core.exceptions import DocumentProcessingError
from autonomous_research_agent.content_processing.document_parser import parse_document
from autonomous_research_agent.content_processing.text_extractor import TextExtractor
from autonomous_research_agent.content_processing.metadata_extractor import MetadataExtractor
from autonomous_research_agent.data_acquisition.acquisition_manager import Paper

logger = logging.getLogger(__name__)

class ProcessedPaper:
    """Representation of a processed research paper"""
    
    def __init__(self, paper: Paper):
        """
        Initialize with original paper
        
        Args:
            paper: Original paper from data acquisition
        """
        # Copy basic metadata from original paper
        self.id = paper.id
        self.title = paper.title
        self.abstract = paper.abstract
        self.authors = paper.authors
        self.year = paper.year
        self.venue = paper.venue
        self.doi = paper.doi
        self.url = paper.url
        self.pdf_url = paper.pdf_url
        self.source = paper.source
        self.source_id = paper.source_id
        self.keywords = paper.keywords
        self.categories = paper.categories
        self.citation_count = paper.citation_count
        
        # Content fields
        self.full_text = paper.full_text
        self.sections = {}
        self.structured_content = {}
        
        # Additional extracted metadata
        self.extracted_metadata = {}
        
        # Citation graph
        self.cited_papers = []
        self.citing_papers = []
        
        # Processing flags
        self.processed = False
        self.processing_errors = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'year': self.year,
            'venue': self.venue,
            'doi': self.doi,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'source': self.source,
            'source_id': self.source_id,
            'keywords': self.keywords,
            'categories': self.categories,
            'citation_count': self.citation_count,
            'sections': self.sections,
            'structured_content': self.structured_content,
            'extracted_metadata': self.extracted_metadata,
            'processed': self.processed,
            'processing_errors': self.processing_errors
        }


class ProcessingManager:
    """
    Manages the processing of research papers
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the processing manager
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.text_extractor = TextExtractor()
        self.metadata_extractor = MetadataExtractor()
    
    def process_papers(self, papers: List[Paper], 
                      max_workers: int = 5,
                      progress_callback: Optional[Callable[[int], None]] = None) -> List[ProcessedPaper]:
        """
        Process a list of papers
        
        Args:
            papers: List of papers to process
            max_workers: Maximum number of worker threads
            progress_callback: Callback function to report progress
            
        Returns:
            List of processed papers
        """
        logger.info(f"Processing {len(papers)} papers")
        
        processed_papers = []
        
        # Process papers in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit processing tasks
            future_to_paper = {
                executor.submit(self.process_paper, paper): paper
                for paper in papers
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_paper)):
                paper = future_to_paper[future]
                try:
                    # Get processed paper
                    processed_paper = future.result()
                    processed_papers.append(processed_paper)
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(1)
                        
                except Exception as e:
                    logger.error(f"Error processing paper {paper.id}: {str(e)}")
                    
                    # Create a processed paper with error
                    processed_paper = ProcessedPaper(paper)
                    processed_paper.processing_errors.append(str(e))
                    processed_papers.append(processed_paper)
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(1)
        
        logger.info(f"Processed {len(processed_papers)} papers")
        return processed_papers
    
    def process_paper(self, paper: Paper) -> ProcessedPaper:
        """
        Process a single paper
        
        Args:
            paper: Paper to process
            
        Returns:
            Processed paper
        """
        logger.info(f"Processing paper: {paper.id}")
        
        processed_paper = ProcessedPaper(paper)
        
        try:
            # Step 1: Get full text if not already available
            if not paper.full_text and paper.pdf_url:
                self._get_full_text(paper, processed_paper)
            elif paper.full_text:
                processed_paper.full_text = paper.full_text
            
            # Step 2: Parse document if full text is available
            if processed_paper.full_text:
                self._parse_document(processed_paper)
            
            # Step 3: Extract metadata
            self._extract_metadata(processed_paper)
            
            # Mark as processed
            processed_paper.processed = True
            
        except Exception as e:
            logger.error(f"Error processing paper {paper.id}: {str(e)}")
            processed_paper.processing_errors.append(str(e))
        
        return processed_paper
    
    def _get_full_text(self, paper: Paper, processed_paper: ProcessedPaper) -> None:
        """
        Get full text for a paper
        
        Args:
            paper: Original paper
            processed_paper: Processed paper to update
        """
        if not paper.pdf_url:
            logger.warning(f"No PDF URL available for paper {paper.id}")
            return
        
        try:
            # Create temporary file for PDF
            pdf_path = os.path.join(self.temp_dir, f"{paper.id.replace(':', '_')}.pdf")
            
            # Download PDF
            response = requests.get(paper.pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded PDF to {pdf_path}")
            
            # Parse PDF
            full_text, _ = parse_document(pdf_path)
            processed_paper.full_text = full_text
            
            # Clean up
            try:
                os.remove(pdf_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error getting full text for paper {paper.id}: {str(e)}")
            processed_paper.processing_errors.append(f"Full text extraction error: {str(e)}")
    
    def _parse_document(self, processed_paper: ProcessedPaper) -> None:
        """
        Parse document content
        
        Args:
            processed_paper: Processed paper to update
        """
        try:
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(processed_paper.full_text)
                temp_path = temp_file.name
            
            # Parse document
            _, sections = parse_document(temp_path)
            processed_paper.sections = sections
            
            # Extract structured content
            structured_content = self.text_extractor.structure_content(
                processed_paper.full_text, sections
            )
            processed_paper.structured_content = structured_content
            
            # Clean up
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error parsing document for paper {processed_paper.id}: {str(e)}")
            processed_paper.processing_errors.append(f"Document parsing error: {str(e)}")
    
    def _extract_metadata(self, processed_paper: ProcessedPaper) -> None:
        """
        Extract metadata from paper content
        
        Args:
            processed_paper: Processed paper to update
        """
        try:
            # Extract metadata from content if available
            if processed_paper.full_text:
                metadata = self.metadata_extractor.extract_metadata(
                    processed_paper.full_text,
                    processed_paper.structured_content
                )
                processed_paper.extracted_metadata = metadata
                
                # Update paper with extracted metadata if not already available
                if not processed_paper.keywords and 'keywords' in metadata:
                    processed_paper.keywords = metadata['keywords']
                
            # Extract metadata from abstract if full text not available
            elif processed_paper.abstract:
                metadata = self.metadata_extractor.extract_metadata_from_abstract(
                    processed_paper.abstract
                )
                processed_paper.extracted_metadata = metadata
                
                # Update paper with extracted metadata if not already available
                if not processed_paper.keywords and 'keywords' in metadata:
                    processed_paper.keywords = metadata['keywords']
                
        except Exception as e:
            logger.error(f"Error extracting metadata for paper {processed_paper.id}: {str(e)}")
            processed_paper.processing_errors.append(f"Metadata extraction error: {str(e)}")
