#!/usr/bin/env python3
"""
Given a linker error log on stdin or in a file, extract undefined symbols,
search the repo for them, and show:

- Where they are currently defined/mentioned (if anywhere)
- Commits where files containing them were deleted (likely the “oops I rm -rf’d runtime” case)

Usage:
  python diagnose_undef.py               # read error text from stdin
  python diagnose_undef.py error.log     # read error text from file
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from textwrap import indent

UNDEF_RE = re.compile(r"undefined reference to `([^`']+)'")

def run(cmd, cwd=None):
    try:
        out = subprocess.check_output(
            cmd, cwd=cwd, stderr=subprocess.STDOUT, text=True
        )
        return out
    except subprocess.CalledProcessError as e:
        return e.output

def is_git_repo(path):
    try:
        subprocess.check_call(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False

def extract_undefined_symbols(text):
    return sorted(set(UNDEF_RE.findall(text)))

def find_current_occurrences(symbol, use_git=True):
    """
    Search current tree for the symbol.

    Prefer `git grep`, fall back to `rg`, then plain `grep`.
    """
    cmds = []
    if use_git:
        cmds.append(["git", "grep", "-n", symbol])
    cmds.append(["rg", "-n", symbol])
    cmds.append(["grep", "-RIn", symbol, "."])

    for cmd in cmds:
        try:
            out = subprocess.check_output(
                cmd, stderr=subprocess.DEVNULL, text=True
            )
            if out.strip():
                return out.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    return ""

def find_deleted_files_for_symbol(symbol):
    """
    Use git log -S to find commits where this symbol appeared, and
    filter for deletions in those commits.
    """
    # -S: search for changes that add/remove the string
    # --name-status: show added/modified/deleted files
    cmd = ["git", "log", "-S", symbol, "--name-status", "--pretty=format:%H %ad %an %s", "--date=short"]
    out = run(cmd)

    if not out.strip():
        return ""

    lines = out.splitlines()
    result_lines = []
    current_header = None

    for line in lines:
        if not line:
            continue
        # Commit header: starts with a hex hash
        if re.match(r"^[0-9a-f]{7,40} ", line):
            current_header = line
            continue
        # Name-status line: e.g. "D\tpath/to/file.c"
        if line.startswith("D\t"):
            if current_header and current_header not in result_lines:
                result_lines.append(current_header)
            result_lines.append(line)

    return "\n".join(result_lines).strip()

def group_by_prefix(symbols, min_shared=3):
    """
    Try to find a common prefix across symbols (e.g., 'ts_'),
    just for display.
    """
    if not symbols:
        return None

    # Start with the first symbol and shrink common prefix.
    prefix = symbols[0]
    for sym in symbols[1:]:
        while not sym.startswith(prefix) and prefix:
            prefix = prefix[:-1]
        if not prefix:
            break

    if len(prefix) < min_shared:
        return None
    return prefix

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[0 if len(sys.argv) == 1 else 1], "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    symbols = extract_undefined_symbols(text)

    if not symbols:
        print("No 'undefined reference' symbols found in the input.")
        return

    print("=== Extracted undefined symbols ===")
    for s in symbols:
        print(f"  {s}")

    prefix = group_by_prefix(symbols)
    if prefix:
        print(f"\nHeuristic: common symbol prefix detected: '{prefix}'")
        print("This often indicates a missing or broken library containing that family of symbols.\n")

    cwd = os.getcwd()
    use_git = is_git_repo(cwd)

    if not use_git:
        print("Warning: current directory is not a git repository; deletion history can't be inspected.\n")

    print("=== Current working tree search ===")
    for s in symbols:
        print(f"\n--- Symbol: {s} ---")
        hits = find_current_occurrences(s, use_git=use_git)
        if hits:
            print("Found mentions in current tree:")
            print(indent(hits, "    "))
        else:
            print("No occurrences in current tree (source may be missing or never present).")

    if use_git:
        print("\n=== Git history: deleted files containing these symbols ===")
        for s in symbols:
            print(f"\n--- Symbol: {s} ---")
            deletions = find_deleted_files_for_symbol(s)
            if deletions:
                print("Commits where files containing this symbol were deleted:")
                print(indent(deletions, "    "))
            else:
                print("No deletions found in history for this symbol (or symbol never committed).")
    else:
        print("\nSkipped git-history analysis (not a git repo).")

if __name__ == "__main__":
    main()

