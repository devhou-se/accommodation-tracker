from .base import BookingPlugin, BookingAvailability, CheckResult, TicketPlugin, TicketAvailability
from .sumo_plugin import SumoPlugin
from .direct_booking_plugin import DirectBookingPlugin

# Plugin registry
AVAILABLE_PLUGINS = {
    "sumo": SumoPlugin,
    "direct_booking": DirectBookingPlugin
}

def create_plugin(plugin_type: str, config: dict) -> BookingPlugin:
    """Factory function to create plugin instances"""
    if plugin_type not in AVAILABLE_PLUGINS:
        raise ValueError(f"Unknown plugin type: {plugin_type}")
    
    return AVAILABLE_PLUGINS[plugin_type](config)