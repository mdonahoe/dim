#!/usr/bin/env python3
"""
Integration tests for dim editor using recorded user sessions.

These tests replay recorded user sessions and verify screen snapshots match.
"""

import os
import sys
import unittest
import subprocess

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TestUserSession1(unittest.TestCase):
    """Integration test from user-session-1 recording."""

    def setUp(self):
        """Ensure we're in the right directory."""
        os.chdir(SCRIPT_DIR)

    def test_user_session_1(self):
        """
        Replay user-session-1 which tests:
        - Opening example.c
        - Word motion (w) and change word (cw)
        - Yank line (yy) and paste (p)
        - Navigation ($, %, j, k)
        - Insert mode and text editing
        - Quit without save (:q!)
        """
        session_dir = os.path.join(SCRIPT_DIR, "user-session-1")

        # The recorded input sequence (minimal sleeps only before screen checks)
        input_sequence = (
            "wcwTest[esc]0"
            "[enter][sleep:50][EXPECT_SCREEN:snapshot001.txt]jyyp"
            "[enter][sleep:50][EXPECT_SCREEN:snapshot002.txt]jj$"
            "%a a kjA hellojj"
            "k0wdwcool[backspace][backspace]"
            "[backspace]jjkkk$"
            "a a i this is a test"
            "[enter][sleep:50][EXPECT_SCREEN:snapshot003.txt][esc]k"
            ":q![enter]"
        )

        result = subprocess.run(
            [
                sys.executable, "testty.py",
                "--run", "./dim example.c",
                "--rows", "49",
                "--cols", "161",
                "--input", input_sequence,
                "--snapshot-dir", session_dir,
                "--timeout", "10.0"
            ],
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR
        )

        # Check for success
        if result.returncode != 0:
            self.fail(
                f"Integration test failed with exit code {result.returncode}\n"
                f"stderr: {result.stderr}\n"
                f"stdout: {result.stdout}"
            )


if __name__ == "__main__":
    unittest.main()
