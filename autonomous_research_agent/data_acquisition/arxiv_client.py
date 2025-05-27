"""
arXiv API Client

This module provides a client for the arXiv API to search and retrieve
academic papers from the arXiv repository.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Union

import arxiv
import requests

from autonomous_research_agent.config.settings import settings
from autonomous_research_agent.core.exceptions import APIError
from autonomous_research_agent.data_acquisition.api_client import APIClient

logger = logging.getLogger(__name__)

class ArxivPaper:
    """Representation of a paper from arXiv"""
    
    def __init__(self, paper_data: Dict):
        """
        Initialize with paper data
        
        Args:
            paper_data: Dictionary containing paper metadata
        """
        self.id = paper_data.get('id', '')
        self.title = paper_data.get('title', '')
        self.abstract = paper_data.get('abstract', '')
        self.authors = paper_data.get('authors', [])
        self.published = paper_data.get('published')
        self.updated = paper_data.get('updated')
        self.doi = paper_data.get('doi')
        self.journal_ref = paper_data.get('journal_ref')
        self.categories = paper_data.get('categories', [])
        self.pdf_url = paper_data.get('pdf_url')
        self.primary_category = paper_data.get('primary_category')
        self.comment = paper_data.get('comment', '')
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'published': self.published.isoformat() if self.published else None,
            'updated': self.updated.isoformat() if self.updated else None,
            'doi': self.doi,
            'journal_ref': self.journal_ref,
            'categories': self.categories,
            'pdf_url': self.pdf_url,
            'primary_category': self.primary_category,
            'comment': self.comment,
            'source': 'arxiv'
        }


class ArxivClient(APIClient):
    """
    Client for the arXiv API
    
    Uses both the official arxiv Python package and direct API calls
    for more flexibility.
    """
    
    def __init__(self):
        """Initialize the arXiv client"""
        api_config = settings.apis.get('arxiv')
        if not api_config:
            raise ValueError("arXiv API configuration not found")
        
        super().__init__(api_config)
        
        # Initialize the arxiv package client
        self.client = arxiv.Client()
    
    def search(self, query: str, max_results: int = 50, 
               sort_by: str = arxiv.SortCriterion.Relevance,
               sort_order: str = arxiv.SortOrder.Descending) -> List[ArxivPaper]:
        """
        Search for papers on arXiv
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            sort_by: Sort criterion (Relevance, LastUpdatedDate, SubmittedDate)
            sort_order: Sort order (Ascending, Descending)
            
        Returns:
            List of ArxivPaper objects
        """
        logger.info(f"Searching arXiv for: {query}")
        
        try:
            # Create search object
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Execute search
            results = list(self.client.results(search))
            
            # Convert to ArxivPaper objects
            papers = []
            for result in results:
                paper_data = {
                    'id': result.entry_id.split('/')[-1],
                    'title': result.title,
                    'abstract': result.summary,
                    'authors': [author.name for author in result.authors],
                    'published': result.published,
                    'updated': result.updated,
                    'doi': result.doi,
                    'journal_ref': result.journal_ref,
                    'categories': result.categories,
                    'pdf_url': result.pdf_url,
                    'primary_category': result.primary_category,
                    'comment': result.comment
                }
                papers.append(ArxivPaper(paper_data))
            
            logger.info(f"Found {len(papers)} papers on arXiv")
            return papers
            
        except Exception as e:
            logger.error(f"Error searching arXiv: {str(e)}")
            raise APIError('arXiv', f"Search error: {str(e)}")
    
    def get_paper_by_id(self, paper_id: str) -> Optional[ArxivPaper]:
        """
        Get a paper by its arXiv ID
        
        Args:
            paper_id: arXiv paper ID (with or without version)
            
        Returns:
            ArxivPaper object or None if not found
        """
        logger.info(f"Fetching arXiv paper with ID: {paper_id}")
        
        # Clean ID format if needed
        paper_id = paper_id.strip()
        if paper_id.startswith('arXiv:'):
            paper_id = paper_id[6:]
        
        try:
            # Create search for specific paper
            search = arxiv.Search(
                id_list=[paper_id],
                max_results=1
            )
            
            # Execute search
            results = list(self.client.results(search))
            
            if not results:
                logger.warning(f"Paper with ID {paper_id} not found on arXiv")
                return None
            
            # Convert to ArxivPaper
            result = results[0]
            paper_data = {
                'id': result.entry_id.split('/')[-1],
                'title': result.title,
                'abstract': result.summary,
                'authors': [author.name for author in result.authors],
                'published': result.published,
                'updated': result.updated,
                'doi': result.doi,
                'journal_ref': result.journal_ref,
                'categories': result.categories,
                'pdf_url': result.pdf_url,
                'primary_category': result.primary_category,
                'comment': result.comment
            }
            
            return ArxivPaper(paper_data)
            
        except Exception as e:
            logger.error(f"Error fetching arXiv paper {paper_id}: {str(e)}")
            raise APIError('arXiv', f"Error fetching paper: {str(e)}")
    
    def download_pdf(self, paper_id: str, output_path: str) -> str:
        """
        Download PDF for a paper
        
        Args:
            paper_id: arXiv paper ID
            output_path: Path to save the PDF
            
        Returns:
            Path to the downloaded PDF
        """
        logger.info(f"Downloading PDF for arXiv paper {paper_id}")
        
        # Clean ID format if needed
        paper_id = paper_id.strip()
        if paper_id.startswith('arXiv:'):
            paper_id = paper_id[6:]
        
        # Get paper to get PDF URL
        paper = self.get_paper_by_id(paper_id)
        if not paper:
            raise APIError('arXiv', f"Paper {paper_id} not found")
        
        if not paper.pdf_url:
            raise APIError('arXiv', f"PDF URL not available for paper {paper_id}")
        
        try:
            # Download PDF
            response = requests.get(paper.pdf_url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"PDF downloaded to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF for paper {paper_id}: {str(e)}")
            raise APIError('arXiv', f"Error downloading PDF: {str(e)}")
    
    def search_by_category(self, category: str, max_results: int = 50,
                         date_from: Optional[str] = None,
                         date_to: Optional[str] = None) -> List[ArxivPaper]:
        """
        Search for papers in a specific category
        
        Args:
            category: arXiv category (e.g., 'cs.AI', 'physics.atom-ph')
            max_results: Maximum number of results to return
            date_from: Start date in format 'YYYYMMDD'
            date_to: End date in format 'YYYYMMDD'
            
        Returns:
            List of ArxivPaper objects
        """
        query = f"cat:{category}"
        
        # Add date range if specified
        if date_from or date_to:
            date_query = "submittedDate:"
            if date_from:
                date_query += f"[{date_from} TO "
            else:
                date_query += "* TO "
            
            if date_to:
                date_query += f"{date_to}]"
            else:
                date_query += "*]"
            
            query += f" AND {date_query}"
        
        return self.search(query, max_results=max_results)
    
    def get_recent_papers(self, category: Optional[str] = None, 
                        max_results: int = 50) -> List[ArxivPaper]:
        """
        Get recent papers, optionally filtered by category
        
        Args:
            category: arXiv category (optional)
            max_results: Maximum number of results to return
            
        Returns:
            List of ArxivPaper objects
        """
        query = ""
        if category:
            query = f"cat:{category}"
        
        return self.search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
