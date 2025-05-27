"""
Template Manager Module

This module manages templates for research reports, providing a flexible system
for generating different types of reports based on the research query and results.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import jinja2

from autonomous_research_agent.core.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)

class TemplateManager:
    """
    Manages templates for research reports
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template manager
        
        Args:
            templates_dir: Directory containing templates
        """
        # Use default templates directory if not specified
        if templates_dir is None:
            # Get the directory of this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(current_dir, 'templates')
        
        self.templates_dir = templates_dir
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.templates_dir),
            autoescape=jinja2.select_autoescape(['html']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._add_custom_filters()
        
        # Default templates
        self.default_templates = {
            'pdf': 'report_pdf.jinja2',
            'markdown': 'report_markdown.jinja2',
            'html': 'report_html.jinja2',
            'json': 'report_json.jinja2'
        }
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _add_custom_filters(self):
        """Add custom filters to Jinja2 environment"""
        # Filter to format a date
        def format_date(date_str, format='%Y-%m-%d'):
            if not date_str:
                return ''
            
            try:
                from datetime import datetime
                if isinstance(date_str, str):
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_obj = date_str
                
                return date_obj.strftime(format)
            except Exception:
                return date_str
        
        # Filter to truncate text
        def truncate_text(text, length=100):
            if not text:
                return ''
            
            if len(text) <= length:
                return text
            
            return text[:length] + '...'
        
        # Filter to format a list as comma-separated string
        def format_list(items, separator=', '):
            if not items:
                return ''
            
            return separator.join(str(item) for item in items)
        
        # Add filters to environment
        self.env.filters['format_date'] = format_date
        self.env.filters['truncate_text'] = truncate_text
        self.env.filters['format_list'] = format_list
    
    def _create_default_templates(self):
        """Create default templates if they don't exist"""
        # Markdown template
        markdown_template = """# Research Report: {{ query }}

## Executive Summary

This report presents findings from a systematic analysis of {{ papers|length }} academic papers related to the research question: "{{ query }}".

{% if topic_analysis and topic_analysis.success %}
The analysis identified {{ topic_analysis.results.num_topics }} main research topics in this area:
{% for topic_id, words in topic_analysis.results.topic_words.items() %}
- Topic {{ topic_id }}: {{ words|format_list }}
{% endfor %}
{% endif %}

{% if methodology_comparison and methodology_comparison.success %}
The most common research methodology was {{ methodology_comparison.results.most_common_methodology }}, used in {{ methodology_comparison.results.category_counts[methodology_comparison.results.most_common_methodology] }} papers.
{% endif %}

{% if findings_comparison and findings_comparison.success and findings_comparison.results.clusters %}
Key findings across the literature include:
{% for cluster in findings_comparison.results.clusters[:3] %}
- {{ cluster.representative }}
{% endfor %}
{% endif %}

{% if research_gaps %}
Potential research gaps identified:
{% for gap in research_gaps %}
- {{ gap }}
{% endfor %}
{% endif %}

## Literature Overview

### Temporal Distribution

{% if papers %}
The analyzed papers were published between {{ papers|map(attribute='year')|min }} and {{ papers|map(attribute='year')|max }}.
{% endif %}

### Key Research Clusters

{% if topic_analysis and topic_analysis.success %}
The analysis identified the following research clusters:

{% for topic_id, words in topic_analysis.results.topic_words.items() %}
#### Topic {{ topic_id }}: {{ words[:3]|format_list }}

Key terms: {{ words|format_list }}

Papers in this cluster:
{% if topic_analysis.results.topic_papers and topic_id in topic_analysis.results.topic_papers %}
{% for paper_title in topic_analysis.results.topic_papers[topic_id] %}
- {{ paper_title }}
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}

### Influential Papers

{% if papers %}
The most cited papers in this collection:

{% for paper in papers|sort(attribute='citation_count', reverse=True)[:5] %}
- **{{ paper.title }}** ({{ paper.year }}) - {{ paper.authors|map(attribute='name')|format_list }} ({{ paper.citation_count }} citations)
{% endfor %}
{% endif %}

## Methodology Analysis

{% if methodology_comparison and methodology_comparison.success %}
### Methodological Approaches

The analysis identified the following methodological approaches across the literature:

{% for methodology, count in methodology_comparison.results.category_counts.items() %}
- **{{ methodology }}**: Used in {{ count }} papers ({{ (count / papers|length * 100)|round }}%)
{% endfor %}

### Methodological Trends

The research shows a methodology diversity score of {{ methodology_comparison.results.methodology_diversity|round(2) }} (where 1.0 indicates each paper uses a unique methodology).

{% endif %}

## Findings Synthesis

{% if findings_comparison and findings_comparison.success and findings_comparison.results.clusters %}
### Key Findings

The analysis identified {{ findings_comparison.results.clusters|length }} distinct findings across the literature:

{% for cluster in findings_comparison.results.clusters %}
#### Finding {{ loop.index }}

{{ cluster.representative }}

Appears in {{ cluster.papers|length }} papers.

{% endfor %}

### Consensus Views

The analysis found an agreement score of {{ findings_comparison.results.agreement_score|round(2) }} across the literature (where 1.0 indicates complete agreement).

{% endif %}

{% if findings_comparison and findings_comparison.numerical_comparison and findings_comparison.numerical_comparison.metrics %}
### Quantitative Results

The analysis identified the following quantitative results across studies:

{% for metric, stats in findings_comparison.numerical_comparison.metrics.items() %}
#### {{ metric|capitalize }}

- Range: {{ stats.min|round(3) }} to {{ stats.max|round(3) }}
- Mean: {{ stats.mean|round(3) }}
- Standard deviation: {{ stats.std|round(3) }}
- Reported in {{ stats.count }} papers

{% endfor %}
{% endif %}

## Discussion

{% if research_gaps %}
### Research Gaps

The analysis identified the following potential research gaps:

{% for gap in research_gaps %}
- {{ gap }}
{% endfor %}
{% endif %}

## References

{% for paper in papers %}
{{ loop.index }}. **{{ paper.title }}** ({{ paper.year }})
   Authors: {{ paper.authors|map(attribute='name')|format_list }}
   {% if paper.venue %}Published in: {{ paper.venue }}{% endif %}
   {% if paper.doi %}DOI: {{ paper.doi }}{% endif %}
   {% if paper.url %}URL: {{ paper.url }}{% endif %}

{% endfor %}

---

*Report generated on {{ now|format_date('%Y-%m-%d') }} by Autonomous Research Agent*
"""
        
        # HTML template
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Report: {{ query }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3, h4 {
            color: #2c3e50;
            margin-top: 1.5em;
        }
        h1 {
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
        }
        .executive-summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin-bottom: 20px;
        }
        .paper-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #fff;
        }
        .paper-title {
            font-weight: bold;
            color: #2980b9;
        }
        .methodology-bar {
            background-color: #3498db;
            height: 20px;
            border-radius: 3px;
            margin-top: 5px;
        }
        .finding-card {
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #27ae60;
            margin-bottom: 15px;
        }
        .gap-card {
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #e74c3c;
            margin-bottom: 15px;
        }
        .references {
            font-size: 0.9em;
        }
        footer {
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            font-size: 0.8em;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <h1>Research Report: {{ query }}</h1>
    
    <div class="executive-summary">
        <h2>Executive Summary</h2>
        <p>This report presents findings from a systematic analysis of {{ papers|length }} academic papers related to the research question: "{{ query }}".</p>
        
        {% if topic_analysis and topic_analysis.success %}
        <p>The analysis identified {{ topic_analysis.results.num_topics }} main research topics in this area:</p>
        <ul>
            {% for topic_id, words in topic_analysis.results.topic_words.items() %}
            <li><strong>Topic {{ topic_id }}:</strong> {{ words|format_list }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        
        {% if methodology_comparison and methodology_comparison.success %}
        <p>The most common research methodology was <strong>{{ methodology_comparison.results.most_common_methodology }}</strong>, used in {{ methodology_comparison.results.category_counts[methodology_comparison.results.most_common_methodology] }} papers.</p>
        {% endif %}
        
        {% if findings_comparison and findings_comparison.success and findings_comparison.results.clusters %}
        <p>Key findings across the literature include:</p>
        <ul>
            {% for cluster in findings_comparison.results.clusters[:3] %}
            <li>{{ cluster.representative }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        
        {% if research_gaps %}
        <p>Potential research gaps identified:</p>
        <ul>
            {% for gap in research_gaps %}
            <li>{{ gap }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    
    <h2>Literature Overview</h2>
    
    <h3>Temporal Distribution</h3>
    {% if papers %}
    <p>The analyzed papers were published between {{ papers|map(attribute='year')|min }} and {{ papers|map(attribute='year')|max }}.</p>
    {% endif %}
    
    <h3>Key Research Clusters</h3>
    {% if topic_analysis and topic_analysis.success %}
    <p>The analysis identified the following research clusters:</p>
    
    {% for topic_id, words in topic_analysis.results.topic_words.items() %}
    <h4>Topic {{ topic_id }}: {{ words[:3]|format_list }}</h4>
    <p>Key terms: {{ words|format_list }}</p>
    
    <p>Papers in this cluster:</p>
    {% if topic_analysis.results.topic_papers and topic_id in topic_analysis.results.topic_papers %}
    <ul>
        {% for paper_title in topic_analysis.results.topic_papers[topic_id] %}
        <li>{{ paper_title }}</li>
        {% endfor %}
    </ul>
    {% endif %}
    {% endfor %}
    {% endif %}
    
    <h3>Influential Papers</h3>
    {% if papers %}
    <p>The most cited papers in this collection:</p>
    
    {% for paper in papers|sort(attribute='citation_count', reverse=True)[:5] %}
    <div class="paper-card">
        <div class="paper-title">{{ paper.title }} ({{ paper.year }})</div>
        <div>Authors: {{ paper.authors|map(attribute='name')|format_list }}</div>
        <div>Citations: {{ paper.citation_count }}</div>
    </div>
    {% endfor %}
    {% endif %}
    
    <h2>Methodology Analysis</h2>
    
    {% if methodology_comparison and methodology_comparison.success %}
    <h3>Methodological Approaches</h3>
    <p>The analysis identified the following methodological approaches across the literature:</p>
    
    {% for methodology, count in methodology_comparison.results.category_counts.items() %}
    <div>
        <strong>{{ methodology }}</strong>: Used in {{ count }} papers ({{ (count / papers|length * 100)|round }}%)
        <div class="methodology-bar" style="width: {{ (count / papers|length * 100)|round }}%;"></div>
    </div>
    {% endfor %}
    
    <h3>Methodological Trends</h3>
    <p>The research shows a methodology diversity score of {{ methodology_comparison.results.methodology_diversity|round(2) }} (where 1.0 indicates each paper uses a unique methodology).</p>
    {% endif %}
    
    <h2>Findings Synthesis</h2>
    
    {% if findings_comparison and findings_comparison.success and findings_comparison.results.clusters %}
    <h3>Key Findings</h3>
    <p>The analysis identified {{ findings_comparison.results.clusters|length }} distinct findings across the literature:</p>
    
    {% for cluster in findings_comparison.results.clusters %}
    <div class="finding-card">
        <h4>Finding {{ loop.index }}</h4>
        <p>{{ cluster.representative }}</p>
        <p>Appears in {{ cluster.papers|length }} papers.</p>
    </div>
    {% endfor %}
    
    <h3>Consensus Views</h3>
    <p>The analysis found an agreement score of {{ findings_comparison.results.agreement_score|round(2) }} across the literature (where 1.0 indicates complete agreement).</p>
    {% endif %}
    
    {% if findings_comparison and findings_comparison.numerical_comparison and findings_comparison.numerical_comparison.metrics %}
    <h3>Quantitative Results</h3>
    <p>The analysis identified the following quantitative results across studies:</p>
    
    {% for metric, stats in findings_comparison.numerical_comparison.metrics.items() %}
    <h4>{{ metric|capitalize }}</h4>
    <ul>
        <li>Range: {{ stats.min|round(3) }} to {{ stats.max|round(3) }}</li>
        <li>Mean: {{ stats.mean|round(3) }}</li>
        <li>Standard deviation: {{ stats.std|round(3) }}</li>
        <li>Reported in {{ stats.count }} papers</li>
    </ul>
    {% endfor %}
    {% endif %}
    
    <h2>Discussion</h2>
    
    {% if research_gaps %}
    <h3>Research Gaps</h3>
    <p>The analysis identified the following potential research gaps:</p>
    
    {% for gap in research_gaps %}
    <div class="gap-card">
        <p>{{ gap }}</p>
    </div>
    {% endfor %}
    {% endif %}
    
    <h2>References</h2>
    <div class="references">
        {% for paper in papers %}
        <p>
            {{ loop.index }}. <strong>{{ paper.title }}</strong> ({{ paper.year }})<br>
            Authors: {{ paper.authors|map(attribute='name')|format_list }}<br>
            {% if paper.venue %}Published in: {{ paper.venue }}<br>{% endif %}
            {% if paper.doi %}DOI: {{ paper.doi }}<br>{% endif %}
            {% if paper.url %}URL: <a href="{{ paper.url }}">{{ paper.url }}</a>{% endif %}
        </p>
        {% endfor %}
    </div>
    
    <footer>
        <p>Report generated on {{ now|format_date('%Y-%m-%d') }} by Autonomous Research Agent</p>
    </footer>
</body>
</html>
"""
        
        # JSON template
        json_template = """{
    "report": {
        "title": "Research Report: {{ query }}",
        "generated_date": "{{ now|format_date('%Y-%m-%d') }}",
        "query": "{{ query }}"
    },
    "executive_summary": {
        "paper_count": {{ papers|length }},
        {% if topic_analysis and topic_analysis.success %}
        "topics": [
            {% for topic_id, words in topic_analysis.results.topic_words.items() %}
            {
                "id": {{ topic_id }},
                "keywords": {{ words|tojson }}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        ],
        {% endif %}
        {% if methodology_comparison and methodology_comparison.success %}
        "most_common_methodology": "{{ methodology_comparison.results.most_common_methodology }}",
        {% endif %}
        {% if findings_comparison and findings_comparison.success and findings_comparison.results.clusters %}
        "key_findings": [
            {% for cluster in findings_comparison.results.clusters[:3] %}
            "{{ cluster.representative }}"{% if not loop.last %},{% endif %}
            {% endfor %}
        ],
        {% endif %}
        {% if research_gaps %}
        "research_gaps": {{ research_gaps|tojson }}
        {% endif %}
    },
    "literature_overview": {
        {% if papers %}
        "year_range": {
            "min": {{ papers|map(attribute='year')|min }},
            "max": {{ papers|map(attribute='year')|max }}
        },
        {% endif %}
        {% if topic_analysis and topic_analysis.success %}
        "research_clusters": [
            {% for topic_id, words in topic_analysis.results.topic_words.items() %}
            {
                "id": {{ topic_id }},
                "keywords": {{ words|tojson }},
                {% if topic_analysis.results.topic_papers and topic_id in topic_analysis.results.topic_papers %}
                "papers": {{ topic_analysis.results.topic_papers[topic_id]|tojson }}
                {% else %}
                "papers": []
                {% endif %}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        ],
        {% endif %}
        "influential_papers": [
            {% for paper in papers|sort(attribute='citation_count', reverse=True)[:5] %}
            {
                "title": "{{ paper.title }}",
                "year": {{ paper.year }},
                "authors": {{ paper.authors|map(attribute='name')|list|tojson }},
                "citation_count": {{ paper.citation_count }}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        ]
    },
    {% if methodology_comparison and methodology_comparison.success %}
    "methodology_analysis": {
        "approaches": {
            {% for methodology, count in methodology_comparison.results.category_counts.items() %}
            "{{ methodology }}": {
                "count": {{ count }},
                "percentage": {{ (count / papers|length * 100)|round }}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        },
        "diversity_score": {{ methodology_comparison.results.methodology_diversity|round(2) }}
    },
    {% endif %}
    {% if findings_comparison and findings_comparison.success %}
    "findings_synthesis": {
        {% if findings_comparison.results.clusters %}
        "key_findings": [
            {% for cluster in findings_comparison.results.clusters %}
            {
                "id": {{ loop.index }},
                "text": "{{ cluster.representative }}",
                "paper_count": {{ cluster.papers|length }}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        ],
        {% endif %}
        "agreement_score": {{ findings_comparison.results.agreement_score|round(2) }},
        {% if findings_comparison.numerical_comparison and findings_comparison.numerical_comparison.metrics %}
        "quantitative_results": {
            {% for metric, stats in findings_comparison.numerical_comparison.metrics.items() %}
            "{{ metric }}": {
                "min": {{ stats.min|round(3) }},
                "max": {{ stats.max|round(3) }},
                "mean": {{ stats.mean|round(3) }},
                "std": {{ stats.std|round(3) }},
                "count": {{ stats.count }}
            }{% if not loop.last %},{% endif %}
            {% endfor %}
        }
        {% endif %}
    },
    {% endif %}
    {% if research_gaps %}
    "research_gaps": {{ research_gaps|tojson }},
    {% endif %}
    "references": [
        {% for paper in papers %}
        {
            "id": {{ loop.index }},
            "title": "{{ paper.title }}",
            "year": {{ paper.year }},
            "authors": {{ paper.authors|map(attribute='name')|list|tojson }},
            {% if paper.venue %}"venue": "{{ paper.venue }}",{% endif %}
            {% if paper.doi %}"doi": "{{ paper.doi }}",{% endif %}
            {% if paper.url %}"url": "{{ paper.url }}"{% endif %}
        }{% if not loop.last %},{% endif %}
        {% endfor %}
    ]
}
"""
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Write templates to files if they don't exist
        templates = {
            'report_markdown.jinja2': markdown_template,
            'report_html.jinja2': html_template,
            'report_json.jinja2': json_template
        }
        
        for filename, content in templates.items():
            filepath = os.path.join(self.templates_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def render_template(self, template_name: str, context: Dict) -> str:
        """
        Render a template with the given context
        
        Args:
            template_name: Name of the template to render
            context: Dictionary of context variables for the template
            
        Returns:
            Rendered template as a string
        """
        try:
            # Get template
            template = self.env.get_template(template_name)
            
            # Add current date to context
            from datetime import datetime
            context['now'] = datetime.now()
            
            # Render template
            return template.render(**context)
            
        except jinja2.exceptions.TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise ReportGenerationError(f"Template not found: {template_name}")
        
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            raise ReportGenerationError(f"Error rendering template: {str(e)}")
    
    def get_template_for_format(self, output_format: str) -> str:
        """
        Get the appropriate template for the specified output format
        
        Args:
            output_format: Output format (pdf, markdown, html, json)
            
        Returns:
            Template name
        """
        if output_format in self.default_templates:
            return self.default_templates[output_format]
        else:
            logger.warning(f"Unknown output format: {output_format}, using markdown")
            return self.default_templates['markdown']
