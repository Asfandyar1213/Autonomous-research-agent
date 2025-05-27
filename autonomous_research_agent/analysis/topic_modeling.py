"""
Topic Modeling Module

This module provides functionality to identify and analyze topics across research papers
using techniques like BERTopic, LDA, and other topic modeling approaches.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from transformers import pipeline

from autonomous_research_agent.core.exceptions import ModelError

logger = logging.getLogger(__name__)

class TopicModeler:
    """
    Topic modeling for research papers
    """
    
    def __init__(self, use_bertopic: bool = True):
        """
        Initialize the topic modeler
        
        Args:
            use_bertopic: Whether to use BERTopic (True) or LDA (False)
        """
        self.use_bertopic = use_bertopic
        self.model = None
        self.vectorizer = None
        self.topics = None
        self.topic_words = None
        self.topic_docs = None
    
    def fit(self, documents: List[str], num_topics: int = 10) -> Dict:
        """
        Fit topic model to documents
        
        Args:
            documents: List of document texts
            num_topics: Number of topics to extract
            
        Returns:
            Dictionary with topic model results
        """
        if self.use_bertopic:
            return self._fit_bertopic(documents, num_topics)
        else:
            return self._fit_lda(documents, num_topics)
    
    def _fit_bertopic(self, documents: List[str], num_topics: int) -> Dict:
        """
        Fit BERTopic model to documents
        
        Args:
            documents: List of document texts
            num_topics: Number of topics to extract
            
        Returns:
            Dictionary with topic model results
        """
        try:
            # Initialize BERTopic model
            self.model = BERTopic(
                nr_topics=num_topics,
                language="english",
                calculate_probabilities=True,
                verbose=True
            )
            
            # Fit model
            topics, probs = self.model.fit_transform(documents)
            
            # Store results
            self.topics = topics
            self.topic_words = self.model.get_topics()
            self.topic_docs = {}
            
            # Group documents by topic
            for i, topic in enumerate(topics):
                if topic not in self.topic_docs:
                    self.topic_docs[topic] = []
                self.topic_docs[topic].append(i)
            
            # Get topic info
            topic_info = self.model.get_topic_info()
            
            # Format results
            results = {
                'model_type': 'bertopic',
                'num_topics': len(self.topic_words),
                'topics': topics,
                'topic_words': {
                    topic: [word for word, score in words]
                    for topic, words in self.topic_words.items()
                    if topic != -1  # Skip outlier topic
                },
                'topic_docs': self.topic_docs,
                'topic_info': topic_info.to_dict('records')
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error fitting BERTopic model: {str(e)}")
            raise ModelError("BERTopic", f"Error fitting model: {str(e)}")
    
    def _fit_lda(self, documents: List[str], num_topics: int) -> Dict:
        """
        Fit LDA model to documents
        
        Args:
            documents: List of document texts
            num_topics: Number of topics to extract
            
        Returns:
            Dictionary with topic model results
        """
        try:
            from sklearn.decomposition import LatentDirichletAllocation
            
            # Initialize vectorizer
            self.vectorizer = CountVectorizer(
                max_df=0.95,
                min_df=2,
                stop_words='english'
            )
            
            # Transform documents to document-term matrix
            X = self.vectorizer.fit_transform(documents)
            
            # Initialize LDA model
            self.model = LatentDirichletAllocation(
                n_components=num_topics,
                max_iter=10,
                learning_method='online',
                random_state=42,
                batch_size=128,
                verbose=0
            )
            
            # Fit model
            self.model.fit(X)
            
            # Get feature names
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get top words for each topic
            self.topic_words = {}
            for topic_idx, topic in enumerate(self.model.components_):
                top_words_idx = topic.argsort()[:-11:-1]
                top_words = [(feature_names[i], topic[i]) for i in top_words_idx]
                self.topic_words[topic_idx] = top_words
            
            # Transform documents to get topic distributions
            doc_topic_dists = self.model.transform(X)
            
            # Assign topics to documents
            self.topics = doc_topic_dists.argmax(axis=1)
            
            # Group documents by topic
            self.topic_docs = {}
            for i, topic in enumerate(self.topics):
                if topic not in self.topic_docs:
                    self.topic_docs[topic] = []
                self.topic_docs[topic].append(i)
            
            # Format results
            results = {
                'model_type': 'lda',
                'num_topics': num_topics,
                'topics': self.topics.tolist(),
                'topic_words': {
                    topic: [word for word, score in words]
                    for topic, words in self.topic_words.items()
                },
                'topic_docs': {
                    str(topic): docs for topic, docs in self.topic_docs.items()
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error fitting LDA model: {str(e)}")
            raise ModelError("LDA", f"Error fitting model: {str(e)}")
    
    def get_document_topics(self, document: str) -> List[Tuple[int, float]]:
        """
        Get topic distribution for a new document
        
        Args:
            document: Document text
            
        Returns:
            List of (topic_id, probability) tuples
        """
        if self.model is None:
            raise ModelError("Topic Model", "Model not fitted")
        
        if self.use_bertopic:
            # Get topics for new document with BERTopic
            topics, probs = self.model.transform([document])
            
            # Get top topics with probabilities
            if len(probs) > 0:
                topic_probs = list(zip(topics[0], probs[0]))
                return sorted(topic_probs, key=lambda x: x[1], reverse=True)
            else:
                return []
        else:
            # Get topics for new document with LDA
            doc_vec = self.vectorizer.transform([document])
            topic_dist = self.model.transform(doc_vec)[0]
            
            # Get top topics with probabilities
            topic_probs = [(i, prob) for i, prob in enumerate(topic_dist)]
            return sorted(topic_probs, key=lambda x: x[1], reverse=True)
    
    def get_topic_keywords(self, topic_id: int, top_n: int = 10) -> List[str]:
        """
        Get top keywords for a topic
        
        Args:
            topic_id: Topic ID
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        if self.topic_words is None or topic_id not in self.topic_words:
            return []
        
        # Get top words for topic
        top_words = self.topic_words[topic_id][:top_n]
        
        # Return just the words (not scores)
        return [word for word, score in top_words]
    
    def get_topic_documents(self, topic_id: int) -> List[int]:
        """
        Get documents assigned to a topic
        
        Args:
            topic_id: Topic ID
            
        Returns:
            List of document indices
        """
        if self.topic_docs is None or topic_id not in self.topic_docs:
            return []
        
        return self.topic_docs[topic_id]
    
    def get_topic_coherence(self) -> float:
        """
        Calculate topic coherence score
        
        Returns:
            Coherence score
        """
        if self.model is None:
            raise ModelError("Topic Model", "Model not fitted")
        
        try:
            if self.use_bertopic:
                # BERTopic has built-in coherence calculation
                coherence = self.model.calculate_topic_coherence()
                return coherence
            else:
                # For LDA, we would need to implement coherence calculation
                # This is a simplified placeholder
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating topic coherence: {str(e)}")
            return 0.0
    
    def visualize_topics(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate topic visualization
        
        Args:
            output_path: Path to save visualization
            
        Returns:
            Path to saved visualization or None
        """
        if self.model is None:
            raise ModelError("Topic Model", "Model not fitted")
        
        try:
            if self.use_bertopic:
                # BERTopic has built-in visualization
                if output_path:
                    self.model.visualize_topics().write_html(output_path)
                    return output_path
                else:
                    # Return HTML as string if no output path
                    return self.model.visualize_topics().to_html()
            else:
                # For LDA, we would need to implement visualization
                # This is a simplified placeholder
                return None
                
        except Exception as e:
            logger.error(f"Error visualizing topics: {str(e)}")
            return None
