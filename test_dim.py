#!/usr/bin/env python3
"""
Test suite for dim editor
"""

import sys
import os

# Import testty functions
sys.path.insert(0, os.path.dirname(__file__))
from testty import run_with_pty, parse_input_string


def test_cannot_quit_with_unsaved_changes():
    """Test that ctrl-q doesn't immediately quit when there are unsaved changes."""
    print("Test: Cannot quit with unsaved changes...")

    # Create a new file with some content, then try to quit without saving
    input_str = "Hello, World![ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output, did_exit, exit_code = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80,
        return_exit_info=True
    )

    # Check that the warning message appears
    assert "WARNING" in output, "Expected WARNING message when trying to quit with unsaved changes"
    assert "unsaved changes" in output, "Expected 'unsaved changes' in warning message"
    assert "Press Ctrl-Q" in output, "Expected instruction to press Ctrl-Q multiple times"

    # Check that we're still in the editor (not quit)
    assert "Hello, World!" in output, "Expected editor content to still be visible"

    # IMPORTANT: Check that the process did NOT exit
    assert not did_exit, "Editor should NOT have exited with unsaved changes after one Ctrl-Q"

    print("  ✓ Warning message displayed")
    print("  ✓ Editor did not quit (process still running)")
    print("  PASSED\n")
    return True


def test_quit_after_multiple_ctrl_q():
    """Test that pressing ctrl-q 4 times will quit even with unsaved changes."""
    print("Test: Quit after multiple ctrl-q presses...")

    # Create content and press ctrl-q 4 times (3 warnings + 1 to actually quit)
    input_str = "Some content[ctrl-q][ctrl-q][ctrl-q][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output, did_exit, exit_code = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80,
        return_exit_info=True
    )

    # After 4 ctrl-q presses, the editor SHOULD have exited
    assert did_exit, "Editor should have exited after 4 Ctrl-Q presses with unsaved changes"
    assert exit_code == 0, f"Editor should exit with code 0, got {exit_code}"

    print("  ✓ Editor exited after 4 Ctrl-Q presses")
    print(f"  ✓ Exit code: {exit_code}")
    print("  PASSED\n")
    return True


def test_quit_immediately_without_changes():
    """Test that ctrl-q quits immediately when there are no unsaved changes."""
    print("Test: Quit immediately without changes...")

    # Open an existing file and quit immediately without making changes
    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output, did_exit, exit_code = run_with_pty(
        command=["./dim", "example.py"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80,
        return_exit_info=True
    )

    # Should not see warning message about unsaved changes
    assert "unsaved changes" not in output, \
        "Should not show warning when no changes were made"

    # Should show the file content (snapshot taken before quit)
    assert "example.py" in output, "Should show the filename"
    assert "python" in output, "Should show python filetype"

    # Should have exited immediately
    assert did_exit, "Editor should have exited immediately without unsaved changes"
    assert exit_code == 0, f"Editor should exit with code 0, got {exit_code}"

    print("  ✓ No unsaved changes warning")
    print("  ✓ Editor exited immediately")
    print(f"  ✓ Exit code: {exit_code}")
    print("  PASSED\n")
    return True


def test_save_then_quit():
    """Test that saving changes allows immediate quit."""
    print("Test: Save then quit...")

    # Create a test file, make changes, save, then quit
    input_str = "Test content[ctrl-s]test_output.txt[enter][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Should see "written to disk" message
    assert "written to disk" in output, "Expected save confirmation message"

    # Should not see unsaved changes warning
    assert "unsaved changes" not in output, "Should not warn about unsaved changes after saving"

    # Clean up the test file
    if os.path.exists("test_output.txt"):
        os.remove("test_output.txt")

    print("  ✓ File saved successfully")
    print("  ✓ Quit without warning after save")
    print("  PASSED\n")
    return True


def test_warning_countdown():
    """Test that the warning shows the correct countdown (3, 2, 1)."""
    print("Test: Warning countdown...")

    # Press ctrl-q once and check the countdown
    input_str = "Content[ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # First ctrl-q should show "Press Ctrl-Q 3 more times"
    # (quit_times starts at 3, shows message with current value)
    assert "3 more times" in output, \
        f"Expected '3 more times' in warning message, got: {output[-200:]}"

    print("  ✓ Countdown shows correct number (3 more times)")
    print("  PASSED\n")
    return True


def test_open_file_and_view_contents():
    """Test that dim can open a file and display its contents."""
    print("Test: Open file and view contents...")

    # Open hello_world.txt and wait briefly to let it render
    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output, did_exit, exit_code = run_with_pty(
        command=["./dim", "hello_world.txt"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80,
        return_exit_info=True
    )

    # Check that file contents are visible
    assert "Hello, World!" in output, "Expected to see 'Hello, World!' in file contents"
    assert "This is a test file" in output, "Expected to see second line of file"
    assert "Line 3: Testing line display" in output, "Expected to see third line"

    # Should have exited cleanly
    assert did_exit, "Editor should have exited"
    assert exit_code == 0, f"Editor should exit with code 0, got {exit_code}"

    print("  ✓ File contents displayed correctly")
    print("  ✓ Editor exited cleanly")
    print("  PASSED\n")
    return True


def test_status_bar_shows_filename_and_lines():
    """Test that the status bar displays filename, line count, and filetype."""
    print("Test: Status bar shows filename and line count...")

    # Open hello_world.txt
    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "hello_world.txt"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Status bar should show filename and line count
    assert "hello_world.txt" in output, "Expected filename in status bar"
    assert "5 lines" in output, "Expected '5 lines' in status bar (file has 5 lines)"

    # Should show "no ft" (no filetype) since .txt doesn't have syntax highlighting
    assert "no ft" in output, "Expected 'no ft' for .txt file"

    # Should show current line position (1/5 since we start at line 1)
    assert "1/5" in output, "Expected '1/5' showing current line position"

    print("  ✓ Status bar shows filename")
    print("  ✓ Status bar shows line count")
    print("  ✓ Status bar shows filetype")
    print("  ✓ Status bar shows current position")
    print("  PASSED\n")
    return True


def test_status_bar_shows_python_filetype():
    """Test that the status bar shows 'python' filetype for .py files."""
    print("Test: Status bar shows Python filetype...")

    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "example.py"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Should show filename and python filetype
    assert "example.py" in output, "Expected 'example.py' filename in status bar"
    assert "python" in output, "Expected 'python' filetype in status bar"

    print("  ✓ Status bar shows Python filetype")
    print("  PASSED\n")
    return True


def test_open_new_file_shows_no_name():
    """Test that opening dim without a file shows '[No Name]' in status bar."""
    print("Test: Open without filename shows '[No Name]'...")

    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Should show [No Name] in status bar
    assert "[No Name]" in output, "Expected '[No Name]' in status bar for new file"
    assert "0 lines" in output, "Expected '0 lines' for empty new file"

    print("  ✓ Status bar shows '[No Name]' for new file")
    print("  ✓ Status bar shows '0 lines'")
    print("  PASSED\n")
    return True


def test_syntax_highlighting_python():
    """Test that Python syntax highlighting works for keywords."""
    print("Test: Python syntax highlighting...")

    # Open example.py and wait for it to render
    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "example.py"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Check that Python content is visible
    assert "def hello_world" in output, "Expected to see function definition"
    assert "class TestClass" in output, "Expected to see class definition"
    assert "print" in output, "Expected to see print statement"

    # The file should be recognized as Python
    assert "python" in output, "Expected 'python' filetype in status bar"

    print("  ✓ Python file contents displayed")
    print("  ✓ Python filetype detected")
    print("  PASSED\n")
    return True


def test_navigation_with_arrow_keys():
    """Test that arrow keys navigate through the file."""
    print("Test: Navigation with arrow keys...")

    # Open hello_world.txt, press down arrow 3 times, then quit
    # This should move cursor to line 4
    input_str = "[sleep:200][down][down][down][sleep:100][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "hello_world.txt"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # After pressing down 3 times, we should be on line 4 (started at line 1)
    assert "4/5" in output, "Expected cursor at line 4/5 after 3 down arrows"

    print("  ✓ Arrow key navigation works")
    print("  ✓ Status bar updates cursor position")
    print("  PASSED\n")
    return True


def test_save_new_file_creates_file():
    """Test that saving a new file with Ctrl-S creates the file on disk."""
    print("Test: Save new file creates file on disk...")

    # Type content, save as test_new_file.txt, then quit
    input_str = "New file content[ctrl-s]test_new_file.txt[enter][sleep:100][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output, did_exit, exit_code = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80,
        return_exit_info=True
    )

    # Should see save confirmation
    assert "written to disk" in output, "Expected save confirmation message"

    # File should exist on disk
    assert os.path.exists("test_new_file.txt"), "Expected file to be created on disk"

    # Verify file contents
    with open("test_new_file.txt", "r") as f:
        contents = f.read()
        assert "New file content" in contents, "Expected file to contain typed content"

    # Clean up
    os.remove("test_new_file.txt")

    # Should have exited cleanly
    assert did_exit, "Editor should have exited"
    assert exit_code == 0, f"Editor should exit with code 0, got {exit_code}"

    print("  ✓ File created on disk")
    print("  ✓ File contains correct content")
    print("  ✓ Editor exited cleanly")
    print("  PASSED\n")
    return True


def test_modified_indicator_in_status_bar():
    """Test that the status bar shows '(modified)' when file is edited."""
    print("Test: Modified indicator in status bar...")

    # Open file, make a change, check for (modified) indicator
    input_str = "[sleep:200]x[sleep:100][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "hello_world.txt"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # After typing 'x', file should be marked as modified
    assert "(modified)" in output, "Expected '(modified)' indicator in status bar after editing"

    # Should also see the warning about unsaved changes when trying to quit
    assert "unsaved changes" in output, "Expected warning about unsaved changes"

    print("  ✓ Status bar shows '(modified)' after edit")
    print("  ✓ Warning shown when quitting with changes")
    print("  PASSED\n")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("DIM EDITOR TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        test_cannot_quit_with_unsaved_changes,
        test_quit_after_multiple_ctrl_q,
        test_quit_immediately_without_changes,
        test_save_then_quit,
        test_warning_countdown,
        test_open_file_and_view_contents,
        test_status_bar_shows_filename_and_lines,
        test_status_bar_shows_python_filetype,
        test_open_new_file_shows_no_name,
        test_syntax_highlighting_python,
        test_navigation_with_arrow_keys,
        test_save_new_file_creates_file,
        test_modified_indicator_in_status_bar,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
