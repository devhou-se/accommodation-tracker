from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class AccommodationResult:
    """Represents a single accommodation with availability information."""
    accommodation_name: str
    available_dates: List[str]
    link: str
    location: str
    price_info: Optional[str] = None
    discovered_at: Optional[str] = None
    
    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.utcnow().isoformat() + "Z"


class BaseScraper(ABC):
    """Abstract base class for accommodation scrapers."""
    
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.logger = logger.bind(scraper=self.__class__.__name__)
    
    @abstractmethod
    async def check_availability(self, target_dates: List[str]) -> List[AccommodationResult]:
        """
        Check availability for the given dates.
        
        Args:
            target_dates: List of date strings in YYYY-MM-DD format
            
        Returns:
            List of AccommodationResult objects with availability information
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up any resources (browser instances, etc.)."""
        pass
    
    def filter_available_dates(self, target_dates: List[str], available_dates: List[str]) -> List[str]:
        """Filter available dates to only include target dates."""
        return [date for date in available_dates if date in target_dates]
    
    def log_availability_found(self, accommodation_name: str, dates: List[str]):
        """Log when availability is found."""
        self.logger.info(
            "Availability found",
            accommodation=accommodation_name,
            dates=dates,
            date_count=len(dates)
        )
    
    def log_no_availability(self, accommodation_name: str):
        """Log when no availability is found."""
        self.logger.info(
            "No availability found",
            accommodation=accommodation_name
        )
    
    def log_scraping_error(self, accommodation_name: str, error: str):
        """Log scraping errors."""
        self.logger.error(
            "Scraping error",
            accommodation=accommodation_name,
            error=error
        )