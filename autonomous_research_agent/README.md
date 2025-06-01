# Autonomous Research Agent for Technical Papers

## Overview
The Autonomous Research Agent for Technical Papers is an advanced AI-powered system designed to automate the entire research workflow for technical and academic papers. It autonomously searches, acquires, processes, analyzes, and generates comprehensive reports on specific research topics or questions.

The system employs natural language processing, information retrieval, and machine learning techniques to transform complex research questions into structured analyses, saving researchers significant time and enabling more efficient knowledge synthesis.

### Key Features
- **Intelligent Query Processing**: Analyzes natural language research questions and extracts key concepts
- **Multi-source Paper Acquisition**: Searches and retrieves papers from arXiv, Semantic Scholar, and other academic sources
- **Automated Content Processing**: Extracts and processes relevant information from papers
- **Comprehensive Analysis**: Compares methodologies, findings, and identifies research gaps
- **Multiple Report Formats**: Generates detailed reports in various formats (Markdown, PDF, HTML)
- **Project Tracking**: Maintains detailed changelogs of the research process

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- A virtual environment (recommended)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/Asfandyar1213/Autonomous-research-agent.git
   cd autonomous_research_agent
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Download required NLP models:
   ```bash
   python -m spacy download en_core_web_lg
   ```

## Usage

### Command Line Interface
The application provides a command-line interface with several commands:

#### Start a New Research Project
```bash
python -m autonomous_research_agent.main research --query "What are the recent advances in quantum computing?" --output-dir ./my_research --max-papers 30 --date-range "2020-2023"
```

#### Resume an Existing Research Project
```bash
python -m autonomous_research_agent.main resume --project-id research_a1b2c3d4 --output-dir ./my_research
```

#### Check Project Status
```bash
python -m autonomous_research_agent.main status --project-id research_a1b2c3d4
```

#### Show Version Information
```bash
python -m autonomous_research_agent.main version
```

### Example Workflow
1. **Start Research**: Ask a research question
   ```bash
   python -m autonomous_research_agent.main research --query "How have transformer models evolved since their introduction in 2017?"
   ```

2. **View Results**: Check the generated reports in the output directory
   ```bash
   # Reports are saved to ./research_output/reports/ by default
   ```

3. **Resume Later**: If needed, resume the research using the project ID
   ```bash
   python -m autonomous_research_agent.main resume --project-id research_a1b2c3d4
   ```

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:
```
# API Keys
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# Rate Limiting
API_CALLS_PER_MINUTE=10

# Processing Options
MAX_PAPERS_TO_PROCESS=50
PAPER_CHUNK_SIZE=1000
```

### Advanced Configuration
Additional configuration options are available in `config/settings.py`. These include:
- Model parameters for text processing
- Analysis thresholds and parameters
- Output formatting options

## Project Structure
```
autonomous_research_agent/
├── analysis/           # Components for analyzing papers
├── config/             # Configuration settings
├── content_processing/ # Text extraction and processing
├── core/               # Core components and exceptions
├── data_acquisition/   # Paper retrieval from sources
├── pipeline/           # Main research pipeline
├── report_generation/  # Report creation in various formats
├── tests/              # Test suite
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Citation
If you use this software in your research, please cite:
```
@software{autonomous_research_agent,
  author = {Asfandyar},
  title = {Autonomous Research Agent for Technical Papers},
  year = {2023},
  url = {https://github.com/Asfandyar1213/Autonomous-research-agent}
}