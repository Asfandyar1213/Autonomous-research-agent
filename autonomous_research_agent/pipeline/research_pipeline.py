"""
Research Pipeline Module

This module coordinates the entire research process, from query processing to report generation.
It manages the flow of data between different components of the system.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from autonomous_research_agent.core.exceptions import PipelineError
from autonomous_research_agent.core.query_processor import QueryProcessor, StructuredQuery
from autonomous_research_agent.data_acquisition.acquisition_manager import AcquisitionManager
from autonomous_research_agent.content_processing.processing_manager import ProcessingManager
from autonomous_research_agent.analysis.analysis_manager import AnalysisManager
from autonomous_research_agent.report_generation.report_generator import ReportGenerator
from autonomous_research_agent.report_generation.changelog_manager import ChangelogManager

logger = logging.getLogger(__name__)

class ResearchPipeline:
    """
    Coordinates the entire research process
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the research pipeline
        
        Args:
            output_dir: Directory to save output files
        """
        # Use default output directory if not specified
        if output_dir is None:
            # Get the current working directory
            output_dir = os.path.join(os.getcwd(), 'research_output')
        
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.query_processor = QueryProcessor()
        self.acquisition_manager = AcquisitionManager()
        self.processing_manager = ProcessingManager()
        self.analysis_manager = AnalysisManager()
        self.report_generator = ReportGenerator(output_dir=os.path.join(self.output_dir, 'reports'))
    
    def process_query(self, query: str) -> Dict:
        """
        Process a research query and generate a comprehensive report
        
        Args:
            query: Research question to investigate
            
        Returns:
            Dictionary with research results
        """
        # Generate a unique project ID
        project_id = f"research_{uuid.uuid4().hex[:8]}"
        
        # Initialize changelog
        changelog = ChangelogManager(
            project_id=project_id,
            changelog_dir=os.path.join(self.output_dir, 'changelogs')
        )
        
        try:
            # Step 1: Process query
            logger.info(f"Processing query: {query}")
            changelog.add_entry(
                entry_type='query_received',
                description=f"Received research query: {query}"
            )
            
            structured_query = self.query_processor.process(query)
            
            changelog.add_entry(
                entry_type='query_processed',
                description=f"Processed research query into structured format",
                details={
                    'structured_query': structured_query.to_dict()
                }
            )
            
            # Step 2: Acquire papers
            logger.info("Acquiring papers")
            papers = self.acquisition_manager.acquire_papers(structured_query)
            
            changelog.add_entry(
                entry_type='papers_acquired',
                description=f"Acquired {len(papers)} papers for research",
                details={
                    'paper_count': len(papers),
                    'sources': [paper.source for paper in papers]
                }
            )
            
            # Step 3: Process papers
            logger.info("Processing papers")
            processed_papers = self.processing_manager.process_papers(papers)
            
            changelog.add_entry(
                entry_type='papers_processed',
                description=f"Processed {len(processed_papers)} papers",
                details={
                    'processed_count': len(processed_papers),
                    'successful_count': sum(1 for paper in processed_papers if paper.processing_success)
                }
            )
            
            # Step 4: Analyze papers
            logger.info("Analyzing papers")
            analysis_results = self.analysis_manager.analyze(processed_papers, structured_query)
            
            changelog.add_entry(
                entry_type='analysis_completed',
                description=f"Completed analysis of research papers",
                details={
                    'topic_count': analysis_results.get('topic_analysis', {}).get('results', {}).get('num_topics', 0) if analysis_results.get('topic_analysis', {}).get('success', False) else 0,
                    'methodology_count': len(analysis_results.get('methodology_comparison', {}).get('results', {}).get('category_counts', {})) if analysis_results.get('methodology_comparison', {}).get('success', False) else 0,
                    'findings_count': len(analysis_results.get('findings_comparison', {}).get('results', {}).get('clusters', [])) if analysis_results.get('findings_comparison', {}).get('success', False) else 0
                }
            )
            
            # Step 5: Generate reports
            logger.info("Generating reports")
            reports = self.report_generator.generate_all_formats(analysis_results)
            
            changelog.add_entry(
                entry_type='reports_generated',
                description=f"Generated research reports in multiple formats",
                details={
                    'report_formats': list(reports.keys()),
                    'report_paths': {k: v for k, v in reports.items() if v is not None}
                }
            )
            
            # Generate changelog report
            changelog_report = changelog.generate_report()
            changelog_path = os.path.join(self.output_dir, 'reports', f"changelog_{project_id}.md")
            
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(changelog_report)
            
            # Prepare results
            results = {
                'project_id': project_id,
                'query': query,
                'structured_query': structured_query.to_dict(),
                'paper_count': len(papers),
                'processed_count': len(processed_papers),
                'reports': reports,
                'changelog_path': changelog_path,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Research process completed successfully for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in research pipeline: {str(e)}")
            
            # Record error in changelog
            changelog.add_entry(
                entry_type='error',
                description=f"Error in research pipeline: {str(e)}",
                details={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            
            raise PipelineError(f"Research pipeline failed: {str(e)}")
    
    def resume_research(self, project_id: str) -> Dict:
        """
        Resume a previous research project
        
        Args:
            project_id: ID of the research project to resume
            
        Returns:
            Dictionary with research results
        """
        # Initialize changelog
        changelog = ChangelogManager(
            project_id=project_id,
            changelog_dir=os.path.join(self.output_dir, 'changelogs')
        )
        
        # Check if project exists
        if not changelog.entries:
            raise PipelineError(f"Research project {project_id} not found")
        
        try:
            # Get the original query
            query_entry = next((entry for entry in changelog.entries if entry.entry_type == 'query_received'), None)
            
            if not query_entry:
                raise PipelineError(f"Original query not found for project {project_id}")
            
            # Extract query from description
            query = query_entry.description.replace("Received research query: ", "")
            
            # Process the query again
            return self.process_query(query)
            
        except Exception as e:
            logger.error(f"Error resuming research project {project_id}: {str(e)}")
            raise PipelineError(f"Failed to resume research: {str(e)}")
    
    def get_project_status(self, project_id: str) -> Dict:
        """
        Get the status of a research project
        
        Args:
            project_id: ID of the research project
            
        Returns:
            Dictionary with project status
        """
        # Initialize changelog
        changelog = ChangelogManager(
            project_id=project_id,
            changelog_dir=os.path.join(self.output_dir, 'changelogs')
        )
        
        # Check if project exists
        if not changelog.entries:
            raise PipelineError(f"Research project {project_id} not found")
        
        # Get summary
        summary = changelog.generate_summary()
        
        # Get latest entry
        latest_entry = changelog.get_latest_entry()
        
        return {
            'project_id': project_id,
            'summary': summary,
            'latest_entry': latest_entry.to_dict() if latest_entry else None,
            'is_completed': any(entry.entry_type == 'reports_generated' for entry in changelog.entries),
            'has_error': any(entry.entry_type == 'error' for entry in changelog.entries)
        }
