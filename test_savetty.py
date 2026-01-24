#!/usr/bin/env python3
"""
Unit tests for savetty.py and EXPECT_SCREEN functionality in testty.py
"""

import os
import sys
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))
from testty import run_with_pty, parse_input_string, ScreenExpectation


class TestExpectScreenParsing(unittest.TestCase):
    """Tests for parsing EXPECT_SCREEN tokens."""

    def test_parse_expect_screen_token(self):
        """Test that [EXPECT_SCREEN:file.txt] is parsed correctly."""
        tokens = parse_input_string("[EXPECT_SCREEN:snapshot001.txt]")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0], ('expect_screen', 'snapshot001.txt'))

    def test_parse_expect_screen_with_other_tokens(self):
        """Test EXPECT_SCREEN mixed with other tokens."""
        tokens = parse_input_string("hello[enter][EXPECT_SCREEN:test.txt][ctrl-q]")
        self.assertEqual(len(tokens), 8)  # h, e, l, l, o, enter, expect_screen, ctrl-q
        # Find the expect_screen token
        expect_token = [t for t in tokens if isinstance(t, tuple) and t[0] == 'expect_screen']
        self.assertEqual(len(expect_token), 1)
        self.assertEqual(expect_token[0][1], 'test.txt')

    def test_parse_expect_screen_case_insensitive(self):
        """Test that EXPECT_SCREEN parsing is case insensitive."""
        tokens1 = parse_input_string("[expect_screen:file.txt]")
        tokens2 = parse_input_string("[EXPECT_SCREEN:file.txt]")
        self.assertEqual(tokens1, tokens2)


class TestExpectScreenVerification(unittest.TestCase):
    """Tests for EXPECT_SCREEN verification during PTY execution."""

    def setUp(self):
        """Create a temporary directory for test snapshots."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_expect_screen_passes_with_matching_content(self):
        """Test that EXPECT_SCREEN passes when screen matches snapshot."""
        # Create a snapshot file with expected content
        snapshot_path = os.path.join(self.test_dir, "snapshot001.txt")
        with open(snapshot_path, 'w') as f:
            f.write("Hello, World!\n")
            f.write("This is a test file\n")
            f.write("Line 3: Testing line display\n")
            f.write("Line 4: More content\n")
            f.write("Line 5: Last line")

        # Open hello_world.txt and verify it matches the snapshot
        input_str = "[sleep:50][EXPECT_SCREEN:snapshot001.txt][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80,
            snapshot_dir=self.test_dir
        )

        # Check that we have an expectation result
        self.assertEqual(len(result.screen_expectations), 1)
        expectation = result.screen_expectations[0]
        self.assertEqual(expectation.snapshot_file, "snapshot001.txt")
        # The screen should contain the file content (may have more due to status bar)
        self.assertIn("Hello, World!", expectation.actual_screen)

    def test_expect_screen_fails_with_mismatched_content(self):
        """Test that EXPECT_SCREEN fails when screen doesn't match snapshot."""
        # Create a snapshot file with different content
        snapshot_path = os.path.join(self.test_dir, "wrong.txt")
        with open(snapshot_path, 'w') as f:
            f.write("This is completely wrong content")

        # Open hello_world.txt but expect different content
        input_str = "[sleep:50][EXPECT_SCREEN:wrong.txt][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80,
            snapshot_dir=self.test_dir
        )

        # Check that we have an expectation result that failed
        self.assertEqual(len(result.screen_expectations), 1)
        expectation = result.screen_expectations[0]
        self.assertFalse(expectation.passed)

    def test_expect_screen_fails_with_missing_file(self):
        """Test that EXPECT_SCREEN fails when snapshot file doesn't exist."""
        input_str = "[sleep:50][EXPECT_SCREEN:nonexistent.txt][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80,
            snapshot_dir=self.test_dir
        )

        # Check that we have an expectation result that failed
        self.assertEqual(len(result.screen_expectations), 1)
        expectation = result.screen_expectations[0]
        self.assertFalse(expectation.passed)

    def test_multiple_expect_screen_tokens(self):
        """Test multiple EXPECT_SCREEN tokens in one sequence."""
        # Create two snapshot files
        snapshot1_path = os.path.join(self.test_dir, "snap1.txt")
        snapshot2_path = os.path.join(self.test_dir, "snap2.txt")

        with open(snapshot1_path, 'w') as f:
            f.write("Content 1")

        with open(snapshot2_path, 'w') as f:
            f.write("Content 2")

        input_str = "[sleep:50][EXPECT_SCREEN:snap1.txt]j[sleep:20][EXPECT_SCREEN:snap2.txt][ctrl-q]"
        input_tokens = parse_input_string(input_str)

        result = run_with_pty(
            command=["./dim", "hello_world.txt"],
            input_tokens=input_tokens,
            delay_ms=10,
            timeout=0.5,
            rows=24,
            cols=80,
            snapshot_dir=self.test_dir
        )

        # Check that we have two expectation results
        self.assertEqual(len(result.screen_expectations), 2)
        self.assertEqual(result.screen_expectations[0].snapshot_file, "snap1.txt")
        self.assertEqual(result.screen_expectations[1].snapshot_file, "snap2.txt")


class TestSavettyByteConversion(unittest.TestCase):
    """Tests for savetty byte-to-sequence conversion."""

    def test_byte_to_sequence_imports(self):
        """Test that savetty can be imported."""
        from savetty import byte_to_sequence
        self.assertTrue(callable(byte_to_sequence))

    def test_byte_to_sequence_regular_char(self):
        """Test converting regular ASCII characters."""
        from savetty import byte_to_sequence

        parts, is_enter = byte_to_sequence(ord('a'), None, 0)
        self.assertEqual(parts, ['a'])
        self.assertFalse(is_enter)

    def test_byte_to_sequence_enter(self):
        """Test converting Enter key."""
        from savetty import byte_to_sequence

        parts, is_enter = byte_to_sequence(0x0d, None, 0)
        self.assertEqual(parts, ['[enter]'])
        self.assertTrue(is_enter)

    def test_byte_to_sequence_escape(self):
        """Test converting Escape key."""
        from savetty import byte_to_sequence

        parts, is_enter = byte_to_sequence(0x1b, None, 0)
        self.assertEqual(parts, ['[esc]'])
        self.assertFalse(is_enter)

    def test_byte_to_sequence_tab(self):
        """Test converting Tab key."""
        from savetty import byte_to_sequence

        parts, is_enter = byte_to_sequence(0x09, None, 0)
        self.assertEqual(parts, ['[tab]'])
        self.assertFalse(is_enter)

    def test_byte_to_sequence_backspace(self):
        """Test converting Backspace key."""
        from savetty import byte_to_sequence

        parts, is_enter = byte_to_sequence(0x7f, None, 0)
        self.assertEqual(parts, ['[backspace]'])
        self.assertFalse(is_enter)

    def test_byte_to_sequence_ctrl_char(self):
        """Test converting control characters."""
        from savetty import byte_to_sequence

        # Ctrl-C is byte 0x03
        parts, is_enter = byte_to_sequence(0x03, None, 0)
        self.assertEqual(parts, ['[ctrl-c]'])
        self.assertFalse(is_enter)

        # Ctrl-Q is byte 0x11
        parts, is_enter = byte_to_sequence(0x11, None, 0)
        self.assertEqual(parts, ['[ctrl-q]'])
        self.assertFalse(is_enter)

    def test_byte_to_sequence_with_sleep(self):
        """Test that sleep tokens are generated for pauses."""
        from savetty import byte_to_sequence

        # 200ms pause should generate a sleep token
        parts, is_enter = byte_to_sequence(ord('x'), 0.0, 0.2, min_sleep_threshold_ms=100)
        self.assertEqual(parts, ['[sleep:200]', 'x'])

    def test_byte_to_sequence_no_sleep_for_short_pause(self):
        """Test that short pauses don't generate sleep tokens."""
        from savetty import byte_to_sequence

        # 50ms pause should not generate a sleep token (below 100ms threshold)
        parts, is_enter = byte_to_sequence(ord('x'), 0.0, 0.05, min_sleep_threshold_ms=100)
        self.assertEqual(parts, ['x'])


class TestRoundTrip(unittest.TestCase):
    """Test that sequences generated by savetty can be parsed by testty."""

    def test_roundtrip_simple_sequence(self):
        """Test that a simple sequence roundtrips correctly."""
        # Generate a sequence that savetty might produce
        sequence = "hello[enter][ctrl-q]"

        # Parse it with testty
        tokens = parse_input_string(sequence)

        # Verify we get the expected tokens
        expected = [b'h', b'e', b'l', b'l', b'o', b'\r', b'\x11']
        self.assertEqual(tokens, expected)

    def test_roundtrip_with_special_keys(self):
        """Test roundtrip with arrow keys and other special sequences."""
        sequence = "[up][down][left][right][tab][esc][backspace]"

        tokens = parse_input_string(sequence)

        expected = [
            b'\x1b[A',  # up
            b'\x1b[B',  # down
            b'\x1b[D',  # left
            b'\x1b[C',  # right
            b'\t',      # tab
            b'\x1b',    # esc
            b'\x7f',    # backspace
        ]
        self.assertEqual(tokens, expected)

    def test_roundtrip_with_sleep_and_expect(self):
        """Test roundtrip with sleep and EXPECT_SCREEN tokens."""
        sequence = "[sleep:100]hello[EXPECT_SCREEN:snap.txt][ctrl-q]"

        tokens = parse_input_string(sequence)

        # Verify sleep and expect_screen tokens are tuples
        self.assertEqual(tokens[0], ('sleep', 100))
        expect_tokens = [t for t in tokens if isinstance(t, tuple) and t[0] == 'expect_screen']
        self.assertEqual(len(expect_tokens), 1)
        self.assertEqual(expect_tokens[0], ('expect_screen', 'snap.txt'))


if __name__ == "__main__":
    unittest.main()
