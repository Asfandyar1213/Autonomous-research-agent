<div align="center">

# Autonomous Research Agent for Technical Papers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/Asfandyar1213/Autonomous-research-agent)](https://github.com/Asfandyar1213/Autonomous-research-agent/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

An intelligent agent that autonomously searches academic databases, analyzes research papers, and generates comprehensive structured reports in response to research questions.

</div>

## Overview

The Autonomous Research Agent is designed to streamline the academic research process by automating the discovery, analysis, and synthesis of scholarly literature. It accepts natural language research questions as input and produces detailed, structured reports that compare methodologies, synthesize findings, and identify research gaps.

### Key Features

- **Intelligent Query Processing**: Transforms natural language questions into optimized search queries
- **Multi-Source Data Acquisition**: Retrieves papers from arXiv, Semantic Scholar, PubMed, and CrossRef
- **Advanced Content Analysis**: Extracts methodologies, findings, and relationships between papers
- **Comprehensive Report Generation**: Creates structured reports with visualizations and proper citations
- **Robust Changelog System**: Tracks all code changes with semantic versioning
- **Production-Ready Architecture**: Containerized, scalable, and secure implementation

## Project Structure

```
autonomous_research_agent/
├── config/                 # Configuration settings
├── core/                   # Core functionality
├── data_acquisition/       # API clients for academic databases
├── content_processing/     # Document parsing and text extraction
├── analysis/               # NLP and comparative analysis
├── report_generation/      # Report creation and formatting
├── changelog/              # Version control and change tracking
├── ui/                     # User interfaces (CLI and API)
├── utils/                  # Helper utilities
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## Implementation Documents

- [Architecture Design](architecture.md): System components, data flow, and integration points
- [Technical Implementation](technical_implementation.md): Code structure, API integrations, and model selection
- [Research Pipeline](research_pipeline.md): Step-by-step process from query to final report
- [Output Specifications](output_specifications.md): Detailed structure for the research report
- [Changelog System](changelog_system.md): Implementation of version control and change tracking
- [Deployment Strategy](deployment_strategy.md): Making the agent production-ready

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Asfandyar1213/Autonomous-research-agent.git
   cd Autonomous-research-agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up API keys:
   ```bash
   cp config/api_keys.example.py config/api_keys.py
   # Edit config/api_keys.py with your API keys
   ```

### Usage

#### Command Line Interface

```bash
# Basic usage with a research question
python main.py --query "What are the recent advances in transformer architectures for natural language processing?"

# Specify output format
python main.py --query "..." --format pdf

# Set search parameters
python main.py --query "..." --max-papers 50 --date-range "2020-2023"
```

#### Web API

```bash
# Start the API server
python -m ui.api

# In another terminal, make a request
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the recent advances in transformer architectures for natural language processing?", "max_papers": 50}'
```

#### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# Make a request to the API
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the recent advances in transformer architectures for natural language processing?"}'
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=./ --cov-report=xml

# Run specific test module
pytest tests/test_query_processor.py
```

### Code Style

```bash
# Check code style
flake8 .

# Format code
black .

# Sort imports
isort .
```

### Adding a New Feature

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Implement your changes

3. Add tests for your feature

4. Record changes in the changelog:
   ```bash
   python -m changelog.cli add --component "component_name" --type "feat" --description "Added new feature X"
   ```

5. Submit a pull request

## Contributing

Contributions are welcome! We appreciate all contributions, from reporting bugs and improving documentation to implementing new features. Here's how you can contribute:

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit your changes**:
   ```bash
   git commit -m "Add some feature"
   ```
4. **Push to your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a pull request**

Please make sure your code follows our coding standards and includes appropriate tests.

### Code of Conduct

We expect all contributors to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before participating.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Academic API providers: arXiv, Semantic Scholar, PubMed, CrossRef
- Open-source NLP libraries: Hugging Face Transformers, spaCy, NLTK
- The research community for making knowledge accessible

---

<div align="center">

Built  by [Asfandyar](https://github.com/Asfandyar1213)

</div>
