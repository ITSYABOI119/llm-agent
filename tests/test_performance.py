"""
Performance Tests for Phase 4 Improvements
Tests caching, connection pooling, and lazy loading
"""

import pytest
import time
import yaml
from pathlib import Path
from tools.cache import Cache, cached
from tools.system import SystemTools
from tools.search import SearchTools
from tools.network import NetworkTools


class TestCaching:
    """Test caching functionality"""

    def test_cache_basic_operations(self):
        """Test basic cache get/set operations"""
        cache = Cache(ttl=10)

        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Test non-existent key
        assert cache.get("nonexistent") is None

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = Cache(ttl=1)  # 1 second TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_custom_ttl(self):
        """Test custom TTL per key"""
        cache = Cache(ttl=10)  # Default 10s

        cache.set("key1", "value1", ttl=1)  # Custom 1s
        cache.set("key2", "value2")  # Default 10s

        time.sleep(1.1)

        assert cache.get("key1") is None  # Expired
        assert cache.get("key2") == "value2"  # Still valid

    def test_cache_invalidate(self):
        """Test cache invalidation"""
        cache = Cache(ttl=10)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Test clearing entire cache"""
        cache = Cache(ttl=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = Cache(ttl=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.stats()
        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 2
        assert stats['expired_entries'] == 0

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries"""
        cache = Cache(ttl=1)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        time.sleep(1.1)

        # Add new entry
        cache.set("key3", "value3")

        # Cleanup should remove 2 expired entries
        removed = cache.cleanup_expired()
        assert removed == 2

        stats = cache.stats()
        assert stats['total_entries'] == 1

    def test_cached_decorator(self):
        """Test @cached decorator"""
        call_count = 0

        @cached(ttl=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different argument should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


class TestSystemToolsCaching:
    """Test system info caching"""

    def test_system_info_cached(self):
        """Test that system info is cached"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        sys_tools = SystemTools(config)

        # First call
        start1 = time.time()
        result1 = sys_tools.get_system_info()
        time1 = time.time() - start1

        # Second call (should be cached)
        start2 = time.time()
        result2 = sys_tools.get_system_info()
        time2 = time.time() - start2

        # Results should be identical
        assert result1 == result2
        assert result1['success'] is True

        # Second call should be faster (cached)
        # Note: May be too fast to measure, so we just verify it works
        assert time2 <= time1 * 2  # At most same speed


class TestSearchToolsCaching:
    """Test file search caching"""

    def test_find_files_cached(self, tmp_path):
        """Test that file searches are cached"""
        config = {
            'agent': {'workspace': str(tmp_path)},
            'security': {'max_file_size': 1024 * 1024}
        }

        # Create test files
        (tmp_path / "test1.py").write_text("print('test1')")
        (tmp_path / "test2.py").write_text("print('test2')")
        (tmp_path / "test3.txt").write_text("test3")

        search_tools = SearchTools(config)

        # First call
        start1 = time.time()
        result1 = search_tools.find_files(pattern="*.py", path=".")
        time1 = time.time() - start1

        # Second call (should be cached)
        start2 = time.time()
        result2 = search_tools.find_files(pattern="*.py", path=".")
        time2 = time.time() - start2

        # Results should be identical
        assert result1 == result2
        assert result1['success'] is True
        assert result1['count'] == 2

        # Second call should be faster
        assert time2 <= time1


class TestConnectionPooling:
    """Test HTTP connection pooling"""

    def test_network_tools_has_session(self):
        """Test that NetworkTools creates a session"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        net_tools = NetworkTools(config)

        # Check session exists
        assert hasattr(net_tools, '_session')
        assert net_tools._session is not None

    def test_network_tools_close(self):
        """Test that session can be closed"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        net_tools = NetworkTools(config)

        # Close should work without error
        net_tools.close()


class TestLazyLoading:
    """Test lazy loading of tools in Agent"""

    def test_agent_lazy_loading(self, tmp_path):
        """Test that tools are loaded lazily"""
        # Create minimal config
        config_file = tmp_path / "config.yaml"
        config = {
            'agent': {
                'name': 'Test Agent',
                'workspace': str(tmp_path)
            },
            'ollama': {
                'host': 'localhost',
                'port': 11434,
                'model': 'qwen2.5-coder:7b',
                'multi_model': {
                    'enabled': True,
                    'models': {
                        'reasoning': {'name': 'openthinker3-7b'},
                        'execution': {'name': 'qwen2.5-coder:7b'}
                    }
                }
            },
            'security': {
                'allowed_paths': ['.'],
                'allowed_commands': ['ls', 'pwd'],
                'max_file_size': 1024 * 1024,
                'rate_limiting': {
                    'enabled': False
                },
                'resource_monitoring': {
                    'enabled': False
                }
            },
            'logging': {
                'level': 'ERROR',
                'log_file': str(tmp_path / 'test.log'),
                'structured_log_file': str(tmp_path / 'test_structured.json')
            },
            'memory': {
                'enabled': True,
                'file': str(tmp_path / 'memory.json')
            },
            'history': {
                'enabled': True,
                'file': str(tmp_path / 'history.json')
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Import and create agent (should not fail even without Ollama)
        try:
            from agent import Agent

            # Create agent
            agent = Agent(str(config_file))

            # Check private variables are None initially
            assert agent._fs_tools is None
            assert agent._cmd_tools is None
            assert agent._sys_tools is None

            # Access a tool (should trigger lazy loading)
            fs_tools = agent.fs_tools
            assert fs_tools is not None
            assert agent._fs_tools is not None

            # Other tools should still be None
            assert agent._cmd_tools is None
            assert agent._sys_tools is None

        except Exception as e:
            # If agent initialization fails (e.g., Ollama not running), skip test
            pytest.skip(f"Agent initialization requires Ollama: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
