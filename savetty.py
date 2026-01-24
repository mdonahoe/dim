#!/usr/bin/env python3
"""
savetty - Record keystrokes and screen state of TUI sessions

Usage: python savetty.py <command> [args...]

This tool wraps a TUI application transparently, recording all keystrokes
including pauses. When the wrapped command exits, it prints the keystroke
sequence to stdout in the format expected by testty.py.

Additionally, whenever Enter is pressed, a screen snapshot is saved to
snapshot001.txt, snapshot002.txt, etc.
"""

import sys
import os
import pty
import time
import select
import termios
import tty
import struct
import fcntl
import signal

# Import TerminalScreen from testty for screen rendering
from testty import TerminalScreen


def get_terminal_size():
    """Get the current terminal size."""
    try:
        result = os.get_terminal_size()
        return result.lines, result.columns
    except OSError:
        return 24, 80


def set_terminal_size(fd, rows, cols):
    """Set the terminal size for a PTY."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def is_terminal_response(data, i):
    """Check if data starting at position i is a terminal response sequence.

    Terminal responses we want to filter out:
    - Cursor Position Report (CPR): ESC [ Pn ; Pn R  (response to ESC[6n)
    - Device Attributes (DA): ESC [ ? Pn ; ... c or ESC [ > Pn ; ... c

    Returns the length of the response sequence if found, 0 otherwise.
    """
    if i >= len(data) or data[i] != 0x1b:
        return 0

    if i + 1 >= len(data) or data[i + 1] != ord('['):
        return 0

    # Look for the end of the CSI sequence
    j = i + 2
    while j < len(data):
        c = data[j]
        if c == ord('R'):
            # Cursor Position Report: ESC [ row ; col R
            return j - i + 1
        elif c == ord('c'):
            # Device Attributes response: ESC [ ... c
            return j - i + 1
        elif c in b'0123456789;?>' or (c >= ord('0') and c <= ord('9')):
            # Continue parsing parameters
            j += 1
        else:
            # Unknown sequence, not a terminal response we recognize
            break

    return 0


def byte_to_sequence(b, last_time, current_time, min_sleep_threshold_ms=100):
    """Convert a byte to its testty sequence representation.

    Returns a tuple of (sequence_parts, is_enter) where sequence_parts is a list
    of strings representing the sequence, and is_enter is True if this was an Enter key.
    """
    parts = []
    is_enter = False

    # Check if we need a sleep token
    if last_time is not None:
        elapsed_ms = int((current_time - last_time) * 1000)
        if elapsed_ms >= min_sleep_threshold_ms:
            parts.append(f"[sleep:{elapsed_ms}]")

    # Convert the byte to its sequence representation
    if b == 0x1b:  # Escape
        parts.append("[esc]")
    elif b == 0x0d or b == 0x0a:  # Enter (CR or LF)
        parts.append("[enter]")
        is_enter = True
    elif b == 0x09:  # Tab
        parts.append("[tab]")
    elif b == 0x7f:  # Backspace (DEL)
        parts.append("[backspace]")
    elif b < 0x20:  # Control characters
        # Convert control character back to letter
        letter = chr(b + ord('a') - 1)
        parts.append(f"[ctrl-{letter}]")
    elif b >= 0x20 and b < 0x7f:  # Printable ASCII
        parts.append(chr(b))
    else:
        # Non-ASCII byte, represent as hex escape
        parts.append(f"\\x{b:02x}")

    return parts, is_enter


def escape_sequence_to_token(seq):
    """Convert an escape sequence to a testty token."""
    if seq == b'\x1b[A':
        return "[up]"
    elif seq == b'\x1b[B':
        return "[down]"
    elif seq == b'\x1b[C':
        return "[right]"
    elif seq == b'\x1b[D':
        return "[left]"
    elif seq == b'\x1b[3~':
        return "[delete]"
    else:
        # Unknown escape sequence, return raw bytes
        return ''.join(f"\\x{b:02x}" for b in seq)


def process_input_bytes(data, recorded_sequence, last_key_time, snapshot_count, screen, min_sleep_threshold_ms=100):
    """Process input bytes and update recorded sequence.

    Returns (updated_last_key_time, updated_snapshot_count, list of enter positions).
    """
    current_time = time.time()
    enter_positions = []
    i = 0

    while i < len(data):
        byte = data[i]

        # Check for escape sequences
        if byte == 0x1b and i + 1 < len(data):
            # Potential escape sequence
            if i + 2 < len(data) and data[i+1] == ord('['):
                # CSI sequence
                if data[i+2] == ord('A'):
                    # Check for sleep
                    if last_key_time is not None:
                        elapsed_ms = int((current_time - last_key_time) * 1000)
                        if elapsed_ms >= min_sleep_threshold_ms:
                            recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                    recorded_sequence.append("[up]")
                    i += 3
                    last_key_time = current_time
                    continue
                elif data[i+2] == ord('B'):
                    if last_key_time is not None:
                        elapsed_ms = int((current_time - last_key_time) * 1000)
                        if elapsed_ms >= min_sleep_threshold_ms:
                            recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                    recorded_sequence.append("[down]")
                    i += 3
                    last_key_time = current_time
                    continue
                elif data[i+2] == ord('C'):
                    if last_key_time is not None:
                        elapsed_ms = int((current_time - last_key_time) * 1000)
                        if elapsed_ms >= min_sleep_threshold_ms:
                            recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                    recorded_sequence.append("[right]")
                    i += 3
                    last_key_time = current_time
                    continue
                elif data[i+2] == ord('D'):
                    if last_key_time is not None:
                        elapsed_ms = int((current_time - last_key_time) * 1000)
                        if elapsed_ms >= min_sleep_threshold_ms:
                            recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                    recorded_sequence.append("[left]")
                    i += 3
                    last_key_time = current_time
                    continue
                elif i + 3 < len(data) and data[i+2] == ord('3') and data[i+3] == ord('~'):
                    if last_key_time is not None:
                        elapsed_ms = int((current_time - last_key_time) * 1000)
                        if elapsed_ms >= min_sleep_threshold_ms:
                            recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                    recorded_sequence.append("[delete]")
                    i += 4
                    last_key_time = current_time
                    continue

        # Regular byte processing
        parts, is_enter = byte_to_sequence(byte, last_key_time, current_time, min_sleep_threshold_ms)
        recorded_sequence.extend(parts)
        last_key_time = current_time

        if is_enter:
            # Record the position for snapshot
            enter_positions.append((len(recorded_sequence), snapshot_count + len(enter_positions) + 1))

        i += 1

    return last_key_time, snapshot_count + len(enter_positions), enter_positions


def save_snapshot(screen, snapshot_num, output_dir="."):
    """Save the current screen state to a snapshot file."""
    filename = os.path.join(output_dir, f"snapshot{snapshot_num:03d}.txt")
    screen_text = screen.get_screen_text()
    with open(filename, 'w') as f:
        f.write(screen_text)
        if screen_text and not screen_text.endswith('\n'):
            f.write('\n')
    return filename


def run_with_recording(command, output_dir=".", min_sleep_threshold_ms=100):
    """Run a command in a PTY, recording keystrokes and screen snapshots.

    Args:
        command: List of command and arguments to run
        output_dir: Directory to save snapshot files
        min_sleep_threshold_ms: Minimum pause duration to record as [sleep:N]

    Returns:
        A tuple of (keystroke_sequence, snapshot_files, rows, cols) where:
        - keystroke_sequence is the recorded sequence string
        - snapshot_files is a list of saved snapshot filenames
        - rows, cols are the terminal dimensions used
    """
    rows, cols = get_terminal_size()
    screen = TerminalScreen(rows, cols)
    recorded_sequence = []
    snapshot_count = 0
    snapshot_files = []
    last_key_time = None
    pending_snapshots = []  # List of (sequence_position, snapshot_num)

    # Create PTY
    master_fd, slave_fd = pty.openpty()
    set_terminal_size(master_fd, rows, cols)

    # Save original terminal settings
    old_settings = None
    stdin_fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(stdin_fd)
    except termios.error:
        pass

    pid = os.fork()

    if pid == 0:
        # Child process
        os.close(master_fd)
        os.setsid()

        # Make slave the controlling terminal
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)

        if slave_fd > 2:
            os.close(slave_fd)

        # Execute the command
        try:
            os.execvp(command[0], command)
        except Exception as e:
            print(f"Failed to execute {command[0]}: {e}", file=sys.stderr)
            os._exit(1)
    else:
        # Parent process
        os.close(slave_fd)

        # Set stdin to raw mode
        if old_settings is not None:
            tty.setraw(stdin_fd)

        # Set master_fd to non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Handle window resize
        def handle_sigwinch(signum, frame):
            nonlocal rows, cols, screen
            rows, cols = get_terminal_size()
            set_terminal_size(master_fd, rows, cols)
            # Resize screen emulator
            screen = TerminalScreen(rows, cols)

        signal.signal(signal.SIGWINCH, handle_sigwinch)

        try:
            while True:
                # Wait for input from either stdin or the PTY
                try:
                    readable, _, _ = select.select([stdin_fd, master_fd], [], [], 0.1)
                except (ValueError, OSError):
                    break

                # Check if child process has exited
                try:
                    wpid, status = os.waitpid(pid, os.WNOHANG)
                    if wpid == pid:
                        # Child exited, drain any remaining output
                        try:
                            while True:
                                chunk = os.read(master_fd, 4096)
                                if not chunk:
                                    break
                                os.write(sys.stdout.fileno(), chunk)
                                screen.process_output(chunk)
                        except (OSError, BlockingIOError):
                            pass
                        break
                except ChildProcessError:
                    break

                for fd in readable:
                    if fd == stdin_fd:
                        # Read from stdin and forward to PTY
                        try:
                            data = os.read(stdin_fd, 1024)
                            if not data:
                                continue

                            # Forward to child
                            os.write(master_fd, data)

                            # Record the keystrokes
                            current_time = time.time()
                            i = 0
                            while i < len(data):
                                byte = data[i]

                                # Check for and skip terminal response sequences
                                # These are sent by the terminal in response to queries (e.g., cursor position)
                                response_len = is_terminal_response(data, i)
                                if response_len > 0:
                                    i += response_len
                                    continue

                                # Check for escape sequences (user input)
                                if byte == 0x1b and i + 2 < len(data) and data[i+1] == ord('['):
                                    # CSI sequence
                                    if data[i+2] == ord('A'):
                                        if last_key_time is not None:
                                            elapsed_ms = int((current_time - last_key_time) * 1000)
                                            if elapsed_ms >= min_sleep_threshold_ms:
                                                recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                                        recorded_sequence.append("[up]")
                                        i += 3
                                        last_key_time = current_time
                                        continue
                                    elif data[i+2] == ord('B'):
                                        if last_key_time is not None:
                                            elapsed_ms = int((current_time - last_key_time) * 1000)
                                            if elapsed_ms >= min_sleep_threshold_ms:
                                                recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                                        recorded_sequence.append("[down]")
                                        i += 3
                                        last_key_time = current_time
                                        continue
                                    elif data[i+2] == ord('C'):
                                        if last_key_time is not None:
                                            elapsed_ms = int((current_time - last_key_time) * 1000)
                                            if elapsed_ms >= min_sleep_threshold_ms:
                                                recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                                        recorded_sequence.append("[right]")
                                        i += 3
                                        last_key_time = current_time
                                        continue
                                    elif data[i+2] == ord('D'):
                                        if last_key_time is not None:
                                            elapsed_ms = int((current_time - last_key_time) * 1000)
                                            if elapsed_ms >= min_sleep_threshold_ms:
                                                recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                                        recorded_sequence.append("[left]")
                                        i += 3
                                        last_key_time = current_time
                                        continue
                                    elif i + 3 < len(data) and data[i+2] == ord('3') and data[i+3] == ord('~'):
                                        if last_key_time is not None:
                                            elapsed_ms = int((current_time - last_key_time) * 1000)
                                            if elapsed_ms >= min_sleep_threshold_ms:
                                                recorded_sequence.append(f"[sleep:{elapsed_ms}]")
                                        recorded_sequence.append("[delete]")
                                        i += 4
                                        last_key_time = current_time
                                        continue

                                # Regular byte processing
                                parts, is_enter = byte_to_sequence(byte, last_key_time, current_time, min_sleep_threshold_ms)
                                recorded_sequence.extend(parts)
                                last_key_time = current_time

                                if is_enter:
                                    # Schedule a snapshot to be taken after output is processed
                                    snapshot_count += 1
                                    pending_snapshots.append(snapshot_count)

                                i += 1

                        except (OSError, BlockingIOError):
                            pass

                    elif fd == master_fd:
                        # Read from PTY and forward to stdout
                        try:
                            chunk = os.read(master_fd, 4096)
                            if chunk:
                                os.write(sys.stdout.fileno(), chunk)
                                screen.process_output(chunk)

                                # Save any pending snapshots after output is processed
                                for snap_num in pending_snapshots:
                                    filename = save_snapshot(screen, snap_num, output_dir)
                                    snapshot_files.append(filename)
                                    # Insert EXPECT_SCREEN marker into recorded sequence
                                    recorded_sequence.append(f"[EXPECT_SCREEN:snapshot{snap_num:03d}.txt]")
                                pending_snapshots = []
                        except (OSError, BlockingIOError):
                            pass

        except KeyboardInterrupt:
            pass
        finally:
            # Restore terminal settings
            if old_settings is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)

            os.close(master_fd)

            # Make sure child is terminated
            try:
                os.kill(pid, signal.SIGTERM)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass

    # Build the final sequence string
    sequence = ''.join(recorded_sequence)
    return sequence, snapshot_files, rows, cols


def main():
    if len(sys.argv) < 2:
        print("Usage: python savetty.py <command> [args...]", file=sys.stderr)
        print("\nRecord keystrokes and screen snapshots from a TUI session.", file=sys.stderr)
        print("Prints the testty command to stdout when the session ends.", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1:]

    # Run the recording
    sequence, snapshot_files, rows, cols = run_with_recording(command)

    # Build the full testty command
    cmd_str = ' '.join(command)
    # Escape single quotes in the sequence for shell safety
    escaped_sequence = sequence.replace("'", "'\"'\"'")

    testty_cmd = f"python testty.py --run '{cmd_str}' --rows {rows} --cols {cols} --input '{escaped_sequence}'"
    if snapshot_files:
        testty_cmd += " --snapshot-dir ."

    # Print summary to stderr, testty command to stdout
    print("\n", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Recording complete!", file=sys.stderr)
    print(f"Terminal size: {rows} rows x {cols} cols", file=sys.stderr)
    if snapshot_files:
        print(f"Saved {len(snapshot_files)} snapshot(s):", file=sys.stderr)
        for f in snapshot_files:
            print(f"  - {f}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("\nReplay command:", file=sys.stderr)
    print(testty_cmd)


if __name__ == '__main__':
    main()
