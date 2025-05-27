"""
Base API Client

This module provides a base class for API clients with common functionality
such as rate limiting, retries, and error handling.
"""

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from autonomous_research_agent.config.settings import APIConfig
from autonomous_research_agent.core.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)

class APIClient:
    """
    Base class for API clients with common functionality
    """
    
    def __init__(self, api_config: APIConfig):
        """
        Initialize the API client with configuration
        
        Args:
            api_config: Configuration for the API
        """
        self.api_config = api_config
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.rate_limit = api_config.rate_limit
        self.timeout = api_config.timeout
        self.retry_attempts = api_config.retry_attempts
        self.retry_backoff = api_config.retry_backoff
        
        # Track request timestamps for rate limiting
        self.request_timestamps = []
        
        # Set up session with retry logic
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=self.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _check_rate_limit(self):
        """
        Check if we're within rate limits and wait if necessary
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        current_time = time.time()
        
        # Remove timestamps older than 60 seconds
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                  if current_time - ts < 60]
        
        # Check if we've hit the rate limit
        if len(self.request_timestamps) >= self.rate_limit:
            oldest_timestamp = min(self.request_timestamps)
            wait_time = 60 - (current_time - oldest_timestamp)
            
            if wait_time > 0:
                logger.warning(f"Rate limit reached for {self.api_config.name}, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        # Add current timestamp
        self.request_timestamps.append(current_time)
    
    def _handle_response(self, response: requests.Response, api_method: str) -> Dict[str, Any]:
        """
        Handle API response, checking for errors
        
        Args:
            response: The HTTP response
            api_method: The API method that was called
            
        Returns:
            Parsed response data
            
        Raises:
            RateLimitError: If rate limit was exceeded
            APIError: For other API errors
        """
        try:
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except ValueError:
                # Not JSON, return text content
                return {"content": response.text}
                
        except requests.exceptions.HTTPError as e:
            # Handle specific status codes
            if response.status_code == 429:
                # Rate limit exceeded
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        retry_after = int(retry_after)
                    except ValueError:
                        retry_after = None
                
                raise RateLimitError(self.api_config.name, retry_after)
            
            # Handle other HTTP errors
            error_msg = f"HTTP error {response.status_code}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    error_msg = f"{error_msg}: {error_data['error']}"
            except ValueError:
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:100]}"
            
            raise APIError(
                self.api_config.name,
                f"Error in {api_method}: {error_msg}",
                status_code=response.status_code,
                response=response
            )
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request to the API
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            Response data
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Check rate limit before making request
        self._check_rate_limit()
        
        # Add API key to parameters if available
        if self.api_key:
            params = params or {}
            params['api_key'] = self.api_key
        
        logger.debug(f"Making GET request to {url}")
        response = self.session.get(url, params=params, timeout=self.timeout)
        
        return self._handle_response(response, f"GET {endpoint}")
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, 
             json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a POST request to the API
        
        Args:
            endpoint: API endpoint to call
            data: Form data
            json_data: JSON data
            
        Returns:
            Response data
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Check rate limit before making request
        self._check_rate_limit()
        
        # Add API key to headers if available
        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        
        logger.debug(f"Making POST request to {url}")
        response = self.session.post(
            url, 
            data=data, 
            json=json_data, 
            headers=headers, 
            timeout=self.timeout
        )
        
        return self._handle_response(response, f"POST {endpoint}")
    
    def close(self):
        """Close the session"""
        self.session.close()
