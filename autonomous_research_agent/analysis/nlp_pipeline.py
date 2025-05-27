"""
NLP Pipeline Module

This module provides natural language processing capabilities for analyzing
research papers, including text preprocessing, entity recognition, and semantic analysis.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union

import nltk
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from transformers import AutoModel, AutoTokenizer, pipeline

from autonomous_research_agent.config.settings import settings
from autonomous_research_agent.core.exceptions import ModelError

logger = logging.getLogger(__name__)

class NLPPipeline:
    """
    Natural Language Processing Pipeline for research paper analysis
    """
    
    def __init__(self):
        """Initialize the NLP pipeline"""
        self.spacy_model = None
        self.sentence_transformer = None
        self.summarizer = None
        self.zero_shot_classifier = None
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models"""
        try:
            # Initialize spaCy model
            try:
                self.spacy_model = spacy.load("en_core_web_lg")
                logger.info("Loaded spaCy model: en_core_web_lg")
            except OSError:
                # Try smaller model if large one is not available
                try:
                    self.spacy_model = spacy.load("en_core_web_md")
                    logger.info("Loaded spaCy model: en_core_web_md")
                except OSError:
                    # Try smallest model if medium one is not available
                    self.spacy_model = spacy.load("en_core_web_sm")
                    logger.info("Loaded spaCy model: en_core_web_sm")
            
            # Initialize NLTK resources
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            # Initialize transformers models if configured
            self._initialize_transformer_models()
            
        except Exception as e:
            logger.error(f"Error initializing NLP models: {str(e)}")
            raise ModelError("NLP Pipeline", f"Initialization error: {str(e)}")
    
    def _initialize_transformer_models(self):
        """Initialize transformer models"""
        try:
            # Initialize sentence transformer for semantic similarity
            from sentence_transformers import SentenceTransformer
            
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded Sentence Transformer model: all-MiniLM-L6-v2")
            
            # Initialize summarizer
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1  # Use CPU
            )
            logger.info("Loaded summarization model: facebook/bart-large-cnn")
            
            # Initialize zero-shot classifier
            self.zero_shot_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # Use CPU
            )
            logger.info("Loaded zero-shot classification model: facebook/bart-large-mnli")
            
        except Exception as e:
            logger.warning(f"Error initializing transformer models: {str(e)}")
            logger.warning("Some advanced NLP features may not be available")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for analysis
        
        Args:
            text: Text to preprocess
            
        Returns:
            Preprocessed text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dictionary mapping entity types to lists of entities
        """
        if not self.spacy_model:
            raise ModelError("NLP Pipeline", "spaCy model not initialized")
        
        # Process text with spaCy
        doc = self.spacy_model(text)
        
        # Extract entities
        entities = {}
        for ent in doc.ents:
            entity_type = ent.label_
            if entity_type not in entities:
                entities[entity_type] = []
            
            # Add entity if not already in list
            if ent.text not in entities[entity_type]:
                entities[entity_type].append(ent.text)
        
        return entities
    
    def extract_noun_phrases(self, text: str) -> List[str]:
        """
        Extract noun phrases from text
        
        Args:
            text: Text to extract noun phrases from
            
        Returns:
            List of noun phrases
        """
        if not self.spacy_model:
            raise ModelError("NLP Pipeline", "spaCy model not initialized")
        
        # Process text with spaCy
        doc = self.spacy_model(text)
        
        # Extract noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        
        # Remove duplicates
        noun_phrases = list(set(noun_phrases))
        
        return noun_phrases
    
    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        if not self.sentence_transformer:
            raise ModelError("NLP Pipeline", "Sentence Transformer model not initialized")
        
        # Encode texts
        embedding1 = self.sentence_transformer.encode(text1, convert_to_tensor=True)
        embedding2 = self.sentence_transformer.encode(text2, convert_to_tensor=True)
        
        # Compute cosine similarity
        from torch.nn import CosineSimilarity
        cos = CosineSimilarity(dim=0)
        similarity = cos(embedding1, embedding2).item()
        
        return similarity
    
    def compute_embeddings(self, texts: List[str]) -> List:
        """
        Compute embeddings for a list of texts
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of embeddings
        """
        if not self.sentence_transformer:
            raise ModelError("NLP Pipeline", "Sentence Transformer model not initialized")
        
        # Encode texts
        embeddings = self.sentence_transformer.encode(texts)
        
        return embeddings
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """
        Generate a summary of text
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length in tokens
            min_length: Minimum summary length in tokens
            
        Returns:
            Summary text
        """
        if not self.summarizer:
            raise ModelError("NLP Pipeline", "Summarizer model not initialized")
        
        # Check if text is too short to summarize
        if len(text.split()) < min_length:
            return text
        
        # Truncate text if too long for model
        max_input_length = 1024
        words = text.split()
        if len(words) > max_input_length:
            text = ' '.join(words[:max_input_length])
        
        # Generate summary
        summary = self.summarizer(
            text, 
            max_length=max_length, 
            min_length=min_length, 
            do_sample=False
        )
        
        return summary[0]['summary_text']
    
    def classify_text(self, text: str, labels: List[str]) -> Dict[str, float]:
        """
        Classify text into one or more categories
        
        Args:
            text: Text to classify
            labels: List of possible labels
            
        Returns:
            Dictionary mapping labels to confidence scores
        """
        if not self.zero_shot_classifier:
            raise ModelError("NLP Pipeline", "Zero-shot classifier not initialized")
        
        # Classify text
        result = self.zero_shot_classifier(text, labels)
        
        # Convert to dictionary
        scores = {label: score for label, score in zip(result['labels'], result['scores'])}
        
        return scores
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from text
        
        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to extract
            
        Returns:
            List of keywords
        """
        # Tokenize text
        words = word_tokenize(text.lower())
        
        # Remove stopwords and short words
        stop_words = set(stopwords.words('english'))
        words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
        
        # Count word frequencies
        from collections import Counter
        word_counts = Counter(words)
        
        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(top_n)]
        
        return keywords
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        try:
            # Initialize sentiment analyzer
            sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1  # Use CPU
            )
            
            # Analyze sentiment
            result = sentiment_analyzer(text)
            
            return {
                'label': result[0]['label'],
                'score': result[0]['score']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                'label': 'NEUTRAL',
                'score': 0.5
            }
