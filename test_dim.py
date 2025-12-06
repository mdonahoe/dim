#!/usr/bin/env python3
"""
Test suite for dim editor using unittest framework
"""

import sys
import os
import unittest

# Import testty functions
sys.path.insert(0, os.path.dirname(__file__))
from testty import run_with_pty, parse_input_string


class TestDimQuit(unittest.TestCase):
    """Tests for quit functionality."""

    def test_cannot_quit_with_unsaved_changes(self):
        """Test that ctrl-q doesn't immediately quit when there are unsaved changes."""
        # Create a new file with some content, then try to quit without saving
        input_str = "Hello, World![ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Check that the warning message appears
        self.assertIn("WARNING", result.output, "Expected WARNING message when trying to quit with unsaved changes")
        self.assertIn("unsaved changes", result.output, "Expected 'unsaved changes' in warning message")
        self.assertIn("Press Ctrl-Q", result.output, "Expected instruction to press Ctrl-Q multiple times")

        # Check that we're still in the editor (not quit)
        self.assertIn("Hello, World!", result.output, "Expected editor content to still be visible")

        # IMPORTANT: Check that the process did NOT exit
        self.assertFalse(result.did_exit, "Editor should NOT have exited with unsaved changes after one Ctrl-Q")

    def test_quit_after_multiple_ctrl_q(self):
        """Test that pressing ctrl-q 4 times will quit even with unsaved changes."""
        # Create content and press ctrl-q 4 times (3 warnings + 1 to actually quit)
        input_str = "Some content[ctrl-q][ctrl-q][ctrl-q][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After 4 ctrl-q presses, the editor SHOULD have exited
        self.assertTrue(result.did_exit, "Editor should have exited after 4 Ctrl-Q presses with unsaved changes")
        self.assertEqual(result.exit_code, 0, f"Editor should exit with code 0, got {result.exit_code}")

    def test_quit_immediately_without_changes(self):
        """Test that ctrl-q quits immediately when there are no unsaved changes."""
        # Open an existing file and quit immediately without making changes
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "example.py"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should not see warning message about unsaved changes
        self.assertNotIn("unsaved changes", result.output,
                        "Should not show warning when no changes were made")

        # Should show the file content (snapshot taken before quit)
        self.assertIn("example.py", result.output, "Should show the filename")
        self.assertIn("python", result.output, "Should show python filetype")

        # Should have exited immediately
        self.assertTrue(result.did_exit, "Editor should have exited immediately without unsaved changes")
        self.assertEqual(result.exit_code, 0, f"Editor should exit with code 0, got {result.exit_code}")

    def test_warning_countdown(self):
        """Test that the warning shows the correct countdown (3, 2, 1)."""
        # Press ctrl-q once and check the countdown
        input_str = "Content[ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # First ctrl-q should show "Press Ctrl-Q 3 more times"
        # (quit_times starts at 3, shows message with current value)
        self.assertIn("3 more times", result.output,
                     f"Expected '3 more times' in warning message")


class TestDimSave(unittest.TestCase):
    """Tests for save functionality."""

    def test_save_then_quit(self):
        """Test that saving changes allows immediate quit."""
        # Create a test file, make changes, save, then quit
        input_str = "Test content[ctrl-s]test_output.txt[enter][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see "written to disk" message
        self.assertIn("written to disk", result.output, "Expected save confirmation message")

        # Should not see unsaved changes warning
        self.assertNotIn("unsaved changes", result.output,
                        "Should not warn about unsaved changes after saving")

        # Clean up the test file
        if os.path.exists("test_output.txt"):
            os.remove("test_output.txt")

    def test_save_new_file_creates_file(self):
        """Test that saving a new file with Ctrl-S creates the file on disk."""
        # Type content, save as test_new_file.txt, then quit
        input_str = "New file content[ctrl-s]test_new_file.txt[enter][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see save confirmation
        self.assertIn("written to disk", result.output, "Expected save confirmation message")

        # File should exist on disk
        self.assertTrue(os.path.exists("test_new_file.txt"), "Expected file to be created on disk")

        # Verify file contents
        with open("test_new_file.txt", "r") as f:
            contents = f.read()
            self.assertIn("New file content", contents, "Expected file to contain typed content")

        # Clean up
        os.remove("test_new_file.txt")

        # Should have exited cleanly
        self.assertTrue(result.did_exit, "Editor should have exited")
        self.assertEqual(result.exit_code, 0, f"Editor should exit with code 0, got {result.exit_code}")


class TestDimFileOperations(unittest.TestCase):
    """Tests for file opening and viewing."""

    def test_open_file_and_view_contents(self):
        """Test that dim can open a file and display its contents."""
        # Open hello_world.txt and wait briefly to let it render
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Check that file contents are visible
        self.assertIn("Hello, World!", result.output, "Expected to see 'Hello, World!' in file contents")
        self.assertIn("This is a test file", result.output, "Expected to see second line of file")
        self.assertIn("Line 3: Testing line display", result.output, "Expected to see third line")

        # Should have exited cleanly
        self.assertTrue(result.did_exit, "Editor should have exited")
        self.assertEqual(result.exit_code, 0, f"Editor should exit with code 0, got {result.exit_code}")

    def test_open_new_file_shows_no_name(self):
        """Test that opening dim without a file shows '[No Name]' in status bar."""
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should show [No Name] in status bar
        self.assertIn("[No Name]", result.output, "Expected '[No Name]' in status bar for new file")
        self.assertIn("0 lines", result.output, "Expected '0 lines' for empty new file")

    def test_open_readme_and_view_first_line(self):
        """Test that dim can open README.md and display its first line."""
        # Open README.md and wait briefly to let it render
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "README.md"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Check that the first line of README is visible
        self.assertIn("dim", result.output, "Expected to see 'dim' (first line of README)")
        self.assertIn("README.md", result.output, "Expected to see 'README.md' filename in status bar")

        # Should have exited cleanly
        self.assertTrue(result.did_exit, "Editor should have exited")
        self.assertEqual(result.exit_code, 0, f"Editor should exit with code 0, got {result.exit_code}")


class TestDimStatusBar(unittest.TestCase):
    """Tests for status bar functionality."""

    def test_status_bar_shows_filename_and_lines(self):
        """Test that the status bar displays filename, line count, and filetype."""
        # Open hello_world.txt
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Status bar should show filename and line count
        self.assertIn("hello_world.txt", result.output, "Expected filename in status bar")
        self.assertIn("5 lines", result.output, "Expected '5 lines' in status bar (file has 5 lines)")

        # Should show "no ft" (no filetype) since .txt doesn't have syntax highlighting
        self.assertIn("no ft", result.output, "Expected 'no ft' for .txt file")

        # Should show current line position (1/5 since we start at line 1)
        self.assertIn("1/5", result.output, "Expected '1/5' showing current line position")

    def test_status_bar_shows_python_filetype(self):
        """Test that the status bar shows 'python' filetype for .py files."""
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "example.py"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should show filename and python filetype
        self.assertIn("example.py", result.output, "Expected 'example.py' filename in status bar")
        self.assertIn("python", result.output, "Expected 'python' filetype in status bar")

    def test_modified_indicator_in_status_bar(self):
        """Test that the status bar shows '(modified)' when file is edited."""
        # Open file, make a change, check for (modified) indicator
        input_str = "[sleep:50]x[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After typing 'x', file should be marked as modified
        self.assertIn("(modified)", result.output,
                     "Expected '(modified)' indicator in status bar after editing")

        # Should also see the warning about unsaved changes when trying to quit
        self.assertIn("unsaved changes", result.output, "Expected warning about unsaved changes")


class TestDimSyntaxHighlighting(unittest.TestCase):
    """Tests for syntax highlighting."""

    def test_syntax_highlighting_python(self):
        """Test that Python syntax highlighting works for keywords, strings, and comments."""
        # Open example.py and wait for it to render
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "example.py"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Check that Python content is visible
        self.assertIn("def hello_world", result.output, "Expected to see function definition")
        self.assertIn("class TestClass", result.output, "Expected to see class definition")
        self.assertIn("print", result.output, "Expected to see print statement")

        # The file should be recognized as Python
        self.assertIn("python", result.output, "Expected 'python' filetype in status bar")

        # Check for explicit highlighted sequences in raw output
        # Color code 33 = yellow (for keywords like def, class, if, return, etc.)
        # Color code 35 = magenta (for strings like "Hello, World!")
        # Color code 36 = cyan (for comments/docstrings like """...""")
        raw_str = result.raw.decode('utf-8', errors='ignore')

        # Check that specific keywords are highlighted in yellow (33m) followed by reset to white (37m)
        self.assertIn("\x1b[33mdef\x1b[37m", raw_str,
                     "Expected keyword 'def' to be highlighted in yellow (33m -> 37m)")
        self.assertIn("\x1b[33mclass\x1b[37m", raw_str,
                     "Expected keyword 'class' to be highlighted in yellow (33m -> 37m)")

        # Check that strings are highlighted in magenta (35m)
        # The string content should start with the color code
        self.assertIn('\x1b[35m"Hello, World!"', raw_str,
                     "Expected string '\"Hello, World!\"' to be highlighted in magenta (35m)")

        # Check that docstrings/comments are highlighted in cyan (36m)
        self.assertIn('\x1b[36m"""', raw_str,
                     "Expected docstring '\"\"\"' to be highlighted in cyan (36m)")

    def test_syntax_highlighting_c(self):
        """Test that C syntax highlighting works with color codes."""
        # Open example.c and wait for it to render
        input_str = "[sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "example.c"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Check that C content is visible
        self.assertIn("int main", result.output, "Expected to see main function")
        self.assertIn("#include", result.output, "Expected to see include directive")
        self.assertIn("printf", result.output, "Expected to see printf call")

        # The file should be recognized as C
        self.assertIn("example.c", result.output, "Expected filename in status bar")
        self.assertIn("c", result.output.lower(), "Expected 'c' filetype in status bar")

        # Check for explicit highlighted sequences in raw output
        # Color code 33 = yellow (for keywords like int, if, return, etc.)
        # Color code 35 = magenta (for strings like "Hello from C!")
        # Color code 36 = cyan (for comments /* ... */)
        raw_str = result.raw.decode('utf-8', errors='ignore')

        # Check that specific keywords are highlighted
        # Type keywords like 'int' are green (32m), regular keywords are yellow (33m)
        self.assertIn("\x1b[32mint\x1b[37m", raw_str,
                     "Expected type keyword 'int' to be highlighted in green (32m -> 37m)")
        self.assertIn("\x1b[33mif\x1b[37m", raw_str,
                     "Expected keyword 'if' to be highlighted in yellow (33m -> 37m)")
        self.assertIn("\x1b[33mreturn\x1b[37m", raw_str,
                     "Expected keyword 'return' to be highlighted in yellow (33m -> 37m)")

        # Check that strings are highlighted in magenta (35m) followed by white (37m)
        self.assertIn('\x1b[35m"Hello from C!"\x1b[37m', raw_str,
                     "Expected string '\"Hello from C!\"' to be highlighted in magenta (35m -> 37m)")

        # Check that comments are highlighted in cyan (36m)
        self.assertIn('\x1b[36m/* Example C file', raw_str,
                     "Expected comment '/* Example C file...' to be highlighted in cyan (36m)")

        # Also check number highlighting (31m = red)
        self.assertTrue(
            "\x1b[31m0\x1b[37m" in raw_str or
            "\x1b[31m1\x1b[37m" in raw_str or
            "\x1b[31m42\x1b[37m" in raw_str,
            "Expected numbers to be highlighted in red (31m -> 37m)"
        )


class TestDimNavigation(unittest.TestCase):
    """Tests for navigation functionality."""

    def test_navigation_with_arrow_keys(self):
        """Test that arrow keys navigate through the file."""
        # Open hello_world.txt, press down arrow 3 times, then quit
        # This should move cursor to line 4
        input_str = "[sleep:50][down][down][down][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After pressing down 3 times, we should be on line 4 (started at line 1)
        self.assertIn("4/5", result.output, "Expected cursor at line 4/5 after 3 down arrows")


if __name__ == "__main__":
    unittest.main()
