"""
Data Acquisition Manager

This module coordinates the acquisition of research papers from multiple sources,
manages rate limiting, and handles error recovery.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from tqdm import tqdm

from autonomous_research_agent.config.settings import settings
from autonomous_research_agent.core.exceptions import APIError, RateLimitError
from autonomous_research_agent.core.query_processor import StructuredQuery
from autonomous_research_agent.data_acquisition.arxiv_client import ArxivClient, ArxivPaper
from autonomous_research_agent.data_acquisition.semantic_scholar import SemanticScholarClient, SemanticScholarPaper
from autonomous_research_agent.data_acquisition.pubmed_client import PubMedClient, PubMedPaper
from autonomous_research_agent.data_acquisition.crossref_client import CrossRefClient, CrossRefPaper

logger = logging.getLogger(__name__)

@dataclass
class Paper:
    """Unified representation of a research paper from any source"""
    
    # Basic metadata
    id: str
    title: str
    abstract: Optional[str] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    year: Optional[int] = None
    
    # Publication info
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    
    # Content
    full_text: Optional[str] = None
    
    # Source tracking
    source: str = ""
    source_id: Optional[str] = None
    
    # Additional metadata
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    citation_count: int = 0
    
    # Processing flags
    full_text_fetched: bool = False
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
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
            'full_text_fetched': self.full_text_fetched,
            'processed': self.processed
        }
    
    @classmethod
    def from_arxiv(cls, arxiv_paper: ArxivPaper) -> 'Paper':
        """Create a Paper from an ArxivPaper"""
        return cls(
            id=f"arxiv:{arxiv_paper.id}",
            title=arxiv_paper.title,
            abstract=arxiv_paper.abstract,
            authors=[{'name': author} for author in arxiv_paper.authors],
            year=arxiv_paper.published.year if arxiv_paper.published else None,
            doi=arxiv_paper.doi,
            url=f"https://arxiv.org/abs/{arxiv_paper.id}",
            pdf_url=arxiv_paper.pdf_url,
            source="arxiv",
            source_id=arxiv_paper.id,
            categories=arxiv_paper.categories
        )
    
    @classmethod
    def from_semantic_scholar(cls, ss_paper: SemanticScholarPaper) -> 'Paper':
        """Create a Paper from a SemanticScholarPaper"""
        return cls(
            id=f"s2:{ss_paper.paper_id}" if ss_paper.paper_id else f"s2:{ss_paper.corpus_id}",
            title=ss_paper.title,
            abstract=ss_paper.abstract,
            authors=[{'name': author.get('name', ''), 'id': author.get('authorId')} 
                    for author in ss_paper.authors],
            year=ss_paper.year,
            venue=ss_paper.venue,
            doi=ss_paper.doi,
            url=ss_paper.url or ss_paper.s2_url,
            pdf_url=ss_paper.pdf_url,
            source="semantic_scholar",
            source_id=ss_paper.paper_id,
            citation_count=ss_paper.citations_count,
            categories=ss_paper.fields_of_study
        )
    
    @classmethod
    def from_pubmed(cls, pubmed_paper: 'PubMedPaper') -> 'Paper':
        """Create a Paper from a PubMedPaper"""
        return cls(
            id=f"pubmed:{pubmed_paper.pmid}",
            title=pubmed_paper.title,
            abstract=pubmed_paper.abstract,
            authors=[{'name': author.get('name', ''), 'affiliation': author.get('affiliation')} 
                    for author in pubmed_paper.authors],
            year=pubmed_paper.publication_date.year if pubmed_paper.publication_date else None,
            venue=pubmed_paper.journal,
            doi=pubmed_paper.doi,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_paper.pmid}/",
            source="pubmed",
            source_id=pubmed_paper.pmid,
            keywords=pubmed_paper.keywords
        )
    
    @classmethod
    def from_crossref(cls, crossref_paper: 'CrossRefPaper') -> 'Paper':
        """Create a Paper from a CrossRefPaper"""
        return cls(
            id=f"doi:{crossref_paper.doi}" if crossref_paper.doi else f"crossref:{crossref_paper.id}",
            title=crossref_paper.title,
            abstract=crossref_paper.abstract,
            authors=[{'name': author.get('name', ''), 'affiliation': author.get('affiliation')} 
                    for author in crossref_paper.authors],
            year=crossref_paper.published_year,
            venue=crossref_paper.journal,
            doi=crossref_paper.doi,
            url=crossref_paper.url,
            source="crossref",
            source_id=crossref_paper.doi or crossref_paper.id
        )


class AcquisitionManager:
    """
    Manages the acquisition of research papers from multiple sources
    """
    
    def __init__(self, max_papers: int = 50, date_range: Optional[str] = None):
        """
        Initialize the acquisition manager
        
        Args:
            max_papers: Maximum number of papers to acquire
            date_range: Date range for papers (e.g., "2020-2023")
        """
        self.max_papers = max_papers
        self.date_range = date_range
        
        # Parse date range if provided
        self.start_year = None
        self.end_year = None
        if date_range:
            parts = date_range.split('-')
            if len(parts) == 2:
                self.start_year = parts[0].strip()
                self.end_year = parts[1].strip()
        
        # Initialize clients
        self.arxiv_client = ArxivClient()
        self.semantic_scholar_client = SemanticScholarClient()
        
        # Initialize optional clients if configured
        self.pubmed_client = None
        if 'pubmed' in settings.apis:
            from autonomous_research_agent.data_acquisition.pubmed_client import PubMedClient
            self.pubmed_client = PubMedClient()
        
        self.crossref_client = None
        if 'crossref' in settings.apis:
            from autonomous_research_agent.data_acquisition.crossref_client import CrossRefClient
            self.crossref_client = CrossRefClient()
        
        # Track papers by ID to avoid duplicates
        self.paper_ids = set()
    
    def acquire_papers(self, structured_query: StructuredQuery) -> List[Paper]:
        """
        Acquire papers from multiple sources based on the structured query
        
        Args:
            structured_query: Structured representation of the research query
            
        Returns:
            List of Paper objects
        """
        logger.info(f"Acquiring papers for query: {structured_query.original_query}")
        logger.info(f"Search terms: {structured_query.search_terms}")
        
        all_papers = []
        
        # Calculate papers per source based on max_papers
        papers_per_source = max(5, self.max_papers // 3)  # At least 5 papers per source
        
        # Acquire papers from arXiv
        arxiv_papers = self._get_arxiv_papers(structured_query, papers_per_source)
        all_papers.extend(arxiv_papers)
        logger.info(f"Acquired {len(arxiv_papers)} papers from arXiv")
        
        # Acquire papers from Semantic Scholar
        ss_papers = self._get_semantic_scholar_papers(structured_query, papers_per_source)
        all_papers.extend(ss_papers)
        logger.info(f"Acquired {len(ss_papers)} papers from Semantic Scholar")
        
        # Acquire papers from PubMed if available
        if self.pubmed_client and structured_query.domain in ['med', 'biology', 'chemistry']:
            pubmed_papers = self._get_pubmed_papers(structured_query, papers_per_source)
            all_papers.extend(pubmed_papers)
            logger.info(f"Acquired {len(pubmed_papers)} papers from PubMed")
        
        # Deduplicate papers
        unique_papers = self._deduplicate_papers(all_papers)
        logger.info(f"After deduplication: {len(unique_papers)} unique papers")
        
        # Enrich papers with additional metadata
        enriched_papers = self._enrich_papers(unique_papers)
        
        # Sort by relevance (currently using citation count as a proxy)
        sorted_papers = sorted(
            enriched_papers, 
            key=lambda p: (p.citation_count if p.citation_count else 0), 
            reverse=True
        )
        
        # Limit to max_papers
        result = sorted_papers[:self.max_papers]
        logger.info(f"Final paper count: {len(result)}")
        
        return result
    
    def _get_arxiv_papers(self, structured_query: StructuredQuery, max_results: int) -> List[Paper]:
        """Get papers from arXiv"""
        try:
            # Generate arXiv query
            arxiv_query = structured_query.get_arxiv_query()
            logger.debug(f"arXiv query: {arxiv_query}")
            
            # Search arXiv
            arxiv_results = self.arxiv_client.search(arxiv_query, max_results=max_results)
            
            # Convert to unified Paper objects
            papers = []
            for arxiv_paper in arxiv_results:
                paper = Paper.from_arxiv(arxiv_paper)
                
                # Skip if we already have this paper
                if paper.id in self.paper_ids:
                    continue
                
                self.paper_ids.add(paper.id)
                papers.append(paper)
            
            return papers
            
        except APIError as e:
            logger.error(f"Error getting papers from arXiv: {str(e)}")
            return []
    
    def _get_semantic_scholar_papers(self, structured_query: StructuredQuery, max_results: int) -> List[Paper]:
        """Get papers from Semantic Scholar"""
        try:
            # Generate Semantic Scholar query
            ss_query_params = structured_query.get_semantic_scholar_query()
            logger.debug(f"Semantic Scholar query: {ss_query_params}")
            
            # Search Semantic Scholar
            ss_results = self.semantic_scholar_client.search(
                query=ss_query_params['query'],
                limit=max_results,
                year=ss_query_params.get('year')
            )
            
            # Convert to unified Paper objects
            papers = []
            for ss_paper in ss_results:
                paper = Paper.from_semantic_scholar(ss_paper)
                
                # Skip if we already have this paper
                if paper.id in self.paper_ids:
                    continue
                
                self.paper_ids.add(paper.id)
                papers.append(paper)
            
            return papers
            
        except APIError as e:
            logger.error(f"Error getting papers from Semantic Scholar: {str(e)}")
            return []
    
    def _get_pubmed_papers(self, structured_query: StructuredQuery, max_results: int) -> List[Paper]:
        """Get papers from PubMed"""
        if not self.pubmed_client:
            return []
        
        try:
            # Generate PubMed query
            pubmed_query = structured_query.get_pubmed_query()
            logger.debug(f"PubMed query: {pubmed_query}")
            
            # Search PubMed
            pubmed_results = self.pubmed_client.search(pubmed_query, max_results=max_results)
            
            # Convert to unified Paper objects
            papers = []
            for pubmed_paper in pubmed_results:
                paper = Paper.from_pubmed(pubmed_paper)
                
                # Skip if we already have this paper
                if paper.id in self.paper_ids:
                    continue
                
                self.paper_ids.add(paper.id)
                papers.append(paper)
            
            return papers
            
        except APIError as e:
            logger.error(f"Error getting papers from PubMed: {str(e)}")
            return []
    
    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Deduplicate papers based on DOI, title similarity, etc.
        
        Args:
            papers: List of papers to deduplicate
            
        Returns:
            Deduplicated list of papers
        """
        # Track papers by DOI and title
        papers_by_doi = {}
        papers_by_title = {}
        unique_papers = []
        
        for paper in papers:
            # Check DOI first (most reliable)
            if paper.doi and paper.doi in papers_by_doi:
                # Merge information from both sources if needed
                existing_paper = papers_by_doi[paper.doi]
                self._merge_paper_info(existing_paper, paper)
                continue
            
            # Check title similarity
            title_key = self._normalize_title(paper.title)
            if title_key in papers_by_title:
                # Merge information from both sources if needed
                existing_paper = papers_by_title[title_key]
                self._merge_paper_info(existing_paper, paper)
                continue
            
            # New unique paper
            if paper.doi:
                papers_by_doi[paper.doi] = paper
            
            papers_by_title[title_key] = paper
            unique_papers.append(paper)
        
        return unique_papers
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        if not title:
            return ""
        
        # Convert to lowercase, remove punctuation and extra whitespace
        normalized = title.lower()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _merge_paper_info(self, target: Paper, source: Paper) -> None:
        """
        Merge information from source paper into target paper
        
        Args:
            target: Target paper to merge into
            source: Source paper to merge from
        """
        # Only update fields that are empty in target but present in source
        if not target.abstract and source.abstract:
            target.abstract = source.abstract
        
        if not target.year and source.year:
            target.year = source.year
        
        if not target.venue and source.venue:
            target.venue = source.venue
        
        if not target.doi and source.doi:
            target.doi = source.doi
        
        if not target.url and source.url:
            target.url = source.url
        
        if not target.pdf_url and source.pdf_url:
            target.pdf_url = source.pdf_url
        
        # Merge lists
        target.keywords = list(set(target.keywords + source.keywords))
        target.categories = list(set(target.categories + source.categories))
        
        # Use the highest citation count
        if source.citation_count > target.citation_count:
            target.citation_count = source.citation_count
    
    def _enrich_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Enrich papers with additional metadata from Semantic Scholar
        
        Args:
            papers: List of papers to enrich
            
        Returns:
            Enriched papers
        """
        logger.info(f"Enriching {len(papers)} papers with additional metadata")
        
        # Use ThreadPoolExecutor for parallel enrichment
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit enrichment tasks
            future_to_paper = {
                executor.submit(self._enrich_paper, paper): paper
                for paper in papers
            }
            
            # Process results as they complete
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    # Get enriched paper
                    enriched_paper = future.result()
                    # Replace original paper with enriched version
                    papers[papers.index(paper)] = enriched_paper
                except Exception as e:
                    logger.error(f"Error enriching paper {paper.id}: {str(e)}")
        
        return papers
    
    def _enrich_paper(self, paper: Paper) -> Paper:
        """
        Enrich a single paper with additional metadata
        
        Args:
            paper: Paper to enrich
            
        Returns:
            Enriched paper
        """
        try:
            # Skip if paper already has good metadata
            if paper.citation_count > 0 and paper.abstract:
                return paper
            
            # Try to get paper from Semantic Scholar
            ss_paper = None
            
            # Try DOI first
            if paper.doi:
                try:
                    ss_paper = self.semantic_scholar_client.get_paper(paper.doi)
                except APIError:
                    pass
            
            # Try arXiv ID if available
            if not ss_paper and paper.source == 'arxiv':
                try:
                    ss_paper = self.semantic_scholar_client.get_paper(paper.source_id)
                except APIError:
                    pass
            
            # If we found the paper on Semantic Scholar, update metadata
            if ss_paper:
                # Create a new paper from Semantic Scholar
                ss_unified_paper = Paper.from_semantic_scholar(ss_paper)
                
                # Merge with original paper
                self._merge_paper_info(paper, ss_unified_paper)
            
            return paper
            
        except Exception as e:
            logger.error(f"Error enriching paper {paper.id}: {str(e)}")
            return paper
    
    def get_paper_full_text(self, paper: Paper) -> Optional[str]:
        """
        Get full text for a paper
        
        Args:
            paper: Paper to get full text for
            
        Returns:
            Full text if available, None otherwise
        """
        logger.info(f"Getting full text for paper: {paper.id}")
        
        # Skip if already fetched
        if paper.full_text_fetched:
            return paper.full_text
        
        # Try to get PDF if URL is available
        if paper.pdf_url:
            try:
                # TODO: Implement PDF downloading and text extraction
                pass
            except Exception as e:
                logger.error(f"Error downloading PDF for paper {paper.id}: {str(e)}")
        
        # Mark as fetched even if unsuccessful to avoid repeated attempts
        paper.full_text_fetched = True
        
        return paper.full_text
