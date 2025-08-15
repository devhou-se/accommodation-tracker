from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BookingAvailability:
    """Represents booking availability for a specific accommodation/date"""
    date: str
    room_type: str
    status: str  # 'available', 'limited', 'fully_booked'
    price: Optional[str] = None
    booking_url: Optional[str] = None
    venue: Optional[str] = None


@dataclass
class CheckResult:
    """Result of checking booking availability"""
    plugin_name: str
    accommodation_name: str
    check_time: datetime
    availabilities: List[BookingAvailability]
    success: bool
    error_message: Optional[str] = None


class BookingPlugin(ABC):
    """Base class for booking availability checking plugins"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
    
    @abstractmethod
    async def check_availability(self) -> CheckResult:
        """Check booking availability and return results"""
        pass
    
    @abstractmethod
    def get_accommodation_info(self) -> Dict:
        """Get basic accommodation information"""
        pass


# Legacy aliases for backward compatibility
TicketAvailability = BookingAvailability
TicketPlugin = BookingPlugin