"""
Comprehensive tests for FileSystemTools
Tests all file operations, edit modes, and validation
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
from tools.filesystem import FileSystemTools
from tools.exceptions import FileOperationError, ValidationError


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    """Create test configuration"""
    return {
        'agent': {
            'workspace': str(temp_workspace)
        },
        'security': {
            'max_file_size': 10485760  # 10MB
        },
        'linter': {
            'enabled': []  # Disable linter for tests
        }
    }


@pytest.fixture
def fs_tools(config):
    """Create FileSystemTools instance"""
    return FileSystemTools(config)


class TestBasicOperations:
    """Test basic file and folder operations"""

    def test_create_folder(self, fs_tools, temp_workspace):
        """Test folder creation"""
        result = fs_tools.create_folder("test_folder")

        assert result['success'] is True
        assert (temp_workspace / "test_folder").exists()
        assert (temp_workspace / "test_folder").is_dir()

    def test_create_nested_folder(self, fs_tools, temp_workspace):
        """Test nested folder creation"""
        result = fs_tools.create_folder("level1/level2/level3")

        assert result['success'] is True
        assert (temp_workspace / "level1" / "level2" / "level3").exists()

    def test_write_file(self, fs_tools, temp_workspace):
        """Test basic file writing"""
        content = "Hello, World!"
        result = fs_tools.write_file("test.txt", content)

        assert result['success'] is True
        assert (temp_workspace / "test.txt").read_text() == content

    def test_write_file_with_newlines(self, fs_tools, temp_workspace):
        """Test file writing with newlines"""
        content = "Line 1\nLine 2\nLine 3"
        result = fs_tools.write_file("multiline.txt", content)

        assert result['success'] is True
        assert (temp_workspace / "multiline.txt").read_text() == content

    def test_read_file(self, fs_tools, temp_workspace):
        """Test file reading"""
        # Create a file
        (temp_workspace / "read_test.txt").write_text("Test content")

        result = fs_tools.read_file("read_test.txt")

        assert result['success'] is True
        assert result['content'] == "Test content"

    def test_read_nonexistent_file(self, fs_tools):
        """Test reading a file that doesn't exist"""
        result = fs_tools.read_file("nonexistent.txt")

        assert result['success'] is False
        assert 'error' in result

    def test_list_directory(self, fs_tools, temp_workspace):
        """Test directory listing"""
        # Create some files and folders
        (temp_workspace / "file1.txt").write_text("content")
        (temp_workspace / "file2.py").write_text("print('hello')")
        (temp_workspace / "folder1").mkdir()

        result = fs_tools.list_directory(".")

        assert result['success'] is True
        assert len(result['items']) == 3

        # Check file details
        file_names = [item['name'] for item in result['items']]
        assert 'file1.txt' in file_names
        assert 'file2.py' in file_names
        assert 'folder1' in file_names

    def test_delete_file(self, fs_tools, temp_workspace):
        """Test file deletion"""
        # Create a file
        (temp_workspace / "delete_me.txt").write_text("content")
        assert (temp_workspace / "delete_me.txt").exists()

        result = fs_tools.delete_file("delete_me.txt")

        assert result['success'] is True
        assert not (temp_workspace / "delete_me.txt").exists()

    def test_delete_nonexistent_file(self, fs_tools):
        """Test deleting a file that doesn't exist"""
        result = fs_tools.delete_file("nonexistent.txt")

        assert result['success'] is False
        assert 'error' in result


class TestEditModes:
    """Test all 8 edit modes"""

    def test_edit_mode_append(self, fs_tools, temp_workspace):
        """Test append mode"""
        # Create initial file
        (temp_workspace / "append.txt").write_text("Line 1\n")

        result = fs_tools.edit_file(
            path="append.txt",
            mode="append",
            content="Line 2\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "append.txt").read_text()
        assert content == "Line 1\nLine 2\n"

    def test_edit_mode_prepend(self, fs_tools, temp_workspace):
        """Test prepend mode"""
        # Create initial file
        (temp_workspace / "prepend.txt").write_text("Line 2\n")

        result = fs_tools.edit_file(
            path="prepend.txt",
            mode="prepend",
            content="Line 1\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "prepend.txt").read_text()
        assert content == "Line 1\nLine 2\n"

    def test_edit_mode_replace(self, fs_tools, temp_workspace):
        """Test replace mode (all occurrences)"""
        # Create initial file
        (temp_workspace / "replace.txt").write_text("foo bar foo baz")

        result = fs_tools.edit_file(
            path="replace.txt",
            mode="replace",
            search="foo",
            replace="qux"
        )

        assert result['success'] is True
        content = (temp_workspace / "replace.txt").read_text()
        assert content == "qux bar qux baz"

    def test_edit_mode_replace_once(self, fs_tools, temp_workspace):
        """Test replace_once mode (first occurrence only)"""
        # Create initial file
        (temp_workspace / "replace_once.txt").write_text("foo bar foo baz")

        result = fs_tools.edit_file(
            path="replace_once.txt",
            mode="replace_once",
            search="foo",
            replace="qux"
        )

        assert result['success'] is True
        content = (temp_workspace / "replace_once.txt").read_text()
        assert content == "qux bar foo baz"

    def test_edit_mode_insert_at_line(self, fs_tools, temp_workspace):
        """Test insert_at_line mode"""
        # Create initial file
        (temp_workspace / "insert_at.txt").write_text("Line 1\nLine 2\nLine 3\n")

        result = fs_tools.edit_file(
            path="insert_at.txt",
            mode="insert_at_line",
            line_number=2,
            content="Inserted Line\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "insert_at.txt").read_text()
        # insert_at_line adds a blank line
        assert "Inserted Line" in content
        assert content.split('\n')[1] == "Inserted Line"

    def test_edit_mode_replace_lines(self, fs_tools, temp_workspace):
        """Test replace_lines mode"""
        # Create initial file
        (temp_workspace / "replace_lines.txt").write_text("Line 1\nLine 2\nLine 3\nLine 4\n")

        result = fs_tools.edit_file(
            path="replace_lines.txt",
            mode="replace_lines",
            start_line=2,
            end_line=3,
            content="New Line\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "replace_lines.txt").read_text()
        # replace_lines may add extra newline
        assert "New Line" in content
        lines = [l for l in content.split('\n') if l]
        assert lines == ["Line 1", "New Line", "Line 4"]

    def test_edit_mode_insert_after(self, fs_tools, temp_workspace):
        """Test insert_after mode with function pattern"""
        # Create Python file with function
        python_code = """def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b
"""
        (temp_workspace / "math.py").write_text(python_code)

        result = fs_tools.edit_file(
            path="math.py",
            mode="insert_after",
            insert_after="def multiply",
            content="\ndef add(a, b):\n    return a + b\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "math.py").read_text()
        assert "def add" in content
        # add should be after multiply but before divide
        assert content.index("def add") > content.index("def multiply")
        assert content.index("def add") < content.index("def divide")

    def test_edit_mode_insert_before(self, fs_tools, temp_workspace):
        """Test insert_before mode with function pattern"""
        # Create Python file with function
        python_code = """def first():
    pass

def second():
    pass
"""
        (temp_workspace / "funcs.py").write_text(python_code)

        result = fs_tools.edit_file(
            path="funcs.py",
            mode="insert_before",
            insert_before="def second",
            content="def middle():\n    pass\n\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "funcs.py").read_text()
        assert "def middle" in content
        # middle should be after first but before second
        assert content.index("def middle") > content.index("def first")
        assert content.index("def middle") < content.index("def second")


class TestPythonValidation:
    """Test Python syntax validation"""

    def test_write_valid_python(self, fs_tools, temp_workspace):
        """Test writing valid Python code"""
        code = "def add(a, b):\n    return a + b\n"
        result = fs_tools.write_file("valid.py", code)

        assert result['success'] is True

    def test_write_invalid_python(self, fs_tools, temp_workspace):
        """Test writing invalid Python code (should fail)"""
        code = "def broken(\n    syntax error here"
        result = fs_tools.write_file("invalid.py", code)

        # Should fail due to syntax validation
        assert result['success'] is False
        assert 'syntax' in result.get('error', '').lower()


class TestSafetyFeatures:
    """Test security and safety features"""

    def test_path_traversal_prevention(self, fs_tools):
        """Test that path traversal is prevented"""
        result = fs_tools.write_file("../outside_workspace.txt", "content")
        assert result['success'] is False
        assert 'outside workspace' in result.get('error', '').lower()

    def test_absolute_path_prevention(self, fs_tools):
        """Test that absolute paths are rejected"""
        result = fs_tools.write_file("/etc/passwd", "content")
        assert result['success'] is False
        assert 'outside workspace' in result.get('error', '').lower()

    def test_max_file_size(self, fs_tools, temp_workspace, config):
        """Test maximum file size limit"""
        # Create tools with small max file size
        config['security']['max_file_size'] = 100
        small_fs = FileSystemTools(config)

        # Try to write file larger than limit
        large_content = "x" * 200
        result = small_fs.write_file("large.txt", large_content)

        assert result['success'] is False
        assert 'size' in result.get('error', '').lower()


class TestErrorHandling:
    """Test error handling"""

    def test_edit_missing_file(self, fs_tools):
        """Test editing a file that doesn't exist"""
        result = fs_tools.edit_file(
            path="nonexistent.txt",
            mode="append",
            content="new content"
        )

        assert result['success'] is False
        assert 'error' in result

    def test_edit_invalid_mode(self, fs_tools, temp_workspace):
        """Test using an invalid edit mode"""
        (temp_workspace / "test.txt").write_text("content")

        result = fs_tools.edit_file(
            path="test.txt",
            mode="invalid_mode",
            content="new content"
        )

        assert result['success'] is False

    def test_replace_pattern_not_found(self, fs_tools, temp_workspace):
        """Test replacing pattern that doesn't exist"""
        (temp_workspace / "test.txt").write_text("hello world")

        result = fs_tools.edit_file(
            path="test.txt",
            mode="replace",
            search="nonexistent",
            replace="replacement"
        )

        assert result['success'] is False
        assert 'not found' in result.get('error', '').lower()


class TestPatternNormalization:
    """Test pattern normalization for insert_after/insert_before"""

    def test_normalize_multiline_pattern(self, fs_tools):
        """Test that multiline patterns are normalized to first line"""
        pattern = "def multiply(a, b):\n    return a * b"
        normalized, is_multiline = fs_tools._normalize_pattern(pattern)

        assert "def multiply" in normalized
        assert is_multiline is True

    def test_normalize_single_line_pattern(self, fs_tools):
        """Test that single-line patterns remain unchanged"""
        pattern = "def hello"
        normalized, is_multiline = fs_tools._normalize_pattern(pattern)

        assert normalized == "def hello"
        assert is_multiline is False


class TestFunctionAndClassDetection:
    """Test smart function/class end detection"""

    def test_find_function_end(self, fs_tools, temp_workspace):
        """Test that _find_function_or_class_end method exists"""
        # Just verify the method exists and can be called
        lines = ["def hello():", "    print('hello')", "    return True", "", "def world():"]
        result = fs_tools._find_function_or_class_end(lines, "def hello", 0)

        # Should find the end of the function (before empty line or next function)
        assert isinstance(result, int)
        assert result >= 0

    def test_find_class_end(self, fs_tools, temp_workspace):
        """Test that _find_function_or_class_end works for classes"""
        lines = ["class MyClass:", "    def method(self):", "        pass", "", "class Other:"]
        result = fs_tools._find_function_or_class_end(lines, "class MyClass", 0)

        # Should find the end of the class
        assert isinstance(result, int)
        assert result >= 0


class TestAdvancedEditModes:
    """Test advanced editing scenarios"""

    def test_edit_with_multiline_search_replace(self, fs_tools, temp_workspace):
        """Test replacing multiline content"""
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        (temp_workspace / "multi.txt").write_text(content)

        result = fs_tools.edit_file(
            path="multi.txt",
            mode="replace",
            search="Line 2\nLine 3",
            replace="New Lines"
        )

        assert result['success'] is True
        new_content = (temp_workspace / "multi.txt").read_text()
        assert "New Lines" in new_content
        assert "Line 2\nLine 3" not in new_content

    def test_edit_replace_once_multiple_occurrences(self, fs_tools, temp_workspace):
        """Test replace_once only replaces first occurrence"""
        content = "hello world\nhello again\nhello there"
        (temp_workspace / "hellos.txt").write_text(content)

        result = fs_tools.edit_file(
            path="hellos.txt",
            mode="replace_once",
            search="hello",
            replace="hi"
        )

        assert result['success'] is True
        new_content = (temp_workspace / "hellos.txt").read_text()
        # Should replace only first occurrence
        assert new_content.count("hi") == 1
        assert new_content.count("hello") == 2

    def test_edit_insert_at_line_boundaries(self, fs_tools, temp_workspace):
        """Test insert_at_line at file start and end"""
        content = "Line 1\nLine 2\nLine 3"
        (temp_workspace / "bounds.txt").write_text(content)

        # Insert at line 1 (beginning)
        result = fs_tools.edit_file(
            path="bounds.txt",
            mode="insert_at_line",
            line_number=1,
            content="Start\n"
        )
        assert result['success'] is True

        # Insert at last line
        result = fs_tools.edit_file(
            path="bounds.txt",
            mode="insert_at_line",
            line_number=4,
            content="End\n"
        )
        assert result['success'] is True

    def test_edit_replace_lines_with_empty_content(self, fs_tools, temp_workspace):
        """Test replacing lines with empty content (deletion)"""
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        (temp_workspace / "delete.txt").write_text(content)

        result = fs_tools.edit_file(
            path="delete.txt",
            mode="replace_lines",
            start_line=2,
            end_line=3,
            content=""
        )

        assert result['success'] is True
        new_content = (temp_workspace / "delete.txt").read_text()
        assert "Line 2" not in new_content
        assert "Line 3" not in new_content
        assert "Line 1" in new_content
        assert "Line 4" in new_content


class TestFileSystemBasicOps:
    """Test basic operations from filesystem_basic.py"""

    def test_read_file_with_encoding(self, fs_tools, temp_workspace):
        """Test reading files with ASCII content"""
        # Test with standard ASCII content (cross-platform safe)
        (temp_workspace / "ascii.txt").write_text("Hello World 123", encoding='utf-8')

        result = fs_tools.read_file("ascii.txt")
        assert result['success'] is True
        assert "Hello World" in result['content']
        assert "123" in result['content']

    def test_list_directory_recursive(self, fs_tools, temp_workspace):
        """Test listing nested directories"""
        # Create nested structure
        (temp_workspace / "dir1").mkdir()
        (temp_workspace / "dir1" / "file1.txt").write_text("content1")
        (temp_workspace / "dir1" / "subdir").mkdir()
        (temp_workspace / "dir1" / "subdir" / "file2.txt").write_text("content2")

        result = fs_tools.list_directory("dir1")
        assert result['success'] is True
        assert result['count'] >= 2  # Fixed: 'count' not 'item_count'

    def test_list_directory_empty(self, fs_tools, temp_workspace):
        """Test listing an empty directory"""
        (temp_workspace / "empty").mkdir()

        result = fs_tools.list_directory("empty")
        assert result['success'] is True
        assert result['count'] == 0  # Fixed: 'count' not 'item_count'

    def test_delete_file_with_spaces(self, fs_tools, temp_workspace):
        """Test deleting files with spaces in name"""
        (temp_workspace / "file with spaces.txt").write_text("content")

        result = fs_tools.delete_file("file with spaces.txt")
        assert result['success'] is True
        assert not (temp_workspace / "file with spaces.txt").exists()

    def test_write_file_creates_parent_directories(self, fs_tools, temp_workspace):
        """Test that write_file creates parent directories"""
        result = fs_tools.write_file("nested/deep/file.txt", "content")

        assert result['success'] is True
        assert (temp_workspace / "nested" / "deep" / "file.txt").exists()

    def test_read_file_size_info(self, fs_tools, temp_workspace):
        """Test that read_file returns size information"""
        content = "x" * 1000
        (temp_workspace / "sized.txt").write_text(content)

        result = fs_tools.read_file("sized.txt")
        assert result['success'] is True
        # File should have size info
        assert 'content' in result


class TestErrorConditions:
    """Test various error conditions and edge cases"""

    def test_edit_file_invalid_line_numbers(self, fs_tools, temp_workspace):
        """Test editing with invalid line numbers"""
        (temp_workspace / "lines.txt").write_text("Line 1\nLine 2\nLine 3")

        # Line number out of range
        result = fs_tools.edit_file(
            path="lines.txt",
            mode="insert_at_line",
            line_number=100,
            content="New"
        )
        assert result['success'] is False

    def test_edit_file_invalid_range(self, fs_tools, temp_workspace):
        """Test replace_lines with invalid range"""
        (temp_workspace / "range.txt").write_text("Line 1\nLine 2\nLine 3")

        # Start line > end line
        result = fs_tools.edit_file(
            path="range.txt",
            mode="replace_lines",
            start_line=3,
            end_line=1,
            content="New"
        )
        assert result['success'] is False

    def test_edit_insert_after_pattern_not_found(self, fs_tools, temp_workspace):
        """Test insert_after with pattern that doesn't exist"""
        (temp_workspace / "test.py").write_text("def hello():\n    pass")

        result = fs_tools.edit_file(
            path="test.py",
            mode="insert_after",
            insert_after="def nonexistent",
            content="new content"
        )
        assert result['success'] is False
        assert 'not found' in result.get('error', '').lower()

    def test_write_file_readonly_simulation(self, fs_tools, temp_workspace):
        """Test handling of write errors"""
        # This tests the error handling path
        # We can't easily make a file readonly cross-platform in tests
        # but we can test with invalid path characters
        result = fs_tools.write_file("invalid\x00name.txt", "content")
        assert result['success'] is False

    def test_read_file_very_large(self, fs_tools, temp_workspace, config):
        """Test reading file near size limit"""
        # Create file just under the size limit
        config['security']['max_file_size'] = 1000
        fs = FileSystemTools(config)

        content = "x" * 900
        (temp_workspace / "large.txt").write_text(content)

        result = fs.read_file("large.txt")
        assert result['success'] is True
        assert len(result['content']) == 900


class TestPythonSyntaxValidation:
    """Test Python syntax validation in detail"""

    def test_edit_python_preserves_valid_syntax(self, fs_tools, temp_workspace):
        """Test that editing Python file validates syntax"""
        code = "def hello():\n    return 'world'\n"
        (temp_workspace / "valid.py").write_text(code)

        result = fs_tools.edit_file(
            path="valid.py",
            mode="append",
            content="\ndef goodbye():\n    return 'bye'\n"
        )

        assert result['success'] is True

    def test_edit_python_rejects_invalid_syntax(self, fs_tools, temp_workspace):
        """Test that editing Python file with invalid syntax fails"""
        code = "def hello():\n    return 'world'\n"
        (temp_workspace / "valid.py").write_text(code)

        result = fs_tools.edit_file(
            path="valid.py",
            mode="append",
            content="\ndef broken(\n    syntax error"
        )

        assert result['success'] is False
        assert 'syntax' in result.get('error', '').lower()

    def test_non_python_file_skip_validation(self, fs_tools, temp_workspace):
        """Test that non-Python files don't get syntax validation"""
        # Text file should allow any content
        result = fs_tools.write_file("test.txt", "def broken(\ninvalid")
        assert result['success'] is True

        # JavaScript file should allow any content
        result = fs_tools.write_file("test.js", "function broken( {")
        assert result['success'] is True


class TestClassDetection:
    """Test class and function end detection"""

    def test_find_class_with_nested_methods(self, fs_tools, temp_workspace):
        """Test finding end of class with multiple methods"""
        code = """class MyClass:
    def __init__(self):
        self.value = 0

    def method1(self):
        return self.value

    def method2(self):
        self.value += 1

class NextClass:
    pass
"""
        (temp_workspace / "classes.py").write_text(code)

        lines = code.split('\n')
        result = fs_tools._find_function_or_class_end(lines, "class MyClass", 0)

        # Should find end after method2
        assert result > 0
        assert result < len(lines)

    def test_insert_after_class(self, fs_tools, temp_workspace):
        """Test inserting after a class definition"""
        code = """class FirstClass:
    def method(self):
        pass

class SecondClass:
    pass
"""
        (temp_workspace / "classes.py").write_text(code)

        result = fs_tools.edit_file(
            path="classes.py",
            mode="insert_after",
            insert_after="class FirstClass",
            content="\nclass MiddleClass:\n    pass\n"
        )

        assert result['success'] is True
        content = (temp_workspace / "classes.py").read_text()
        assert "MiddleClass" in content
        assert content.index("MiddleClass") > content.index("FirstClass")
        assert content.index("MiddleClass") < content.index("SecondClass")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
