"""
Report Generator Module

This module generates comprehensive research reports based on the analysis results.
It uses the template manager to render reports in different formats.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import markdown
from weasyprint import HTML

from autonomous_research_agent.core.exceptions import ReportGenerationError
from autonomous_research_agent.report_generation.template_manager import TemplateManager

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates research reports based on analysis results
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the report generator
        
        Args:
            output_dir: Directory to save generated reports
        """
        # Use default output directory if not specified
        if output_dir is None:
            # Get the current working directory
            output_dir = os.path.join(os.getcwd(), 'reports')
        
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize template manager
        self.template_manager = TemplateManager()
    
    def generate_report(self, analysis_results: Dict, output_format: str = 'markdown') -> str:
        """
        Generate a research report
        
        Args:
            analysis_results: Results of the analysis
            output_format: Format of the report (markdown, html, pdf, json)
            
        Returns:
            Path to the generated report
        """
        logger.info(f"Generating {output_format} report")
        
        try:
            # Get template for the specified format
            template_name = self.template_manager.get_template_for_format(output_format)
            
            # Render template
            report_content = self.template_manager.render_template(template_name, analysis_results)
            
            # Generate filename
            query = analysis_results.get('query', {}).get('original_query', 'research')
            query_slug = self._slugify(query)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{query_slug}_{timestamp}.{self._get_file_extension(output_format)}"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save report
            if output_format == 'pdf':
                self._generate_pdf(report_content, filepath)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            
            logger.info(f"Report saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise ReportGenerationError(f"Report generation failed: {str(e)}")
    
    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        import re
        import unicodedata
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        # Remove non-word characters
        text = re.sub(r'[^\w\s-]', '', text.lower())
        # Replace spaces with hyphens
        text = re.sub(r'[-\s]+', '-', text).strip('-_')
        # Limit length
        return text[:50]
    
    def _get_file_extension(self, output_format: str) -> str:
        """
        Get file extension for the specified output format
        
        Args:
            output_format: Output format
            
        Returns:
            File extension
        """
        extensions = {
            'markdown': 'md',
            'html': 'html',
            'pdf': 'pdf',
            'json': 'json'
        }
        
        return extensions.get(output_format, 'txt')
    
    def _generate_pdf(self, html_content: str, output_path: str):
        """
        Generate PDF from HTML content
        
        Args:
            html_content: HTML content
            output_path: Path to save the PDF
        """
        try:
            # Convert HTML to PDF
            HTML(string=html_content).write_pdf(output_path)
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise ReportGenerationError(f"PDF generation failed: {str(e)}")
    
    def generate_all_formats(self, analysis_results: Dict) -> Dict[str, str]:
        """
        Generate reports in all available formats
        
        Args:
            analysis_results: Results of the analysis
            
        Returns:
            Dictionary mapping formats to file paths
        """
        formats = ['markdown', 'html', 'json', 'pdf']
        reports = {}
        
        for output_format in formats:
            try:
                filepath = self.generate_report(analysis_results, output_format)
                reports[output_format] = filepath
            except Exception as e:
                logger.error(f"Error generating {output_format} report: {str(e)}")
                reports[output_format] = None
        
        return reports
