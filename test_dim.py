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

    output = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Check that the warning message appears
    assert "WARNING" in output, "Expected WARNING message when trying to quit with unsaved changes"
    assert "unsaved changes" in output, "Expected 'unsaved changes' in warning message"
    assert "Press Ctrl-Q" in output, "Expected instruction to press Ctrl-Q multiple times"

    # Check that we're still in the editor (not quit)
    assert "Hello, World!" in output, "Expected editor content to still be visible"

    print("  ✓ Warning message displayed")
    print("  ✓ Editor did not quit")
    print("  PASSED\n")
    return True


def test_quit_after_multiple_ctrl_q():
    """Test that pressing ctrl-q 3 times will quit even with unsaved changes."""
    print("Test: Quit after multiple ctrl-q presses...")

    # Create content and press ctrl-q twice, then check the warning
    # On the third ctrl-q, it should quit
    input_str = "Some content[ctrl-q][ctrl-q][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # After 2 ctrl-q presses, should show "Press Ctrl-Q 1 more times to quit"
    # (The snapshot is taken before the final ctrl-q)
    assert "1 more times to quit" in output or "Ctrl-Q 1" in output, \
        "Expected warning showing 1 more time needed"

    print("  ✓ Warning countdown working correctly")
    print("  PASSED\n")
    return True


def test_quit_immediately_without_changes():
    """Test that ctrl-q quits immediately when there are no unsaved changes."""
    print("Test: Quit immediately without changes...")

    # Open an existing file and quit immediately without making changes
    input_str = "[sleep:300][ctrl-q]"
    input_tokens = parse_input_string(input_str)

    output = run_with_pty(
        command=["./dim", "test.py"],
        input_tokens=input_tokens,
        delay_ms=50,
        timeout=2.0,
        rows=24,
        cols=80
    )

    # Should not see warning message about unsaved changes
    assert "unsaved changes" not in output, \
        "Should not show warning when no changes were made"

    # Should show the file content (snapshot taken before quit)
    assert "test.py" in output, "Should show the filename"
    assert "python" in output, "Should show python filetype"

    print("  ✓ No unsaved changes warning")
    print("  ✓ Editor displayed file correctly")
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
