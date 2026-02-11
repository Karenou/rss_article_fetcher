"""RSS Manager Module

This module handles reading and parsing RSS subscription sources.
"""

import os
import re
from typing import List, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass
class RSSSource:
    """RSS source data model."""
    title: str
    xml_url: str
    html_url: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"RSSSource(title='{self.title}', xml_url='{self.xml_url}')"


class RSSManager:
    """Manages RSS subscription sources."""
    
    def __init__(self, rss_file_path: str, logger=None):
        """Initialize RSS manager.
        
        Args:
            rss_file_path: Path to RSS subscription file.
            logger: Logger instance.
        """
        self.rss_file_path = rss_file_path
        self.logger = logger
        self.sources: List[RSSSource] = []
    
    def load_sources(self) -> List[RSSSource]:
        """Load RSS sources from file.
        
        Returns:
            List of RSSSource objects.
        
        Raises:
            FileNotFoundError: If RSS file doesn't exist.
            ValueError: If RSS file is empty or invalid.
        """
        if not os.path.exists(self.rss_file_path):
            error_msg = f"RSS subscription file not found: {self.rss_file_path}"
            if self.logger:
                self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        if self.logger:
            self.logger.info(f"Loading RSS sources from: {self.rss_file_path}")
        
        try:
            with open(self.rss_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                error_msg = "RSS subscription file is empty"
                if self.logger:
                    self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Try to detect format and parse
            if '<outline' in content:
                # OPML format
                self.sources = self._parse_opml(content)
            else:
                # Try plain text format (one URL per line)
                self.sources = self._parse_plain_text(content)
            
            if not self.sources:
                error_msg = "No valid RSS sources found in file"
                if self.logger:
                    self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            if self.logger:
                self.logger.info(f"Successfully loaded {len(self.sources)} RSS sources")
                for source in self.sources:
                    self.logger.debug(f"  - {source.title}: {source.xml_url}")
            
            return self.sources
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading RSS sources: {e}", exc_info=True)
            raise
    
    def _parse_opml(self, content: str) -> List[RSSSource]:
        """Parse OPML format RSS sources.
        
        Args:
            content: OPML content string.
        
        Returns:
            List of RSSSource objects.
        """
        sources = []
        
        # Parse each outline element
        outline_pattern = r'<outline[^>]*>'
        outlines = re.findall(outline_pattern, content)
        
        for outline in outlines:
            try:
                # Extract attributes
                xml_url = self._extract_attribute(outline, 'xmlUrl')
                if not xml_url:
                    continue
                
                title = self._extract_attribute(outline, 'title') or \
                        self._extract_attribute(outline, 'text') or \
                        xml_url
                
                html_url = self._extract_attribute(outline, 'htmlUrl')
                
                source = RSSSource(
                    title=title,
                    xml_url=xml_url,
                    html_url=html_url
                )
                sources.append(source)
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to parse outline: {outline[:100]}... Error: {e}")
                continue
        
        return sources
    
    def _extract_attribute(self, element_str: str, attr_name: str) -> Optional[str]:
        """Extract attribute value from element string.
        
        Args:
            element_str: Element string.
            attr_name: Attribute name.
        
        Returns:
            Attribute value or None.
        """
        # Pattern to match attribute="value" or attribute='value'
        pattern = rf'{attr_name}=["\']([^"\']+)["\']'
        match = re.search(pattern, element_str)
        if match:
            return match.group(1)
        return None
    
    def _parse_plain_text(self, content: str) -> List[RSSSource]:
        """Parse plain text format RSS sources (one URL per line).
        
        Args:
            content: Plain text content.
        
        Returns:
            List of RSSSource objects.
        """
        sources = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check if line looks like a URL
            if line.startswith('http://') or line.startswith('https://'):
                try:
                    # Extract domain as title
                    domain = re.search(r'https?://([^/]+)', line)
                    title = domain.group(1) if domain else line
                    
                    source = RSSSource(
                        title=title,
                        xml_url=line,
                        html_url=None
                    )
                    sources.append(source)
                    
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to parse line: {line}. Error: {e}")
                    continue
        
        return sources
    
    def get_sources(self) -> List[RSSSource]:
        """Get loaded RSS sources.
        
        Returns:
            List of RSSSource objects.
        """
        return self.sources
    
    def validate_sources(self) -> bool:
        """Validate loaded RSS sources.
        
        Returns:
            True if sources are valid, False otherwise.
        """
        if not self.sources:
            if self.logger:
                self.logger.error("No RSS sources loaded")
            return False
        
        valid_count = 0
        for source in self.sources:
            if source.xml_url and (source.xml_url.startswith('http://') or 
                                   source.xml_url.startswith('https://')):
                valid_count += 1
            else:
                if self.logger:
                    self.logger.warning(f"Invalid RSS source URL: {source.xml_url}")
        
        if self.logger:
            self.logger.info(f"Validated {valid_count}/{len(self.sources)} RSS sources")
        
        return valid_count > 0
