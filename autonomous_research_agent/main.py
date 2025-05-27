#!/usr/bin/env python3
"""
Autonomous Research Agent for Technical Papers
Main entry point for the application
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from tqdm import tqdm

from autonomous_research_agent.pipeline.research_pipeline import ResearchPipeline
from autonomous_research_agent.core.exceptions import PipelineError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('research_agent.log')
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@click.group()
def cli():
    """Autonomous Research Agent for Technical Papers"""
    pass

@cli.command()
@click.option('--query', required=True, help='Research question to investigate')
@click.option('--output-dir', help='Directory to save research output', default='research_output')
@click.option('--max-papers', default=50, type=int, help='Maximum number of papers to analyze')
@click.option('--date-range', help='Date range for papers (e.g., "2020-2023")')
def research(query: str, output_dir: Optional[str] = None, max_papers: int = 50, date_range: Optional[str] = None):
    """Process a research question and generate a comprehensive report"""
    logger.info(f"Starting research for query: {query}")
    logger.info(f"Parameters: max_papers={max_papers}, date_range={date_range}")
    
    try:
        # Create pipeline
        pipeline = ResearchPipeline(output_dir=output_dir)
        
        # Process query
        results = pipeline.process_query(query)
        
        # Print results
        click.echo(f"Research completed successfully!")
        click.echo(f"Project ID: {results['project_id']}")
        click.echo(f"Generated reports:")
        
        for format_name, report_path in results.get('reports', {}).items():
            if report_path:
                click.echo(f"  - {format_name}: {report_path}")
        
        click.echo(f"Changelog: {results.get('changelog_path', 'Not available')}")
        
    except PipelineError as e:
        logger.error(f"Research pipeline error: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--project-id', required=True, help='ID of the research project to resume')
@click.option('--output-dir', help='Directory to save research output', default='research_output')
def resume(project_id: str, output_dir: Optional[str] = None):
    """Resume a previous research project"""
    logger.info(f"Resuming research project: {project_id}")
    
    try:
        # Create pipeline
        pipeline = ResearchPipeline(output_dir=output_dir)
        
        # Resume research
        results = pipeline.resume_research(project_id)
        
        # Print results
        click.echo(f"Research resumed successfully!")
        click.echo(f"Project ID: {results['project_id']}")
        click.echo(f"Generated reports:")
        
        for format_name, report_path in results.get('reports', {}).items():
            if report_path:
                click.echo(f"  - {format_name}: {report_path}")
        
        click.echo(f"Changelog: {results.get('changelog_path', 'Not available')}")
        
    except PipelineError as e:
        logger.error(f"Research pipeline error: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--project-id', required=True, help='ID of the research project')
@click.option('--output-dir', help='Directory to save research output', default='research_output')
def status(project_id: str, output_dir: Optional[str] = None):
    """Get the status of a research project"""
    logger.info(f"Getting status for research project: {project_id}")
    
    try:
        # Create pipeline
        pipeline = ResearchPipeline(output_dir=output_dir)
        
        # Get project status
        status = pipeline.get_project_status(project_id)
        
        # Print status
        click.echo(f"Project ID: {status['project_id']}")
        click.echo(f"Status: {'Completed' if status['is_completed'] else 'In Progress'}")
        
        if status['has_error']:
            click.echo(f"Error detected in project")
        
        if status['latest_entry']:
            click.echo(f"Latest activity: {status['latest_entry']['type']} - {status['latest_entry']['description']}")
            click.echo(f"Timestamp: {status['latest_entry']['timestamp']}")
        
        if status['summary']:
            click.echo(f"Summary:")
            click.echo(f"  - Total entries: {status['summary']['entry_count']}")
            click.echo(f"  - Started: {status['summary']['first_timestamp']}")
            click.echo(f"  - Last updated: {status['summary']['last_timestamp']}")
        
    except PipelineError as e:
        logger.error(f"Research pipeline error: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
def version():
    """Display the current version of the application"""
    click.echo(f"Autonomous Research Agent for Technical Papers v0.1.0")

if __name__ == '__main__':
    cli()
