def name():
    """Return the planner name."""
    return "IncludePathResolver"

def can_handle(clue_type):
    """Handle missing_file clues where the path is a relative include."""
    return clue_type == "missing_file"

def plan(clues, git_state):
    """Resolve missing include paths to actual file paths in git.

    When a compiler reports 'file.h: No such file or directory', the path
    is often a relative include path (e.g., 'tree_sitter/parser.h') rather
    than the actual file path in the repo (e.g., 'tree-sitter/lib/include/tree_sitter/parser.h').

    This planner handles two cases:
    1. Direct suffix match: deleted file ends with the include path
    2. Symlink target: include path resolves to a symlink whose target is deleted

    For case 2, it matches files with the same basename when directory components
    of the include path appear in the deleted file path (accounting for variations
    like tree_sitter vs tree-sitter).
    """
    plans = []
    seen_targets = {}

    for clue in clues:
        if clue["clue_type"] != "missing_file":
            continue

        file_path = clue["context"].get("file_path", "")
        if not file_path:
            continue

        # Skip if this exact path is in deleted_files (default planner handles it)
        if file_path in git_state.get("deleted_files", []):
            continue

        # Skip if we've already planned to restore this
        if file_path in seen_targets:
            continue

        deleted = git_state.get("deleted_files", [])

        # Strategy 1: Direct suffix match
        found = False
        for deleted_file in deleted:
            if deleted_file.endswith("/" + file_path) or deleted_file == file_path:
                if deleted_file not in seen_targets:
                    seen_targets[deleted_file] = True
                    seen_targets[file_path] = True
                    plans.append({
                        "plan_type": "restore_file",
                        "priority": -5,
                        "target_file": deleted_file,
                        "action": "restore_full",
                        "params": {"ref": git_state["ref"]},
                        "reason": "Restore " + deleted_file + " (matches include path " + file_path + ")",
                    })
                    found = True
                    break

        if found:
            continue

        # Strategy 2: Match by basename + related directory names
        # This handles symlinks where the target has a different path structure
        basename = path_basename(file_path)
        if "/" in file_path:
            # Extract directory components and normalize (replace _ with -)
            dirname = path_dirname(file_path)
            # Get path components for matching
            dir_parts = dirname.replace("_", "-").lower().split("/")

            for deleted_file in deleted:
                if not deleted_file.endswith("/" + basename) and not deleted_file == basename:
                    continue

                # Check if deleted file path contains related directory names
                deleted_lower = deleted_file.replace("_", "-").lower()
                match_score = 0
                for part in dir_parts:
                    if part and part in deleted_lower:
                        match_score += 1

                # Require at least one directory component to match
                if match_score > 0:
                    if deleted_file not in seen_targets:
                        seen_targets[deleted_file] = True
                        seen_targets[file_path] = True
                        plans.append({
                            "plan_type": "restore_file",
                            "priority": -5,
                            "target_file": deleted_file,
                            "action": "restore_full",
                            "params": {"ref": git_state["ref"]},
                            "reason": "Restore " + deleted_file + " (symlink target for include " + file_path + ")",
                        })
                        break

    return plans
