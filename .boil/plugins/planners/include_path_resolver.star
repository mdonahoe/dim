def name():
    """Return the planner name."""
    return "IncludePathResolver"

def can_handle(clue_type):
    """Handle missing_file clues."""
    return clue_type == "missing_file"

def plan(clues, git_state):
    """Resolve missing file paths to actual file paths in git.

    This planner handles three cases:
    1. Direct exact match: file path exactly matches a deleted file
    2. Suffix match: deleted file ends with the include path
    3. Basename + directory match: for symlinks where target has different path
    """
    plans = []
    seen_targets = {}

    deleted = git_state.get("deleted_files", [])
    deleted_set = {f: True for f in deleted}

    for clue in clues:
        if clue["clue_type"] != "missing_file":
            continue

        file_path = clue["context"].get("file_path", "")
        if not file_path:
            continue

        # Skip if we've already planned to restore this
        if file_path in seen_targets:
            continue

        # Strategy 1: Direct exact match in deleted_files
        if file_path in deleted_set:
            seen_targets[file_path] = True
            plans.append({
                "plan_type": "restore_file",
                "priority": -5,
                "target_file": file_path,
                "action": "restore_full",
                "params": {"ref": git_state["ref"]},
                "reason": "Restore " + file_path + " (direct match)",
            })
            continue

        # Strategy 2: Suffix match - deleted file ends with the include path
        found = False
        for deleted_file in deleted:
            if deleted_file.endswith("/" + file_path):
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

        # Strategy 3: Match by basename + related directory names
        # This handles symlinks where the target has a different path structure
        basename = path_basename(file_path)
        if "/" in file_path:
            dirname = path_dirname(file_path)
            dir_parts = dirname.replace("_", "-").lower().split("/")

            for deleted_file in deleted:
                if not deleted_file.endswith("/" + basename) and not deleted_file == basename:
                    continue

                deleted_lower = deleted_file.replace("_", "-").lower()
                match_score = 0
                for part in dir_parts:
                    if part and part in deleted_lower:
                        match_score += 1

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
