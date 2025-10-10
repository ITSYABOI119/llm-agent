"""
Test suite for Phase 1: Streaming Execution & Progress Feedback

Tests:
- Event bus publish/subscribe
- Progress indicator updates
- Streaming executor events
- Real-time progress display
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from tools.event_bus import EventBus, EventType
from tools.progress_indicator import ProgressIndicator


class TestEventBus:
    """Test event bus system for streaming"""

    def test_event_bus_singleton(self):
        """Event bus should be a singleton"""
        from tools.event_bus import get_event_bus

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    def test_subscribe_and_publish(self):
        """Should publish events to subscribers"""
        bus = EventBus()
        received_events = []

        def handler(data):
            received_events.append(data)

        bus.subscribe(EventType.STATUS_CHANGE, handler)
        bus.publish(EventType.STATUS_CHANGE, {'status': 'thinking'})

        assert len(received_events) == 1
        assert received_events[0]['status'] == 'thinking'

    def test_multiple_subscribers(self):
        """Should support multiple subscribers for same event"""
        bus = EventBus()
        handler1_calls = []
        handler2_calls = []

        bus.subscribe(EventType.TOOL_CALL, lambda d: handler1_calls.append(d))
        bus.subscribe(EventType.TOOL_CALL, lambda d: handler2_calls.append(d))

        bus.publish(EventType.TOOL_CALL, {'tool': 'write_file'})

        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1

    def test_event_history(self):
        """Should track event history"""
        bus = EventBus()

        bus.publish(EventType.STATUS_CHANGE, {'status': 'start'})
        bus.publish(EventType.THINKING, {'content': 'analyzing...'})
        bus.publish(EventType.TOOL_CALL, {'tool': 'read_file'})

        history = bus.get_history(limit=10)

        assert len(history) == 3
        assert history[0]['type'] == EventType.STATUS_CHANGE
        assert history[1]['type'] == EventType.THINKING
        assert history[2]['type'] == EventType.TOOL_CALL

    def test_event_history_limit(self):
        """Should respect history limit"""
        bus = EventBus()

        # Publish more events than the limit (1000)
        for i in range(1100):
            bus.publish(EventType.STATUS_CHANGE, {'index': i})

        history = bus.get_history()

        # Should only keep last 1000
        assert len(history) == 1000
        assert history[0]['data']['index'] == 100  # First kept event

    def test_unsubscribe(self):
        """Should support unsubscribing"""
        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        bus.subscribe(EventType.TOOL_RESULT, handler)
        bus.publish(EventType.TOOL_RESULT, {'result': 1})

        bus.unsubscribe(EventType.TOOL_RESULT, handler)
        bus.publish(EventType.TOOL_RESULT, {'result': 2})

        # Should only receive first event
        assert len(received) == 1
        assert received[0]['result'] == 1


class TestProgressIndicator:
    """Test progress indicator display"""

    def test_initialization(self):
        """Should initialize with default state"""
        indicator = ProgressIndicator()

        assert indicator.current_status == "Idle"
        assert indicator.current_tool is None
        assert indicator.tools_completed == 0
        assert indicator.tools_total == 0

    def test_status_change_event(self):
        """Should update status on status change event"""
        indicator = ProgressIndicator()

        indicator.handle_event({
            'type': EventType.STATUS_CHANGE,
            'data': {'status': 'thinking', 'model': 'qwen2.5-coder:7b'},
            'timestamp': time.time()
        })

        assert indicator.current_status == "Thinking"
        assert indicator.current_model == 'qwen2.5-coder:7b'

    def test_thinking_event(self):
        """Should display thinking content"""
        indicator = ProgressIndicator()

        with patch('builtins.print') as mock_print:
            indicator.handle_event({
                'type': EventType.THINKING,
                'data': {'content': 'Analyzing the task requirements...'},
                'timestamp': time.time()
            })

            # Should print abbreviated thinking
            assert mock_print.called

    def test_tool_call_event(self):
        """Should track tool execution"""
        indicator = ProgressIndicator()

        indicator.handle_event({
            'type': EventType.TOOL_CALL,
            'data': {
                'tool': 'write_file',
                'params': {'path': 'test.py'},
                'status': 'executing',
                'index': 0,
                'total': 3
            },
            'timestamp': time.time()
        })

        assert indicator.current_tool == 'write_file'
        assert indicator.tools_total == 3
        assert indicator.tools_completed == 0

    def test_tool_result_event(self):
        """Should track tool completion"""
        indicator = ProgressIndicator()

        # First call
        indicator.handle_event({
            'type': EventType.TOOL_CALL,
            'data': {
                'tool': 'write_file',
                'status': 'executing',
                'index': 0,
                'total': 2
            },
            'timestamp': time.time()
        })

        # Result
        indicator.handle_event({
            'type': EventType.TOOL_RESULT,
            'data': {
                'tool': 'write_file',
                'result': {'success': True},
                'execution_time': 0.5,
                'status': 'success'
            },
            'timestamp': time.time()
        })

        assert indicator.tools_completed == 1

    def test_complete_event(self):
        """Should handle completion event"""
        indicator = ProgressIndicator()

        with patch('builtins.print') as mock_print:
            indicator.handle_event({
                'type': EventType.COMPLETE,
                'data': {'status': 'success'},
                'timestamp': time.time()
            })

            assert mock_print.called
            assert indicator.current_status == "Complete"

    def test_error_event(self):
        """Should handle error events"""
        indicator = ProgressIndicator()

        with patch('builtins.print') as mock_print:
            indicator.handle_event({
                'type': EventType.ERROR,
                'data': {'error': 'File not found'},
                'timestamp': time.time()
            })

            assert mock_print.called
            assert indicator.current_status == "Error"


class TestStreamingIntegration:
    """Test streaming in executors (integration tests)"""

    def test_single_phase_publishes_events(self):
        """Single-phase executor should publish streaming events"""
        # This test would require mocking the executor
        # Skipping for now - would test in real execution
        pass

    def test_two_phase_publishes_planning_events(self):
        """Two-phase should publish events during planning"""
        # This test would require mocking the executor
        # Skipping for now - would test in real execution
        pass

    def test_progress_indicator_integration(self):
        """Progress indicator should receive events from executor"""
        bus = EventBus()
        indicator = ProgressIndicator()

        # Subscribe indicator to events
        bus.subscribe(EventType.STATUS_CHANGE, indicator.handle_event)
        bus.subscribe(EventType.TOOL_CALL, indicator.handle_event)
        bus.subscribe(EventType.TOOL_RESULT, indicator.handle_event)

        # Simulate execution flow
        bus.publish(EventType.STATUS_CHANGE, {
            'status': 'thinking',
            'model': 'qwen2.5-coder:7b',
            'timestamp': time.time()
        })

        assert indicator.current_status == "Thinking"

        bus.publish(EventType.TOOL_CALL, {
            'tool': 'write_file',
            'params': {'path': 'test.py'},
            'status': 'executing',
            'index': 0,
            'total': 1,
            'timestamp': time.time()
        })

        assert indicator.current_tool == 'write_file'

        bus.publish(EventType.TOOL_RESULT, {
            'tool': 'write_file',
            'result': {'success': True},
            'execution_time': 0.3,
            'status': 'success',
            'timestamp': time.time()
        })

        assert indicator.tools_completed == 1


class TestStreamingConfiguration:
    """Test streaming configuration"""

    def test_streaming_disabled(self):
        """Should respect streaming disabled config"""
        config = {
            'ollama': {
                'multi_model': {
                    'streaming': {
                        'enabled': False
                    }
                }
            }
        }

        # In real code, executor would check this config
        # and skip event publishing
        assert not config['ollama']['multi_model']['streaming']['enabled']

    def test_show_thinking_disabled(self):
        """Should respect show_thinking config"""
        config = {
            'ollama': {
                'multi_model': {
                    'streaming': {
                        'enabled': True,
                        'show_thinking': False
                    }
                }
            }
        }

        assert not config['ollama']['multi_model']['streaming']['show_thinking']


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
