"""
Configuration settings for the Autonomous Research Agent
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class APIConfig(BaseModel):
    """Configuration for external API services"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = Field(default=60, description="Requests per minute")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_backoff: float = Field(default=2.0, description="Exponential backoff factor")

class ModelConfig(BaseModel):
    """Configuration for ML models"""
    name: str
    type: str
    path: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    
    @field_validator('type')
    @classmethod
    def validate_model_type(cls, v):
        allowed_types = ['local', 'huggingface', 'openai', 'custom']
        if v not in allowed_types:
            raise ValueError(f"Model type must be one of {allowed_types}")
        return v

class DatabaseConfig(BaseModel):
    """Configuration for database connections"""
    type: str
    connection_string: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    
    @field_validator('type')
    @classmethod
    def validate_db_type(cls, v):
        allowed_types = ['sqlite', 'postgresql', 'mysql']
        if v not in allowed_types:
            raise ValueError(f"Database type must be one of {allowed_types}")
        return v

class CacheConfig(BaseModel):
    """Configuration for caching system"""
    enabled: bool = True
    type: str = "memory"
    ttl: int = Field(default=3600, description="Time to live in seconds")
    max_size: int = Field(default=1000, description="Maximum number of items in cache")
    redis_url: Optional[str] = None
    
    @field_validator('type')
    @classmethod
    def validate_cache_type(cls, v):
        allowed_types = ['memory', 'redis', 'file']
        if v not in allowed_types:
            raise ValueError(f"Cache type must be one of {allowed_types}")
        return v

class LoggingConfig(BaseModel):
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    rotate: bool = True
    max_size: int = 10485760  # 10MB
    backup_count: int = 5
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v

class Settings(BaseSettings):
    """Main application settings"""
    # Application settings
    app_name: str = "Autonomous Research Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # API configurations
    apis: Dict[str, APIConfig] = Field(default_factory=dict)
    
    # Model configurations
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    
    # Database configuration
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(
        type="sqlite",
        connection_string="sqlite:///research_agent.db"
    ))
    
    # Cache configuration
    cache: CacheConfig = Field(default_factory=CacheConfig)
    
    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Research settings
    default_max_papers: int = 50
    default_search_depth: int = 2
    citation_format: str = "ieee"
    allowed_domains: List[str] = Field(default_factory=lambda: [
        "computer_science", "physics", "mathematics", "biology", 
        "medicine", "chemistry", "economics", "psychology"
    ])
    
    # File paths
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    cache_dir: Path = Field(default_factory=lambda: Path("cache"))
    output_dir: Path = Field(default_factory=lambda: Path("output"))
    
    # Class methods
    @classmethod
    def load_from_file(cls, config_path: Union[str, Path]) -> 'Settings':
        """Load settings from a YAML configuration file"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Process API configurations
        if 'apis' in config_data:
            config_data['apis'] = {
                name: APIConfig(**api_config)
                for name, api_config in config_data['apis'].items()
            }
        
        # Process model configurations
        if 'models' in config_data:
            config_data['models'] = {
                name: ModelConfig(**model_config)
                for name, model_config in config_data['models'].items()
            }
        
        # Process database configuration
        if 'database' in config_data:
            config_data['database'] = DatabaseConfig(**config_data['database'])
        
        # Process cache configuration
        if 'cache' in config_data:
            config_data['cache'] = CacheConfig(**config_data['cache'])
        
        # Process logging configuration
        if 'logging' in config_data:
            config_data['logging'] = LoggingConfig(**config_data['logging'])
        
        # Convert string paths to Path objects
        for path_field in ['data_dir', 'cache_dir', 'output_dir']:
            if path_field in config_data:
                config_data[path_field] = Path(config_data[path_field])
        
        return cls(**config_data)
    
    def ensure_directories(self):
        """Ensure that required directories exist"""
        for directory in [self.data_dir, self.cache_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_prefix = "RESEARCH_AGENT_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create default settings instance
settings = Settings()

# Load API keys from environment variables
def load_api_keys():
    """Load API keys from environment variables"""
    # ArXiv doesn't require an API key
    settings.apis["arxiv"] = APIConfig(
        name="ArXiv",
        base_url="http://export.arxiv.org/api/query",
        rate_limit=100  # ArXiv allows 100 requests per minute
    )
    
    # Semantic Scholar
    semantic_scholar_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    settings.apis["semantic_scholar"] = APIConfig(
        name="Semantic Scholar",
        base_url="https://api.semanticscholar.org/graph/v1",
        api_key=semantic_scholar_key,
        rate_limit=100  # 100 requests per 5-minute window with API key
    )
    
    # PubMed
    pubmed_key = os.getenv("PUBMED_API_KEY")
    settings.apis["pubmed"] = APIConfig(
        name="PubMed",
        base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        api_key=pubmed_key,
        rate_limit=10 if pubmed_key is None else 100  # Higher rate limit with API key
    )
    
    # CrossRef
    settings.apis["crossref"] = APIConfig(
        name="CrossRef",
        base_url="https://api.crossref.org",
        rate_limit=50  # Standard rate limit
    )
    
    # OpenAI (if used)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        settings.models["openai_gpt4"] = ModelConfig(
            name="GPT-4",
            type="openai",
            api_endpoint="https://api.openai.com/v1/chat/completions",
            parameters={
                "model": "gpt-4",
                "temperature": 0.2,
                "max_tokens": 4000
            }
        )

# Load API keys on module import
load_api_keys()
