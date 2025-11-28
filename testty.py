#!/usr/bin/env python3
"""
testty - A tool for testing interactive TTY programs non-interactively
Usage: testty --run PROGRAM [--input INPUT_STRING] [--output FILE] [--delay MS]
"""

import sys
import os
import pty
import time
import argparse
import termios
import struct
import fcntl
from dataclasses import dataclass
from typing import Optional


@dataclass
class Result:
    """Result from running a command in a PTY."""
    output: str
    raw: bytes
    did_exit: bool
    exit_code: Optional[int]


class TerminalScreen:
    """Simple terminal screen emulator that processes ANSI escape sequences."""

    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.buffer = [[' ' for _ in range(cols)] for _ in range(rows)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.saved_cursor = (0, 0)

    def process_output(self, data):
        """Process terminal output byte by byte."""
        i = 0
        while i < len(data):
            # Check for escape sequence
            if data[i:i+1] == b'\x1b':
                i = self._process_escape(data, i)
            elif data[i:i+1] == b'\r':
                # Carriage return
                self.cursor_col = 0
                i += 1
            elif data[i:i+1] == b'\n':
                # Line feed
                self.cursor_row = min(self.cursor_row + 1, self.rows - 1)
                i += 1
            elif data[i:i+1] == b'\t':
                # Tab - move to next tab stop (every 8 chars)
                self.cursor_col = ((self.cursor_col // 8) + 1) * 8
                if self.cursor_col >= self.cols:
                    self.cursor_col = self.cols - 1
                i += 1
            elif data[i:i+1] == b'\b':
                # Backspace
                self.cursor_col = max(0, self.cursor_col - 1)
                i += 1
            else:
                # Regular character
                try:
                    char = chr(data[i])
                    if self.cursor_row < self.rows and self.cursor_col < self.cols:
                        self.buffer[self.cursor_row][self.cursor_col] = char
                        self.cursor_col += 1
                        if self.cursor_col >= self.cols:
                            self.cursor_col = 0
                            self.cursor_row = min(self.cursor_row + 1, self.rows - 1)
                except (ValueError, UnicodeDecodeError):
                    pass
                i += 1

        return i

    def _process_escape(self, data, i):
        """Process ANSI escape sequence starting at position i."""
        if i + 1 >= len(data):
            return i + 1

        if data[i+1:i+2] == b'[':
            # CSI sequence
            return self._process_csi(data, i + 2)
        elif data[i+1:i+2] == b']':
            # OSC sequence (operating system command) - skip it
            end = data.find(b'\x07', i)
            if end == -1:
                end = data.find(b'\x1b\\', i)
                if end == -1:
                    return len(data)
                return end + 2
            return end + 1
        else:
            # Unknown escape sequence, skip 2 bytes
            return i + 2

    def _process_csi(self, data, i):
        """Process CSI (Control Sequence Introducer) sequence."""
        # Find the end of the CSI sequence
        j = i
        while j < len(data) and data[j:j+1] in b'0123456789;?':
            j += 1

        if j >= len(data):
            return len(data)

        command = chr(data[j])
        params_str = data[i:j].decode('ascii', errors='ignore')
        params = []
        if params_str and not params_str.startswith('?'):
            try:
                params = [int(p) if p else 0 for p in params_str.split(';')]
            except ValueError:
                params = []

        # Process the command
        if command == 'H' or command == 'f':
            # Cursor position
            row = (params[0] - 1) if len(params) > 0 and params[0] > 0 else 0
            col = (params[1] - 1) if len(params) > 1 and params[1] > 0 else 0
            self.cursor_row = min(row, self.rows - 1)
            self.cursor_col = min(col, self.cols - 1)
        elif command == 'A':
            # Cursor up
            n = params[0] if params else 1
            self.cursor_row = max(0, self.cursor_row - n)
        elif command == 'B':
            # Cursor down
            n = params[0] if params else 1
            self.cursor_row = min(self.rows - 1, self.cursor_row + n)
        elif command == 'C':
            # Cursor forward
            n = params[0] if params else 1
            self.cursor_col = min(self.cols - 1, self.cursor_col + n)
        elif command == 'D':
            # Cursor back
            n = params[0] if params else 1
            self.cursor_col = max(0, self.cursor_col - n)
        elif command == 'J':
            # Erase in display
            n = params[0] if params else 0
            if n == 0:
                # Clear from cursor to end of screen
                for c in range(self.cursor_col, self.cols):
                    self.buffer[self.cursor_row][c] = ' '
                for r in range(self.cursor_row + 1, self.rows):
                    self.buffer[r] = [' '] * self.cols
            elif n == 1:
                # Clear from cursor to beginning of screen
                for c in range(0, self.cursor_col + 1):
                    self.buffer[self.cursor_row][c] = ' '
                for r in range(0, self.cursor_row):
                    self.buffer[r] = [' '] * self.cols
            elif n == 2:
                # Clear entire screen
                self.buffer = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        elif command == 'K':
            # Erase in line
            n = params[0] if params else 0
            if n == 0:
                # Clear from cursor to end of line
                for c in range(self.cursor_col, self.cols):
                    self.buffer[self.cursor_row][c] = ' '
            elif n == 1:
                # Clear from cursor to beginning of line
                for c in range(0, self.cursor_col + 1):
                    self.buffer[self.cursor_row][c] = ' '
            elif n == 2:
                # Clear entire line
                self.buffer[self.cursor_row] = [' '] * self.cols
        elif command == 's':
            # Save cursor position
            self.saved_cursor = (self.cursor_row, self.cursor_col)
        elif command == 'u':
            # Restore cursor position
            self.cursor_row, self.cursor_col = self.saved_cursor
        # Ignore color codes (m), cursor visibility (?25h, ?25l), and other formatting

        return j + 1

    def get_screen_text(self):
        """Return the current screen as a string."""
        lines = []
        for row in self.buffer:
            line = ''.join(row).rstrip()
            lines.append(line)

        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()

        return '\n'.join(lines)

def parse_input_string(input_str):
    """Parse input string and convert special sequences to bytes."""
    if not input_str:
        return []

    tokens = []
    i = 0
    while i < len(input_str):
        if input_str[i] == '[':
            # Find the closing bracket
            end = input_str.find(']', i)
            if end == -1:
                tokens.append(input_str[i].encode())
                i += 1
                continue

            special = input_str[i+1:end].lower()

            # Handle special keys
            if special == 'enter':
                tokens.append(b'\r')
            elif special == 'tab':
                tokens.append(b'\t')
            elif special == 'esc':
                tokens.append(b'\x1b')
            elif special == 'backspace':
                tokens.append(b'\x7f')
            elif special == 'delete':
                tokens.append(b'\x1b[3~')
            elif special.startswith('ctrl-'):
                key = special[5:]
                if len(key) == 1:
                    # Convert ctrl-x to control character
                    ctrl_char = ord(key.upper()) & 0x1f
                    tokens.append(bytes([ctrl_char]))
                else:
                    raise ValueError(f"Invalid ctrl sequence: {special}")
            elif special == 'up':
                tokens.append(b'\x1b[A')
            elif special == 'down':
                tokens.append(b'\x1b[B')
            elif special == 'right':
                tokens.append(b'\x1b[C')
            elif special == 'left':
                tokens.append(b'\x1b[D')
            elif special.startswith('sleep:'):
                # Sleep for specified milliseconds
                ms = int(special[6:])
                tokens.append(('sleep', ms))
            else:
                raise ValueError(f"Unknown special sequence: {special}")

            i = end + 1
        else:
            tokens.append(input_str[i].encode())
            i += 1

    return tokens

def set_terminal_size(fd, rows=24, cols=80):
    """Set the terminal size for the PTY."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def run_with_pty(command, input_tokens, delay_ms=10, timeout=5.0, rows=24, cols=80):
    """Run a command in a PTY and send input tokens to it.

    Args:
        command: List of command and arguments to run
        input_tokens: List of input tokens (from parse_input_string)
        delay_ms: Delay in milliseconds between keystrokes
        timeout: Timeout in seconds
        rows: Terminal rows
        cols: Terminal columns

    Returns:
        Result object with output, raw, did_exit, and exit_code fields
    """

    screen = TerminalScreen(rows, cols)
    snapshot_screen = None
    process_exited = False
    exit_code = None
    raw_output = b''

    # Create a pseudo-terminal
    master_fd, slave_fd = pty.openpty()

    # Set terminal size
    set_terminal_size(master_fd, rows, cols)

    try:
        # Fork the process
        pid = os.fork()

        if pid == 0:
            # Child process
            os.close(master_fd)

            # Make the PTY the controlling terminal
            os.setsid()

            # Redirect stdin, stdout, stderr to the slave PTY
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)

            if slave_fd > 2:
                os.close(slave_fd)

            # Execute the command
            os.execvp(command[0], command)
        else:
            # Parent process
            os.close(slave_fd)

            # Set non-blocking mode on master_fd
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Give the program a moment to start
            time.sleep(0.1)

            # Read initial output
            try:
                chunk = os.read(master_fd, 4096)
                raw_output += chunk
                screen.process_output(chunk)
            except OSError:
                pass

            # Send input tokens, but capture screen before the last one
            for i, token in enumerate(input_tokens):
                # Take a snapshot before the last token (usually the quit command)
                if i == len(input_tokens) - 1:
                    snapshot_screen = screen.get_screen_text()

                if isinstance(token, tuple) and token[0] == 'sleep':
                    time.sleep(token[1] / 1000.0)
                    # After sleep, also read output
                    try:
                        chunk = os.read(master_fd, 4096)
                        raw_output += chunk
                        screen.process_output(chunk)
                    except OSError:
                        pass
                else:
                    os.write(master_fd, token)
                    time.sleep(delay_ms / 1000.0)

                    # Read any output after each input
                    try:
                        chunk = os.read(master_fd, 4096)
                        raw_output += chunk
                        screen.process_output(chunk)
                    except OSError:
                        pass

            # Wait a bit for final output
            time.sleep(0.2)

            # Read remaining output
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    chunk = os.read(master_fd, 4096)
                    if chunk:
                        raw_output += chunk
                        screen.process_output(chunk)
                    else:
                        break
                except OSError:
                    # No more data
                    break

                # Check if process is still running
                try:
                    wpid, status = os.waitpid(pid, os.WNOHANG)
                    if wpid == pid:
                        process_exited = True
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
                        break
                except ChildProcessError:
                    process_exited = True
                    break

            # Check one more time if process exited after timeout
            if not process_exited:
                try:
                    wpid, status = os.waitpid(pid, os.WNOHANG)
                    if wpid == pid:
                        process_exited = True
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
                except ChildProcessError:
                    process_exited = True

            # Try to terminate the process if it's still running
            if not process_exited:
                try:
                    os.kill(pid, 15)  # SIGTERM
                    wpid, status = os.waitpid(pid, 0)
                    if wpid == pid:
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
                except (ProcessLookupError, ChildProcessError):
                    process_exited = True

    finally:
        os.close(master_fd)

    # Return the snapshot if we took one and current screen is empty
    final_screen = screen.get_screen_text()
    if snapshot_screen and not final_screen.strip():
        final_screen = snapshot_screen

    return Result(
        output=final_screen,
        raw=raw_output,
        did_exit=process_exited,
        exit_code=exit_code
    )

def unused_method():
    "this can be deleted"
    pass

def main():
    parser = argparse.ArgumentParser(
        description='Test interactive TTY programs non-interactively',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  testty --run "./dim test.txt" --input "hello[ctrl-s][ctrl-q]"
  testty --run "vim" --input "iHello World[esc]:wq[enter]" --delay 50
  testty --run "./dim" --input "test[ctrl-s]file.txt[enter][ctrl-q]" --output result.txt

Special sequences:
  [enter]      - Enter/Return key
  [ctrl-X]     - Control+X (e.g., [ctrl-s], [ctrl-q])
  [tab]        - Tab key
  [esc]        - Escape key
  [backspace]  - Backspace
  [up/down/left/right] - Arrow keys
  [sleep:N]    - Sleep for N milliseconds
        """
    )

    parser.add_argument('--run', required=True, help='Command to run')
    parser.add_argument('--input', default='', help='Input string to send')
    parser.add_argument('--output', help='File to write output to (default: stdout)')
    parser.add_argument('--delay', type=int, default=10, help='Delay in ms between keystrokes (default: 10)')
    parser.add_argument('--timeout', type=float, default=5.0, help='Timeout in seconds (default: 5.0)')
    parser.add_argument('--rows', type=int, default=24, help='Terminal rows (default: 24)')
    parser.add_argument('--cols', type=int, default=80, help='Terminal columns (default: 80)')

    args = parser.parse_args()

    # Parse the command
    command = args.run.split()

    # Parse the input string
    try:
        input_tokens = parse_input_string(args.input)
    except ValueError as e:
        print(f"Error parsing input string: {e}", file=sys.stderr)
        return 1

    # Run the command
    result = run_with_pty(command, input_tokens, args.delay, args.timeout, args.rows, args.cols)

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(result.output)
            if result.output and not result.output.endswith('\n'):
                f.write('\n')
    else:
        # Print to stdout
        print(result.output)

    return 0

if __name__ == '__main__':
    sys.exit(main())
