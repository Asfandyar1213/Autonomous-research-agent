"""
Changelog Manager Module

This module manages a changelog system to track research progress and updates.
It records changes in the research process, findings, and analysis results.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from autonomous_research_agent.core.exceptions import ChangelogError

logger = logging.getLogger(__name__)

class ChangelogEntry:
    """
    Represents a single changelog entry
    """
    
    def __init__(
        self,
        entry_type: str,
        description: str,
        details: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize a changelog entry
        
        Args:
            entry_type: Type of changelog entry (e.g., 'paper_added', 'analysis_updated')
            description: Brief description of the change
            details: Additional details about the change
            timestamp: Timestamp of the change
        """
        self.entry_type = entry_type
        self.description = description
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        """
        Convert the entry to a dictionary
        
        Returns:
            Dictionary representation of the entry
        """
        return {
            'type': self.entry_type,
            'description': self.description,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChangelogEntry':
        """
        Create a changelog entry from a dictionary
        
        Args:
            data: Dictionary representation of the entry
            
        Returns:
            ChangelogEntry instance
        """
        timestamp = datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else None
        return cls(
            entry_type=data['type'],
            description=data['description'],
            details=data.get('details', {}),
            timestamp=timestamp
        )


class ChangelogManager:
    """
    Manages the changelog for a research project
    """
    
    def __init__(self, project_id: str, changelog_dir: Optional[str] = None):
        """
        Initialize the changelog manager
        
        Args:
            project_id: Identifier for the research project
            changelog_dir: Directory to store changelog files
        """
        self.project_id = project_id
        
        # Use default changelog directory if not specified
        if changelog_dir is None:
            # Get the current working directory
            changelog_dir = os.path.join(os.getcwd(), 'changelogs')
        
        self.changelog_dir = changelog_dir
        
        # Create changelog directory if it doesn't exist
        os.makedirs(self.changelog_dir, exist_ok=True)
        
        # Initialize entries list
        self.entries = []
        
        # Load existing changelog if available
        self._load_changelog()
    
    def _get_changelog_path(self) -> str:
        """
        Get the path to the changelog file
        
        Returns:
            Path to the changelog file
        """
        return os.path.join(self.changelog_dir, f"changelog_{self.project_id}.json")
    
    def _load_changelog(self):
        """Load existing changelog if available"""
        changelog_path = self._get_changelog_path()
        
        if os.path.exists(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert dictionaries to ChangelogEntry objects
                self.entries = [ChangelogEntry.from_dict(entry) for entry in data]
                logger.info(f"Loaded {len(self.entries)} changelog entries")
                
            except Exception as e:
                logger.error(f"Error loading changelog: {str(e)}")
                # Initialize with empty list if loading fails
                self.entries = []
    
    def _save_changelog(self):
        """Save the changelog to file"""
        changelog_path = self._get_changelog_path()
        
        try:
            # Convert entries to dictionaries
            data = [entry.to_dict() for entry in self.entries]
            
            with open(changelog_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.entries)} changelog entries")
            
        except Exception as e:
            logger.error(f"Error saving changelog: {str(e)}")
            raise ChangelogError(f"Failed to save changelog: {str(e)}")
    
    def add_entry(
        self,
        entry_type: str,
        description: str,
        details: Optional[Dict] = None
    ) -> ChangelogEntry:
        """
        Add a new entry to the changelog
        
        Args:
            entry_type: Type of changelog entry
            description: Brief description of the change
            details: Additional details about the change
            
        Returns:
            The created changelog entry
        """
        # Create new entry
        entry = ChangelogEntry(
            entry_type=entry_type,
            description=description,
            details=details
        )
        
        # Add to entries list
        self.entries.append(entry)
        
        # Save changelog
        self._save_changelog()
        
        return entry
    
    def get_entries(
        self,
        entry_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ChangelogEntry]:
        """
        Get changelog entries with optional filtering
        
        Args:
            entry_type: Filter by entry type
            start_time: Filter entries after this time
            end_time: Filter entries before this time
            
        Returns:
            List of changelog entries
        """
        filtered_entries = self.entries
        
        # Filter by entry type
        if entry_type:
            filtered_entries = [entry for entry in filtered_entries if entry.entry_type == entry_type]
        
        # Filter by start time
        if start_time:
            filtered_entries = [entry for entry in filtered_entries if entry.timestamp >= start_time]
        
        # Filter by end time
        if end_time:
            filtered_entries = [entry for entry in filtered_entries if entry.timestamp <= end_time]
        
        # Sort by timestamp
        filtered_entries.sort(key=lambda entry: entry.timestamp)
        
        return filtered_entries
    
    def get_latest_entry(self, entry_type: Optional[str] = None) -> Optional[ChangelogEntry]:
        """
        Get the latest changelog entry
        
        Args:
            entry_type: Filter by entry type
            
        Returns:
            Latest changelog entry or None if no entries exist
        """
        filtered_entries = self.get_entries(entry_type=entry_type)
        
        if filtered_entries:
            return filtered_entries[-1]
        
        return None
    
    def generate_summary(self) -> Dict:
        """
        Generate a summary of the changelog
        
        Returns:
            Dictionary with changelog summary
        """
        # Count entries by type
        entry_counts = {}
        for entry in self.entries:
            entry_counts[entry.entry_type] = entry_counts.get(entry.entry_type, 0) + 1
        
        # Get first and last entry timestamps
        if self.entries:
            first_entry = min(self.entries, key=lambda entry: entry.timestamp)
            last_entry = max(self.entries, key=lambda entry: entry.timestamp)
            first_timestamp = first_entry.timestamp
            last_timestamp = last_entry.timestamp
        else:
            first_timestamp = None
            last_timestamp = None
        
        return {
            'project_id': self.project_id,
            'entry_count': len(self.entries),
            'entry_counts_by_type': entry_counts,
            'first_timestamp': first_timestamp.isoformat() if first_timestamp else None,
            'last_timestamp': last_timestamp.isoformat() if last_timestamp else None
        }
    
    def clear(self):
        """Clear all changelog entries"""
        self.entries = []
        self._save_changelog()
        logger.info("Changelog cleared")
    
    def generate_report(self) -> str:
        """
        Generate a human-readable report of the changelog
        
        Returns:
            Markdown formatted report
        """
        if not self.entries:
            return "# Changelog\n\nNo entries found."
        
        # Sort entries by timestamp
        sorted_entries = sorted(self.entries, key=lambda entry: entry.timestamp)
        
        # Group entries by date
        entries_by_date = {}
        for entry in sorted_entries:
            date_str = entry.timestamp.strftime('%Y-%m-%d')
            if date_str not in entries_by_date:
                entries_by_date[date_str] = []
            entries_by_date[date_str].append(entry)
        
        # Generate report
        report = ["# Changelog\n"]
        
        for date_str, entries in entries_by_date.items():
            report.append(f"## {date_str}\n")
            
            for entry in entries:
                time_str = entry.timestamp.strftime('%H:%M:%S')
                report.append(f"### {time_str} - {entry.entry_type}\n")
                report.append(f"{entry.description}\n")
                
                if entry.details:
                    report.append("**Details:**\n")
                    for key, value in entry.details.items():
                        if isinstance(value, dict) or isinstance(value, list):
                            value_str = json.dumps(value, indent=2)
                            report.append(f"- **{key}**:\n```json\n{value_str}\n```\n")
                        else:
                            report.append(f"- **{key}**: {value}\n")
                
                report.append("\n")
        
        return "\n".join(report)
