def name():
    """Return the planner name."""
    return "UndefinedSymbolRestorer"

def can_handle(clue_type):
    """Handle linker undefined symbols clues."""
    return clue_type == "linker_undefined_symbols"

def plan(clues, git_state):
    """Restore partial files that contain undefined symbols.

    When linker reports undefined symbols and there are partial files,
    search git history to find which partial file defines the symbol
    and restore it.
    """
    plans = []
    seen_files = {}

    partial_files = git_state.get("partial_files", [])
    deleted_files = git_state.get("deleted_files", []) or []
    ref = git_state["ref"]

    # Build set of partial file paths (handle both "file" and "File" keys)
    partial_paths = {}
    for pf in partial_files:
        file_path = pf.get("file") or pf.get("File", "")
        if file_path:
            partial_paths[file_path] = True

    log("UndefinedSymbolRestorer: partial_paths = " + str(partial_paths))

    for clue in clues:
        if clue["clue_type"] != "linker_undefined_symbols":
            continue

        symbol = clue["context"].get("symbol", "")
        if not symbol:
            continue

        log("UndefinedSymbolRestorer: Looking for symbol: " + symbol)

        # Search git history for files that define this symbol
        matches = git_grep(symbol, ref)
        log("UndefinedSymbolRestorer: git_grep found " + str(len(matches)) + " matches")

        for match in matches:
            file_path = match[0]
            log("UndefinedSymbolRestorer: Checking file: " + file_path)

            # Skip if already planned
            if file_path in seen_files:
                continue

            # Check if this file is in partial_files
            if file_path in partial_paths:
                # Verify the symbol is NOT in the current (broken) content
                current_content = read_file(file_path)
                if current_content and symbol in current_content:
                    log("UndefinedSymbolRestorer: Symbol already present in current file, skipping")
                    continue

                seen_files[file_path] = True
                log("UndefinedSymbolRestorer: Planning to restore partial file " + file_path)
                plans.append({
                    "plan_type": "restore_file",
                    "priority": -5,
                    "target_file": file_path,
                    "action": "restore_full",
                    "params": {"ref": ref},
                    "reason": "Restore partial file " + file_path + " (defines undefined symbol '" + symbol + "')",
                })

            # Also check if file was deleted
            if file_path in deleted_files:
                seen_files[file_path] = True
                log("UndefinedSymbolRestorer: Planning to restore deleted file " + file_path)
                plans.append({
                    "plan_type": "restore_file",
                    "priority": -5,
                    "target_file": file_path,
                    "action": "restore_full",
                    "params": {"ref": ref},
                    "reason": "Restore deleted file " + file_path + " (defines undefined symbol '" + symbol + "')",
                })

    log("UndefinedSymbolRestorer: Generated " + str(len(plans)) + " plans")
    return plans
