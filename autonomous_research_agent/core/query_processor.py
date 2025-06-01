"""
Query Processor Module

This module is responsible for processing and refining research questions.
It extracts key concepts, identifies domain-specific terminology, and
transforms natural language questions into structured queries for academic APIs.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import spacy
from transformers import pipeline

from autonomous_research_agent.config.settings import settings
from autonomous_research_agent.core.exceptions import QueryProcessingError

logger = logging.getLogger(__name__)

@dataclass
class StructuredQuery:
    """Structured representation of a research query"""
    original_query: str
    search_terms: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    time_frame: Optional[Tuple[str, str]] = None
    key_concepts: List[str] = field(default_factory=list)
    excluded_terms: List[str] = field(default_factory=list)
    expanded_terms: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "original_query": self.original_query,
            "search_terms": self.search_terms,
            "domain": self.domain,
            "time_frame": self.time_frame,
            "key_concepts": self.key_concepts,
            "excluded_terms": self.excluded_terms,
            "expanded_terms": self.expanded_terms
        }
    
    def get_arxiv_query(self) -> str:
        """Generate a query string for arXiv API"""
        query_parts = []
        
        # Add main search terms
        if self.search_terms:
            terms = ' AND '.join([f'"{term}"' for term in self.search_terms])
            query_parts.append(f"all:({terms})")
        
        # Add domain if available
        if self.domain:
            query_parts.append(f"cat:{self.domain}")
        
        # Combine all parts
        query = ' AND '.join(query_parts)
        
        return query
    
    def get_semantic_scholar_query(self) -> Dict:
        """Generate query parameters for Semantic Scholar API"""
        query = {
            "query": ' '.join(self.search_terms),
            "limit": 100,
            "fields": "title,authors,year,abstract,venue,url,citations,references"
        }
        
        # Add year filter if time frame is specified
        if self.time_frame:
            start_year, end_year = self.time_frame
            if start_year and end_year:
                query["year"] = f"{start_year}-{end_year}"
        
        return query
    
    def get_pubmed_query(self) -> str:
        """Generate a query string for PubMed API"""
        query_parts = []
        
        # Add main search terms
        if self.search_terms:
            terms = ' AND '.join([f'"{term}"[Title/Abstract]' for term in self.search_terms])
            query_parts.append(f"({terms})")
        
        # Add date range if available
        if self.time_frame:
            start_year, end_year = self.time_frame
            if start_year and end_year:
                query_parts.append(f"({start_year}[PDAT]:{end_year}[PDAT])")
        
        # Combine all parts
        query = ' AND '.join(query_parts)
        
        return query


class QueryProcessor:
    """
    Processes natural language research questions and transforms them into
    structured queries suitable for academic search APIs.
    """
    
    def __init__(self):
        """Initialize the query processor with NLP models"""
        self.nlp = None
        self.zero_shot_classifier = None
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize NLP models for query processing"""
        # Flag to track if we're using fallback mechanisms
        self.using_fallback = False
        
        try:
            # Load spaCy model for NLP processing
            try:
                self.nlp = spacy.load("en_core_web_lg")
                logger.info("Loaded spaCy model: en_core_web_lg")
            except OSError:
                # Try smaller model if large model is not available
                try:
                    logger.warning("en_core_web_lg not found, trying en_core_web_md instead")
                    self.nlp = spacy.load("en_core_web_md")
                    logger.info("Loaded spaCy model: en_core_web_md")
                except OSError:
                    # Fall back to smallest model as last resort
                    logger.warning("en_core_web_md not found, trying en_core_web_sm instead")
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("Loaded spaCy model: en_core_web_sm")
                    self.using_fallback = True
            
            # Initialize zero-shot classifier for domain classification
            try:
                self.zero_shot_classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1  # Use CPU
                )
                logger.info("Initialized zero-shot classifier")
            except Exception as e:
                logger.warning(f"Error initializing zero-shot classifier: {str(e)}")
                self.zero_shot_classifier = None
                self.using_fallback = True
                
        except Exception as e:
            logger.warning(f"Error initializing NLP models: {str(e)}")
            self.nlp = None
            self.zero_shot_classifier = None
            self.using_fallback = True
            raise QueryProcessingError(f"Failed to initialize NLP models: {str(e)}")
    
    def process(self, query: str) -> StructuredQuery:
        """
        Process a natural language research question and convert it to a structured query
        
        Args:
            query: The research question to process
            
        Returns:
            A StructuredQuery object with extracted information
        """
        logger.info(f"Processing query: {query}")
        
        # Clean the query
        cleaned_query = self._clean_query(query)
        
        # Extract key concepts and search terms
        search_terms, key_concepts = self._extract_key_concepts(cleaned_query)
        
        # Identify domain
        domain = self._identify_domain(cleaned_query, key_concepts)
        
        # Extract time frame
        time_frame = self._extract_time_frame(cleaned_query)
        
        # Identify excluded terms
        excluded_terms = self._identify_excluded_terms(cleaned_query)
        
        # Expand search terms with related concepts
        expanded_terms = self._expand_search_terms(search_terms, domain)
        
        # Create structured query
        structured_query = StructuredQuery(
            original_query=query,
            search_terms=search_terms,
            domain=domain,
            time_frame=time_frame,
            key_concepts=key_concepts,
            excluded_terms=excluded_terms,
            expanded_terms=expanded_terms
        )
        
        logger.info(f"Processed query into structured format with {len(search_terms)} search terms")
        return structured_query
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query text"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', query).strip()
        
        # Remove special characters except those that might be meaningful
        cleaned = re.sub(r'[^\w\s\-\(\)\"\':]', ' ', cleaned)
        
        return cleaned
    
    def _extract_key_concepts(self, query: str) -> Tuple[List[str], List[str]]:
        """
        Extract key concepts and search terms from the query
        
        Returns:
            Tuple of (search_terms, key_concepts)
        """
        if not self.nlp:
            self.initialize_models()
        
        # Process the query with spaCy
        doc = self.nlp(query)
        
        # Extract noun phrases as key concepts
        noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        
        # Extract named entities
        entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART", "LAW", "LANGUAGE"]]
        
        # Extract important keywords (nouns, proper nouns, adjectives)
        keywords = [token.text for token in doc if (token.pos_ in ["NOUN", "PROPN"] and not token.is_stop)]
        
        # Combine and deduplicate
        all_concepts = list(set(noun_phrases + entities + keywords))
        
        # Filter out very short terms and common words
        filtered_concepts = [concept for concept in all_concepts if len(concept) > 3]
        
        # Select the most relevant terms for search
        search_terms = self._select_search_terms(filtered_concepts, query)
        
        return search_terms, filtered_concepts
    
    def _select_search_terms(self, concepts: List[str], query: str) -> List[str]:
        """
        Select the most relevant terms for search queries
        
        This uses a combination of:
        1. Term frequency in the query
        2. Term specificity (inverse document frequency proxy)
        3. Term position in the query
        """
        # Simple implementation: select terms that appear in the query
        # and prioritize longer, more specific phrases
        terms = sorted(concepts, key=lambda x: (-len(x.split()), query.lower().find(x.lower())))
        
        # Limit to a reasonable number of search terms
        return terms[:5]
    
    def _identify_domain(self, query: str, key_concepts: List[str]) -> Optional[str]:
        """
        Identify the academic domain most relevant to the query
        
        Returns:
            Domain identifier (e.g., "cs.AI", "physics.atom-ph") or None
        """
        if not self.zero_shot_classifier:
            self.initialize_models()
        
        # Define candidate domains
        domains = settings.allowed_domains
        
        # Combine query and key concepts for better classification
        classification_text = query
        if key_concepts:
            classification_text += " " + " ".join(key_concepts[:5])
        
        # Use zero-shot classification to identify domain
        try:
            result = self.zero_shot_classifier(classification_text, domains)
            top_domain = result["labels"][0]
            confidence = result["scores"][0]
            
            logger.debug(f"Domain classification: {top_domain} (confidence: {confidence:.2f})")
            
            # Only return domain if confidence is high enough
            if confidence > 0.5:
                # Map to API-specific domain codes
                domain_mapping = {
                    "computer_science": "cs",
                    "physics": "physics",
                    "mathematics": "math",
                    "biology": "q-bio",
                    "medicine": "med",
                    "chemistry": "chem",
                    "economics": "econ",
                    "psychology": "psych"
                }
                return domain_mapping.get(top_domain)
            
        except Exception as e:
            logger.warning(f"Error in domain classification: {str(e)}")
        
        return None
    
    def _extract_time_frame(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Extract time frame information from the query
        
        Returns:
            Tuple of (start_year, end_year) or None
        """
        # Look for year ranges like "2010-2020" or "between 2010 and 2020"
        year_range_pattern = r'(\d{4})\s*[-–—to]\s*(\d{4})'
        between_pattern = r'between\s+(\d{4})\s+and\s+(\d{4})'
        since_pattern = r'since\s+(\d{4})'
        
        # Check for year range
        range_match = re.search(year_range_pattern, query)
        if range_match:
            start_year, end_year = range_match.groups()
            return start_year, end_year
        
        # Check for "between X and Y" pattern
        between_match = re.search(between_pattern, query)
        if between_match:
            start_year, end_year = between_match.groups()
            return start_year, end_year
        
        # Check for "since X" pattern
        since_match = re.search(since_pattern, query)
        if since_match:
            start_year = since_match.group(1)
            import datetime
            current_year = str(datetime.datetime.now().year)
            return start_year, current_year
        
        return None
    
    def _identify_excluded_terms(self, query: str) -> List[str]:
        """
        Identify terms that should be excluded from search results
        
        Looks for patterns like "not X", "excluding Y", etc.
        """
        excluded = []
        
        # Look for exclusion patterns
        not_pattern = r'not\s+(\w+)'
        excluding_pattern = r'excluding\s+(\w+)'
        except_pattern = r'except\s+(\w+)'
        
        for pattern in [not_pattern, excluding_pattern, except_pattern]:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                excluded.append(match.group(1))
        
        return excluded
    
    def _expand_search_terms(self, search_terms: List[str], domain: Optional[str]) -> Dict[str, List[str]]:
        """
        Expand search terms with related concepts and synonyms
        
        Returns:
            Dictionary mapping original terms to lists of expanded terms
        """
        expanded_terms = {}
        
        # If NLP model isn't initialized, try to initialize it
        if not self.nlp:
            self.initialize_models()
            
        # If still no NLP model, return empty expansions
        if not self.nlp or self.using_fallback:
            logger.warning("Cannot expand search terms: NLP model not available or using fallback")
            return {term: [] for term in search_terms}
        
        try:
            for term in search_terms:
                # Get word vectors for term
                term_doc = self.nlp(term)
                
                # Skip terms that don't have vectors
                if not term_doc.has_vector:
                    expanded_terms[term] = []
                    continue
                
                # Find similar terms using word vectors
                similar_terms = []
                for word in self.nlp.vocab:
                    # Skip words without vectors or that are too short
                    if not word.has_vector or len(word.text) < 4:
                        continue
                    
                    # Calculate similarity
                    similarity = term_doc.similarity(word)
                    
                    # Add if similarity is high enough
                    if similarity > 0.7 and word.text.lower() != term.lower():
                        similar_terms.append(word.text)
                
                # Limit to top 3 similar terms
                expanded_terms[term] = similar_terms[:3]
        except Exception as e:
            logger.error(f"Error in search term expansion: {str(e)}")
            # Provide empty expansions as fallback
            expanded_terms = {term: [] for term in search_terms}
        
        return expanded_terms
