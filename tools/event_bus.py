"""
Event Bus for Streaming Execution

Provides real-time event broadcasting for streaming execution progress.
Events can be consumed by CLI progress indicators, web UIs, or logging systems.
"""

from typing import Callable, Dict, Any, List
from datetime import datetime
import logging


class EventBus:
    """Central event bus for streaming execution events"""

    def __init__(self):
        self.subscribers: List[Callable] = []
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 1000  # Keep last 1000 events

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Subscribe to events

        Args:
            callback: Function to call with each event
        """
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Remove a subscriber"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event to all subscribers

        Args:
            event_type: Type of event (status, thinking, tool_call, tool_result, complete)
            data: Event data dictionary
        """
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logging.error(f"Error in event subscriber: {e}")

    def clear_history(self):
        """Clear event history"""
        self.event_history = []

    def get_history(self, event_type: str = None) -> List[Dict[str, Any]]:
        """
        Get event history, optionally filtered by type

        Args:
            event_type: Filter by event type, or None for all events

        Returns:
            List of events
        """
        if event_type:
            return [e for e in self.event_history if e['type'] == event_type]
        return self.event_history.copy()


# Global event bus instance
_global_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
