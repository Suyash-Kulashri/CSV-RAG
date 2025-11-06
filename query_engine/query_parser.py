"""
Query parser for understanding user questions and extracting entities.
"""
import re
from typing import Dict, List, Optional, Set


class QueryParser:
    """Parse user queries to extract entities and determine query intent."""
    
    def __init__(self):
        """Initialize the query parser."""
        # Common patterns for part numbers (alphanumeric codes)
        self.part_patterns = [
            r'\b[A-Z]{2,}\d{3,}\b',  # e.g., TRNBRG00104, ABC12345
            r'\b\d{4,}[A-Z]{1,}\b',  # e.g., 1234ABC
            r'#[A-Z0-9]+',  # e.g., #TRNBRG00104
            r'parts?\s+town\s+#?\s*([A-Z0-9]+)',  # e.g., "parts town #TRNBRG00104"
            r'part\s+#?\s*([A-Z0-9]+)',  # e.g., "part #TRNBRG00104"
        ]
        
        # Common patterns for model names (usually alphanumeric with dashes/underscores)
        self.model_patterns = [
            r'\b[A-Z0-9]+[-_][A-Z0-9]+\b',  # e.g., TUD-123, ABC_456
            r'model\s+([A-Z0-9-]+)',  # e.g., "model TUD-123"
        ]
    
    def parse(self, query: str) -> Dict:
        """
        Parse a user query to extract entities and determine intent.
        
        Args:
            query: User's query string
            
        Returns:
            Dictionary with:
            - intent: 'part', 'model', 'general', or 'comparison'
            - parts_town_numbers: List of extracted Parts Town # values
            - manufacturer_numbers: List of extracted manufacturer numbers
            - model_names: List of extracted model names
            - query_text: Original query text
            - keywords: Important keywords from the query
        """
        query_lower = query.lower()
        
        # Extract Parts Town numbers
        parts_town_numbers = self._extract_parts_town_numbers(query)
        
        # Extract manufacturer numbers (similar patterns)
        manufacturer_numbers = self._extract_manufacturer_numbers(query)
        
        # Extract model names
        model_names = self._extract_model_names(query)
        
        # Determine intent
        intent = self._determine_intent(
            query_lower, 
            parts_town_numbers, 
            manufacturer_numbers, 
            model_names
        )
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        return {
            'intent': intent,
            'parts_town_numbers': parts_town_numbers,
            'manufacturer_numbers': manufacturer_numbers,
            'model_names': model_names,
            'query_text': query,
            'keywords': keywords
        }
    
    def _extract_parts_town_numbers(self, query: str) -> List[str]:
        """Extract Parts Town # values from query."""
        found = set()
        
        # Try each pattern
        for pattern in self.part_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Pattern with capture group
                    found.add(match[0].upper())
                else:
                    found.add(match.upper())
        
        # Also look for explicit "Parts Town #" mentions
        parts_town_pattern = r'parts?\s+town\s*#?\s*([A-Z0-9]+)'
        matches = re.findall(parts_town_pattern, query, re.IGNORECASE)
        found.update([m.upper() for m in matches])
        
        return list(found)
    
    def _extract_manufacturer_numbers(self, query: str) -> List[str]:
        """Extract manufacturer numbers from query."""
        found = set()
        
        # Look for "manufacturer #" or "mfr #" patterns
        patterns = [
            r'manufacturer\s*#?\s*([A-Z0-9]+)',
            r'mfr\s*#?\s*([A-Z0-9]+)',
            r'manufacturer\s+number\s+([A-Z0-9]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            found.update([m.upper() for m in matches])
        
        return list(found)
    
    def _extract_model_names(self, query: str) -> List[str]:
        """Extract model names from query."""
        found = set()
        
        # Try each pattern
        for pattern in self.model_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    found.add(match[0].upper())
                else:
                    found.add(match.upper())
        
        # Also look for explicit "model" mentions
        model_pattern = r'model\s+([A-Z0-9-_]+)'
        matches = re.findall(model_pattern, query, re.IGNORECASE)
        found.update([m.upper() for m in matches])
        
        return list(found)
    
    def _determine_intent(self, 
                         query_lower: str, 
                         parts_town_numbers: List[str],
                         manufacturer_numbers: List[str],
                         model_names: List[str]) -> str:
        """Determine the intent of the query."""
        # If specific part/model mentioned, prioritize that
        if parts_town_numbers or manufacturer_numbers:
            return 'part'
        
        if model_names:
            return 'model'
        
        # Check for comparison queries
        comparison_keywords = ['compare', 'difference', 'vs', 'versus', 'between']
        if any(kw in query_lower for kw in comparison_keywords):
            return 'comparison'
        
        # Check for part-related keywords
        part_keywords = ['part', 'parts', 'component', 'bearing', 'valve', 'sensor']
        if any(kw in query_lower for kw in part_keywords):
            return 'part'
        
        # Check for model-related keywords
        model_keywords = ['model', 'unit', 'system', 'equipment']
        if any(kw in query_lower for kw in model_keywords):
            return 'model'
        
        # Default to general
        return 'general'
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query."""
        # Common stopwords to ignore
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'can', 'what', 'which', 'who',
            'where', 'when', 'why', 'how', 'this', 'that', 'these', 'those'
        }
        
        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
        
        # Filter out stopwords and short words
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
