"""
Semantic Scholar API Client

This module provides a client for the Semantic Scholar API to search and retrieve
academic papers, author information, and citation data.
"""

import logging
from typing import Dict, List, Optional, Union

from autonomous_research_agent.config.settings import settings
from autonomous_research_agent.core.exceptions import APIError
from autonomous_research_agent.data_acquisition.api_client import APIClient

logger = logging.getLogger(__name__)

class SemanticScholarPaper:
    """Representation of a paper from Semantic Scholar"""
    
    def __init__(self, paper_data: Dict):
        """
        Initialize with paper data
        
        Args:
            paper_data: Dictionary containing paper metadata
        """
        self.paper_id = paper_data.get('paperId')
        self.corpus_id = paper_data.get('corpusId')
        self.external_ids = paper_data.get('externalIds', {})
        self.title = paper_data.get('title', '')
        self.abstract = paper_data.get('abstract', '')
        self.venue = paper_data.get('venue', '')
        self.year = paper_data.get('year')
        self.authors = paper_data.get('authors', [])
        self.citations_count = paper_data.get('citationCount', 0)
        self.citations = paper_data.get('citations', [])
        self.references = paper_data.get('references', [])
        self.url = paper_data.get('url')
        self.pdf_url = paper_data.get('openAccessPdf', {}).get('url')
        self.fields_of_study = paper_data.get('fieldsOfStudy', [])
        self.s2_url = paper_data.get('s2Url')
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            'id': self.paper_id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': [author.get('name', '') for author in self.authors],
            'year': self.year,
            'venue': self.venue,
            'citations_count': self.citations_count,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'fields_of_study': self.fields_of_study,
            'external_ids': self.external_ids,
            'source': 'semantic_scholar'
        }
    
    @property
    def doi(self) -> Optional[str]:
        """Get DOI if available"""
        return self.external_ids.get('DOI')
    
    @property
    def arxiv_id(self) -> Optional[str]:
        """Get arXiv ID if available"""
        return self.external_ids.get('ArXiv')


class SemanticScholarClient(APIClient):
    """
    Client for the Semantic Scholar API
    """
    
    def __init__(self):
        """Initialize the Semantic Scholar client"""
        api_config = settings.apis.get('semantic_scholar')
        if not api_config:
            raise ValueError("Semantic Scholar API configuration not found")
        
        super().__init__(api_config)
    
    def search(self, query: str, limit: int = 100, fields: Optional[List[str]] = None,
              year: Optional[str] = None, venue: Optional[str] = None) -> List[SemanticScholarPaper]:
        """
        Search for papers on Semantic Scholar
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            fields: Fields to include in the response
            year: Year filter (e.g., "2020" or "2018-2022")
            venue: Venue filter
            
        Returns:
            List of SemanticScholarPaper objects
        """
        logger.info(f"Searching Semantic Scholar for: {query}")
        
        # Default fields if not specified
        if fields is None:
            fields = [
                "paperId", "corpusId", "externalIds", "title", "abstract", 
                "venue", "year", "authors", "citationCount", "openAccessPdf",
                "fieldsOfStudy", "s2Url", "url"
            ]
        
        # Build parameters
        params = {
            "query": query,
            "limit": min(limit, 100),  # API maximum is 100
            "fields": ",".join(fields)
        }
        
        # Add optional filters
        if year:
            params["year"] = year
        
        if venue:
            params["venue"] = venue
        
        try:
            # Make API request
            response = self.get("paper/search", params=params)
            
            # Extract papers from response
            papers = []
            if "data" in response:
                for paper_data in response["data"]:
                    papers.append(SemanticScholarPaper(paper_data))
            
            logger.info(f"Found {len(papers)} papers on Semantic Scholar")
            return papers
            
        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {str(e)}")
            raise APIError('Semantic Scholar', f"Search error: {str(e)}")
    
    def get_paper(self, paper_id: str, fields: Optional[List[str]] = None) -> Optional[SemanticScholarPaper]:
        """
        Get a paper by its Semantic Scholar ID, DOI, arXiv ID, etc.
        
        Args:
            paper_id: Paper identifier (S2 ID, DOI, arXiv ID, etc.)
            fields: Fields to include in the response
            
        Returns:
            SemanticScholarPaper object or None if not found
        """
        logger.info(f"Fetching paper with ID: {paper_id}")
        
        # Default fields if not specified
        if fields is None:
            fields = [
                "paperId", "corpusId", "externalIds", "title", "abstract", 
                "venue", "year", "authors", "citationCount", "openAccessPdf",
                "fieldsOfStudy", "s2Url", "url"
            ]
        
        # Determine ID type
        if paper_id.startswith("10."):
            # Looks like a DOI
            endpoint = f"paper/DOI:{paper_id}"
        elif paper_id.lower().startswith("arxiv:"):
            # arXiv ID with prefix
            endpoint = f"paper/ArXiv:{paper_id[6:]}"
        elif paper_id.find(".") > 0 and paper_id[0].isdigit():
            # Likely an arXiv ID without prefix
            endpoint = f"paper/ArXiv:{paper_id}"
        elif paper_id.startswith("PMC"):
            # PubMed Central ID
            endpoint = f"paper/PMC:{paper_id}"
        elif paper_id.isdigit():
            # PubMed ID
            endpoint = f"paper/PMID:{paper_id}"
        else:
            # Assume Semantic Scholar ID
            endpoint = f"paper/{paper_id}"
        
        # Build parameters
        params = {
            "fields": ",".join(fields)
        }
        
        try:
            # Make API request
            response = self.get(endpoint, params=params)
            
            # Check if paper was found
            if not response or response.get("error"):
                logger.warning(f"Paper with ID {paper_id} not found on Semantic Scholar")
                return None
            
            return SemanticScholarPaper(response)
            
        except Exception as e:
            logger.error(f"Error fetching paper {paper_id} from Semantic Scholar: {str(e)}")
            raise APIError('Semantic Scholar', f"Error fetching paper: {str(e)}")
    
    def get_paper_citations(self, paper_id: str, limit: int = 100, 
                          fields: Optional[List[str]] = None) -> List[SemanticScholarPaper]:
        """
        Get papers that cite the specified paper
        
        Args:
            paper_id: Paper identifier
            limit: Maximum number of citations to return
            fields: Fields to include in the response
            
        Returns:
            List of SemanticScholarPaper objects
        """
        logger.info(f"Fetching citations for paper: {paper_id}")
        
        # Default fields if not specified
        if fields is None:
            fields = [
                "paperId", "corpusId", "externalIds", "title", "abstract", 
                "venue", "year", "authors", "citationCount"
            ]
        
        # Build parameters
        params = {
            "limit": min(limit, 1000),  # API maximum is 1000
            "fields": ",".join(fields)
        }
        
        try:
            # Make API request
            endpoint = f"paper/{paper_id}/citations"
            response = self.get(endpoint, params=params)
            
            # Extract citations from response
            citations = []
            if "data" in response:
                for citation_data in response["data"]:
                    # The citation object has a 'citingPaper' field with the paper data
                    if "citingPaper" in citation_data:
                        citations.append(SemanticScholarPaper(citation_data["citingPaper"]))
            
            logger.info(f"Found {len(citations)} citations for paper {paper_id}")
            return citations
            
        except Exception as e:
            logger.error(f"Error fetching citations for paper {paper_id}: {str(e)}")
            raise APIError('Semantic Scholar', f"Error fetching citations: {str(e)}")
    
    def get_paper_references(self, paper_id: str, limit: int = 100,
                           fields: Optional[List[str]] = None) -> List[SemanticScholarPaper]:
        """
        Get papers referenced by the specified paper
        
        Args:
            paper_id: Paper identifier
            limit: Maximum number of references to return
            fields: Fields to include in the response
            
        Returns:
            List of SemanticScholarPaper objects
        """
        logger.info(f"Fetching references for paper: {paper_id}")
        
        # Default fields if not specified
        if fields is None:
            fields = [
                "paperId", "corpusId", "externalIds", "title", "abstract", 
                "venue", "year", "authors", "citationCount"
            ]
        
        # Build parameters
        params = {
            "limit": min(limit, 1000),  # API maximum is 1000
            "fields": ",".join(fields)
        }
        
        try:
            # Make API request
            endpoint = f"paper/{paper_id}/references"
            response = self.get(endpoint, params=params)
            
            # Extract references from response
            references = []
            if "data" in response:
                for reference_data in response["data"]:
                    # The reference object has a 'citedPaper' field with the paper data
                    if "citedPaper" in reference_data:
                        references.append(SemanticScholarPaper(reference_data["citedPaper"]))
            
            logger.info(f"Found {len(references)} references for paper {paper_id}")
            return references
            
        except Exception as e:
            logger.error(f"Error fetching references for paper {paper_id}: {str(e)}")
            raise APIError('Semantic Scholar', f"Error fetching references: {str(e)}")
    
    def get_author(self, author_id: str) -> Dict:
        """
        Get author information
        
        Args:
            author_id: Author identifier
            
        Returns:
            Author information
        """
        logger.info(f"Fetching author with ID: {author_id}")
        
        try:
            # Make API request
            endpoint = f"author/{author_id}"
            params = {
                "fields": "authorId,name,url,paperCount,citationCount,hIndex,affiliations,homepage"
            }
            
            response = self.get(endpoint, params=params)
            
            # Check if author was found
            if not response or response.get("error"):
                logger.warning(f"Author with ID {author_id} not found on Semantic Scholar")
                return {}
            
            return response
            
        except Exception as e:
            logger.error(f"Error fetching author {author_id} from Semantic Scholar: {str(e)}")
            raise APIError('Semantic Scholar', f"Error fetching author: {str(e)}")
    
    def get_author_papers(self, author_id: str, limit: int = 100,
                        fields: Optional[List[str]] = None) -> List[SemanticScholarPaper]:
        """
        Get papers by a specific author
        
        Args:
            author_id: Author identifier
            limit: Maximum number of papers to return
            fields: Fields to include in the response
            
        Returns:
            List of SemanticScholarPaper objects
        """
        logger.info(f"Fetching papers for author: {author_id}")
        
        # Default fields if not specified
        if fields is None:
            fields = [
                "paperId", "corpusId", "externalIds", "title", "abstract", 
                "venue", "year", "authors", "citationCount"
            ]
        
        # Build parameters
        params = {
            "limit": min(limit, 1000),  # API maximum is 1000
            "fields": ",".join(fields)
        }
        
        try:
            # Make API request
            endpoint = f"author/{author_id}/papers"
            response = self.get(endpoint, params=params)
            
            # Extract papers from response
            papers = []
            if "data" in response:
                for paper_data in response["data"]:
                    papers.append(SemanticScholarPaper(paper_data))
            
            logger.info(f"Found {len(papers)} papers for author {author_id}")
            return papers
            
        except Exception as e:
            logger.error(f"Error fetching papers for author {author_id}: {str(e)}")
            raise APIError('Semantic Scholar', f"Error fetching author papers: {str(e)}")
