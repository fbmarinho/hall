from collections import defaultdict

class EventEmitter:
    def __init__(self):
        self._v_listeners = defaultdict(list)

    def add_event_listener(self, event_name: str, callback: callable):
        """Register a callback for a specific event."""
        self._v_listeners[event_name].append(callback)

    def remove_event_listener(self, event_name: str, callback):
        """Remove a specific listener for a given event."""
        if callback in self._v_listeners[event_name]:
            self._v_listeners[event_name].remove(callback)

    def has_listeners_to_event(self, event_name:str):
        return len(self._v_listeners[event_name]) > 0

    async def emit(self, event_name: str, *args, **kwargs):
        """Invoke all listeners for the given event."""
        if event_name in self._v_listeners:
            for callback in self._v_listeners[event_name]:
                await callback(*args, **kwargs)
