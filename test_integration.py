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

        # The recorded input sequence
        input_sequence = (
            "w[sleep:1435]cw[sleep:1066]Test[sleep:2025][esc][sleep:1022]0[sleep:602]"
            "[enter][EXPECT_SCREEN:snapshot001.txt][sleep:1231]jyyp[sleep:1935]"
            "[enter][EXPECT_SCREEN:snapshot002.txt][sleep:668]jj[sleep:1010]$[sleep:734]"
            "%[sleep:2236]a [sleep:903]a [sleep:608]kjA [sleep:1008]hellojj[sleep:858]"
            "k[sleep:1581]0w[sleep:720]dw[sleep:2794]cool[sleep:723][backspace][backspace]"
            "[sleep:813][backspace][sleep:958]jj[sleep:998]kkk[sleep:2101]$[sleep:994]"
            "a [sleep:3443]a [sleep:623]i [sleep:543]this is a test[sleep:692]"
            "[enter][EXPECT_SCREEN:snapshot003.txt][sleep:2385][esc][sleep:1115]k[sleep:960]"
            ":q![sleep:1663][enter]"
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
