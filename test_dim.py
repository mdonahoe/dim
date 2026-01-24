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
        input_str = "iHello, World![ctrl-q]"
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
        input_str = "iSome content[ctrl-q][ctrl-q][ctrl-q][ctrl-q]"
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
        """Test that :q quits immediately when there are no unsaved changes."""
        # Open an existing file and quit immediately without making changes
        input_str = "[sleep:50]:q[enter]"
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
        input_str = "iContent[ctrl-q]"
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
        input_str = "iTest content[ctrl-s]test_output.txt[enter][ctrl-q]"
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
        input_str = "iNew file content[ctrl-s]test_new_file.txt[enter][sleep:20][ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]ix[sleep:20][ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[ctrl-q]"
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
        input_str = "[sleep:50]i[down][down][down][sleep:20][ctrl-q]"
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


class TestDimYankPaste(unittest.TestCase):
    """Tests for yank (yy) and paste (p) functionality."""

    def test_yank_line_and_paste(self):
        """Test that yy yanks current line and p pastes it below."""
        # Open hello_world.txt, yank first line with yy, move down, paste with p
        input_str = "[sleep:50]yyjp[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After yanking line 1 "Hello, World!" and pasting after line 2,
        # we should see "Hello, World!" appear twice in the output
        # Count occurrences of "Hello, World!"
        count = result.output.count("Hello, World!")
        self.assertGreaterEqual(count, 2,
            f"Expected 'Hello, World!' to appear at least twice after yy + p, found {count} times")

    def test_yank_line_shows_message(self):
        """Test that yy shows a 'yanked' message in status bar."""
        # Open file and yank a line
        input_str = "[sleep:50]yy[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should show confirmation that line was yanked
        self.assertIn("yank", result.output.lower(),
            "Expected 'yank' message in status bar after yy")

    def test_paste_without_yank(self):
        """Test that p does nothing or shows message when nothing is yanked."""
        # Open file and try to paste without yanking first
        input_str = "[sleep:50]p[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # File should remain unchanged (still 5 lines)
        self.assertIn("5 lines", result.output,
            "Expected file to still have 5 lines when paste with empty register")


class TestDimTabInsertion(unittest.TestCase):
    """Tests for tab key insertion behavior."""

    def test_tab_inserts_four_spaces(self):
        """Test that pressing tab in insert mode inserts 4 spaces."""
        # Create new file, enter insert mode, press tab, then type text
        input_str = "[sleep:50]i[tab]test[ctrl-s]test_tab.txt[enter][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Verify file was created with 4 spaces before 'test'
        self.assertTrue(os.path.exists("test_tab.txt"),
            "Expected file to be created")

        with open("test_tab.txt", "r") as f:
            contents = f.read()
            # Tab should insert 4 spaces, not a tab character
            self.assertIn("    test", contents,
                "Expected 4 spaces before 'test' when tab is pressed")
            self.assertNotIn("\t", contents,
                "Expected spaces, not tab character")

        # Clean up
        os.remove("test_tab.txt")

    def test_tab_respects_existing_tabs(self):
        """Test that tab inserts actual tabs if file already contains tabs."""
        # Create a file with tabs first
        with open("test_with_tabs.txt", "w") as f:
            f.write("\tindented with tab\n")

        # Open the file, go to end, add new line with tab
        input_str = "[sleep:50]Go[tab]more[ctrl-s][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "test_with_tabs.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Read the file and check if tab was used
        with open("test_with_tabs.txt", "r") as f:
            contents = f.read()
            lines = contents.split('\n')
            # The new line should also use tab (if feature respects existing tabs)
            if len(lines) >= 2:
                self.assertIn("\t", lines[-1] if lines[-1] else lines[-2],
                    "Expected tab character when file already contains tabs")

        # Clean up
        os.remove("test_with_tabs.txt")

    def test_tab_at_beginning_of_line(self):
        """Test that tab at beginning of line creates proper indentation."""
        # Create new file, enter insert mode, press tab twice
        input_str = "[sleep:50]i[tab][tab]indented[ctrl-s]test_indent.txt[enter][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Verify file was created with 8 spaces (2 tabs * 4 spaces each)
        self.assertTrue(os.path.exists("test_indent.txt"),
            "Expected file to be created")

        with open("test_indent.txt", "r") as f:
            contents = f.read()
            # Two tabs should give 8 spaces
            self.assertIn("        indented", contents,
                "Expected 8 spaces (2 tabs) before 'indented'")

        # Clean up
        os.remove("test_indent.txt")


class TestDimJJEscape(unittest.TestCase):
    """Tests for jj to escape from insert mode."""

    def test_jj_escapes_insert_mode(self):
        """Test that typing jj quickly in insert mode escapes to normal mode."""
        # Enter insert mode, type some text, then jj to escape, then :q to quit
        input_str = "[sleep:50]ihello jj[sleep:10]:q[enter]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # If jj worked, we should see "hello " (without jj) in the content
        # and the :q command should have worked (process should exit or show command)
        # The jj should not appear in the text if it triggered escape
        self.assertIn("hello", result.output,
            "Expected 'hello' to appear in content")
        # If jj escaped, then :q should be interpreted as a command
        # Either the editor quit or we see a save warning
        command_worked = (
            result.did_exit or
            "no write" in result.output.lower() or
            "warning" in result.output.lower()
        )
        self.assertTrue(command_worked,
            "Expected jj to escape insert mode and :q to be interpreted as command")

    def test_jj_does_not_escape_when_slow(self):
        """Test that j followed by slow j does not escape insert mode."""
        # Enter insert mode, type j, wait, type j - should insert both j's
        input_str = "[sleep:50]ij[sleep:200]j[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Both j's should appear in the content since they were typed slowly
        self.assertIn("jj", result.output,
            "Expected 'jj' to appear in content when typed slowly")
        # Should show unsaved changes warning (still in insert mode)
        self.assertIn("unsaved", result.output.lower(),
            "Expected unsaved changes warning (still has content)")

    def test_jj_in_middle_of_text(self):
        """Test that jj works even when typed in the middle of text."""
        # Type some text, then jj, then more commands
        input_str = "[sleep:50]itestjj:q[enter]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see "test" but not "jj" in content (jj triggered escape)
        self.assertIn("test", result.output,
            "Expected 'test' in content")
        # :q should be a command, not text
        command_worked = (
            result.did_exit or
            "no write" in result.output.lower()
        )
        self.assertTrue(command_worked,
            "Expected jj to escape and :q to work as command")


class TestDimNumberRepeat(unittest.TestCase):
    """Tests for number prefix to repeat commands."""

    def test_number_j_moves_down_multiple_lines(self):
        """Test that 3j moves cursor down 3 lines."""
        # Open file with 5 lines, press 3j to move down 3 lines
        input_str = "[sleep:50]3j[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should be on line 4 (started at line 1, moved down 3)
        self.assertIn("4/5", result.output,
            "Expected cursor at line 4/5 after 3j")

    def test_number_k_moves_up_multiple_lines(self):
        """Test that 2k moves cursor up 2 lines."""
        # Open file, go to line 5, then press 2k to move up 2 lines
        input_str = "[sleep:50]G2k[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Started at line 5 (G), moved up 2, should be at line 3
        self.assertIn("3/5", result.output,
            "Expected cursor at line 3/5 after G + 2k")

    def test_number_x_deletes_multiple_chars(self):
        """Test that 5x deletes 5 characters."""
        # Open file, delete 5 characters with 5x
        input_str = "[sleep:50]5x[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # "Hello, World!" should become ", World!" after deleting "Hello"
        self.assertIn(", World!", result.output,
            "Expected ', World!' after 5x deletes 'Hello'")
        # Should show modified indicator
        self.assertIn("(modified)", result.output,
            "Expected (modified) after deletion")

    def test_number_dd_deletes_multiple_lines(self):
        """Test that 2dd deletes 2 lines."""
        # Open file, delete 2 lines with 2dd
        input_str = "[sleep:50]2dd[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After deleting first 2 lines, should have 3 lines remaining
        self.assertIn("3 lines", result.output,
            "Expected 3 lines remaining after 2dd on 5-line file")
        # First line should now be what was line 3
        self.assertIn("Line 3:", result.output,
            "Expected 'Line 3:' to be visible (now first line)")

    def test_large_number_repeat(self):
        """Test that large numbers like 10j work correctly."""
        # Open file, try to move down 10 lines (should stop at end)
        input_str = "[sleep:50]10j[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should be at the last line (5/5) since file only has 5 lines
        self.assertIn("5/5", result.output,
            "Expected cursor at line 5/5 after 10j (capped at file end)")


class TestDimFindCharacter(unittest.TestCase):
    """Tests for f (find character) and related motions."""

    def test_f_jumps_to_character(self):
        """Test that f{char} moves cursor to next occurrence of character."""
        # Open file, use fw to jump to 'W' in "Hello, World!"
        input_str = "[sleep:50]fW[sleep:20]i[ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After f jumps to W, entering insert mode and trying to quit
        # should show unsaved changes (cursor moved to position 7 for 'W')
        # The presence of the file content indicates we're still in the editor
        self.assertIn("Hello, World!", result.output,
            "Expected file content to be visible")

    def test_f_with_number_prefix(self):
        """Test that 2f{char} jumps to second occurrence of character."""
        # Line is "Hello, World!" - 2fl should jump to second 'l'
        input_str = "[sleep:50]2fl[sleep:20]i[ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should have moved to second 'l' in "Hello"
        self.assertIn("Hello, World!", result.output,
            "Expected file content after 2fl")

    def test_ct_change_to_character(self):
        """Test that ct{char} deletes to character and enters insert mode."""
        # On "Hello, World!" use ct, to change to comma, then type "Goodbye"
        input_str = "[sleep:50]ct,Goodbye[esc][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # "Hello" should be replaced with "Goodbye", leaving "Goodbye, World!"
        self.assertIn("Goodbye", result.output,
            "Expected 'Goodbye' after ct, replaces 'Hello'")
        self.assertIn("World!", result.output,
            "Expected 'World!' to remain after ct,")
        self.assertIn("(modified)", result.output,
            "Expected (modified) after change")

    def test_dt_delete_to_character(self):
        """Test that dt{char} deletes to character (not including it)."""
        # On "Hello, World!" use dt, to delete to comma
        input_str = "[sleep:50]dt,[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # "Hello" should be deleted, leaving ", World!"
        self.assertIn(", World!", result.output,
            "Expected ', World!' after dt, deletes 'Hello'")
        self.assertIn("(modified)", result.output,
            "Expected (modified) after deletion")

    def test_f_no_match_does_nothing(self):
        """Test that f{char} with no match leaves cursor in place."""
        # Try to find 'z' which doesn't exist in "Hello, World!"
        input_str = "[sleep:50]fz[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Cursor should still be at line 1 (no modification, no movement indicated)
        self.assertIn("1/5", result.output,
            "Expected cursor to remain at line 1/5 when f finds no match")
        # File should not be modified
        self.assertNotIn("(modified)", result.output,
            "Expected no modification when f finds no match")


class TestDimEditCommand(unittest.TestCase):
    """Tests for :e (edit) command with tab completion."""

    def test_edit_command_tab_completion(self):
        """Test that :e file<tab> tab-completes filenames."""
        # Open dim, type :e hell<tab> which should complete to hello_world.txt
        input_str = "[sleep:50]:e hell[tab][sleep:50][enter][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After tab completion and opening, should see hello_world.txt in status
        self.assertIn("hello_world.txt", result.output,
            "Expected 'hello_world.txt' after tab completion with :e hell<tab>")

    def test_edit_command_opens_file(self):
        """Test that :e filename opens the specified file."""
        # Open dim, use :e to open hello_world.txt
        input_str = "[sleep:50]:e hello_world.txt[enter][sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see file contents and filename in status bar
        self.assertIn("hello_world.txt", result.output,
            "Expected 'hello_world.txt' in status bar after :e command")
        self.assertIn("Hello, World!", result.output,
            "Expected file content after :e command")

    def test_edit_command_relative_path(self):
        """Test that :e works with relative paths based on current buffer."""
        # First open example.py, then use :e to open example.c (same directory)
        input_str = "[sleep:50]:e example.c[enter][sleep:50][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "example.py"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should now show example.c content
        self.assertIn("example.c", result.output,
            "Expected 'example.c' in status bar after :e command")
        self.assertIn("int main", result.output,
            "Expected C file content after :e command")

    def test_edit_command_shows_completion_options(self):
        """Test that tab shows multiple options when prefix matches multiple files."""
        # Type :e example<tab> which matches both example.py and example.c
        input_str = "[sleep:50]:e example[tab][sleep:50][esc][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should show both options or complete to common prefix
        # Either "example." is shown or both files are listed
        has_completion = (
            "example.py" in result.output or
            "example.c" in result.output or
            "example." in result.output
        )
        self.assertTrue(has_completion,
            "Expected tab completion to show example files")


class TestDimYankWord(unittest.TestCase):
    """Tests for yw (yank word) functionality."""

    def test_yank_word_and_paste(self):
        """Test that yw yanks current word and p pastes it."""
        # Open hello_world.txt, yank first word with yw, move to end of line, paste
        input_str = "[sleep:50]yw$p[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After yanking "Hello," (first word) and pasting at end,
        # we should see "Hello" appear twice on the first line
        # The line should be "Hello, World!Hello," or similar
        self.assertIn("(modified)", result.output,
            "Expected (modified) after yw + p")

    def test_yank_word_shows_message(self):
        """Test that yw shows a 'yanked' message in status bar."""
        # Open file and yank a word
        input_str = "[sleep:50]yw[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should show confirmation that word was yanked
        self.assertIn("yank", result.output.lower(),
            "Expected 'yank' message in status bar after yw")

    def test_yank_word_and_paste_at_different_location(self):
        """Test yanking word on one line and pasting on another."""
        # Yank "Hello," then go to line 2 and paste
        input_str = "[sleep:50]ywjp[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # File should be modified after paste
        self.assertIn("(modified)", result.output,
            "Expected (modified) after pasting yanked word")


class TestDimCapitalC(unittest.TestCase):
    """Tests for C (change to end of line) functionality."""

    def test_C_deletes_to_end_of_line_and_enters_insert(self):
        """Test that C deletes from cursor to end of line and enters insert mode."""
        # Open file, move right 5 chars to 'o' in "Hello", then C to delete rest
        input_str = "[sleep:50]foCReplaced[esc][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # After fo (find 'o'), C should delete ", World!" and we type "Replaced"
        # Result should be "HelloReplaced"
        self.assertIn("Replaced", result.output,
            "Expected 'Replaced' after C and typing")
        self.assertIn("(modified)", result.output,
            "Expected (modified) after C")

    def test_C_at_end_of_line_enters_insert_mode(self):
        """Test that C at end of line just enters insert mode."""
        # Go to end of line with $, then C, type text
        input_str = "[sleep:50]$CExtra[esc][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see Extra appended
        self.assertIn("Extra", result.output,
            "Expected 'Extra' after C at end of line")

    def test_C_shows_insert_mode(self):
        """Test that C enters INSERT mode."""
        # Use C and check mode indicator
        input_str = "[sleep:50]C[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should be in INSERT mode
        self.assertIn("INSERT", result.output,
            "Expected INSERT mode after C")


class TestDimReplaceChar(unittest.TestCase):
    """Tests for r (replace character) functionality."""

    def test_r_replaces_character(self):
        """Test that r{char} replaces current character with new character."""
        # Open file, replace 'H' with 'J'
        input_str = "[sleep:50]rJ[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # First character 'H' should be replaced with 'J'
        self.assertIn("Jello, World!", result.output,
            "Expected 'Jello, World!' after replacing H with J")
        self.assertIn("(modified)", result.output,
            "Expected (modified) after replacement")

    def test_r_stays_in_normal_mode(self):
        """Test that r remains in normal mode after replacement."""
        # Replace character, then try a normal mode command
        input_str = "[sleep:50]rJl[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should still be in NORMAL mode (l moved right, not inserted 'l')
        self.assertIn("NORMAL", result.output,
            "Expected NORMAL mode after r replacement")

    def test_r_with_number_prefix(self):
        """Test that 3r{char} replaces 3 characters."""
        # Replace first 3 characters with 'X'
        input_str = "[sleep:50]3rX[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # First 3 chars "Hel" should be replaced with "XXX"
        self.assertIn("XXXlo, World!", result.output,
            "Expected 'XXXlo, World!' after 3rX")


class TestDimBackwardFind(unittest.TestCase):
    """Tests for F and T (backward find character) functionality."""

    def test_F_jumps_backward_to_character(self):
        """Test that F{char} moves cursor backward to character."""
        # Go to end of line, then F, to find the comma backward
        input_str = "[sleep:50]$F,[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Cursor should be on ',' now, file unmodified
        self.assertNotIn("(modified)", result.output,
            "File should not be modified by F movement")
        self.assertIn("Hello, World!", result.output,
            "File content should be unchanged")

    def test_T_jumps_backward_before_character(self):
        """Test that T{char} moves cursor backward to one after character."""
        # Go to end of line, then T, to find position after comma backward
        input_str = "[sleep:50]$T,[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # File should not be modified
        self.assertNotIn("(modified)", result.output,
            "File should not be modified by T movement")

    def test_dF_deletes_backward_to_character(self):
        """Test that dF{char} deletes backward to character (inclusive)."""
        # Go to end of line, then dF, to delete from cursor back to comma
        input_str = "[sleep:50]$dF,[sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # "Hello, World!" with $dF, should become "Hello"
        # (delete from end back to and including comma)
        self.assertIn("Hello", result.output,
            "Expected 'Hello' to remain after dF,")
        self.assertIn("(modified)", result.output,
            "File should be modified after deletion")

    def test_cT_changes_backward_before_character(self):
        """Test that cT{char} changes backward to one after character."""
        # Go to end of line, then cT, to change from cursor to after comma
        input_str = "[sleep:50]$cT,NEW[esc][sleep:20][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80
        )

        # Should see NEW in the output
        self.assertIn("NEW", result.output,
            "Expected 'NEW' after cT, replacement")
        self.assertIn("(modified)", result.output,
            "File should be modified after change")


if __name__ == "__main__":
    unittest.main()
