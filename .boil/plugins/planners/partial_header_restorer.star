def name():
    """Return the planner name."""
    return "PartialHeaderRestorer"

def can_handle(clue_type):
    """Handle unknown_type_name and undeclared_identifier clues."""
    return clue_type in ["unknown_type_name", "undeclared_identifier", "c_undeclared_identifier"]

def plan(clues, git_state):
    """Restore partial header files that are included by files with type errors.

    When a .c file has type errors and includes a header that's in partial_files,
    the root cause is likely the partial header. Restore it.
    """
    plans = []
    seen_files = {}

    partial_files = git_state.get("partial_files", [])
    if not partial_files:
        return plans

    # Build a set of partial file paths
    partial_paths = {}
    for pf in partial_files:
        partial_paths[pf["file"]] = pf

    for clue in clues:
        if clue["clue_type"] not in ["unknown_type_name", "undeclared_identifier", "c_undeclared_identifier"]:
            continue

        file_path = clue["context"].get("file_path", "")
        if not file_path:
            continue

        # Read the source file to find its includes
        content = read_file(file_path)
        if not content:
            continue

        # Find all #include directives
        includes = regex_find_all(r'#\s*include\s*"(?P<path>[^"]+)"', content)

        # Get the directory of the source file
        source_dir = path_dirname(file_path)

        for inc in includes:
            inc_path = inc["groups"]["path"]

            # Resolve the include path relative to source file directory
            full_path = path_join(source_dir, inc_path)

            # Check if this matches any partial file
            for partial_path in partial_paths:
                # Match either full path or if partial path ends with the include path
                if partial_path == full_path or partial_path.endswith("/" + inc_path) or partial_path.endswith(inc_path):
                    if partial_path not in seen_files:
                        seen_files[partial_path] = True
                        plans.append({
                            "plan_type": "restore_file",
                            "priority": -10,  # High priority - restore header before trying other fixes
                            "target_file": partial_path,
                            "action": "restore_full",
                            "params": {"ref": git_state["ref"]},
                            "reason": "Restore partial header " + partial_path + " (included by " + file_path + ", defines missing types)",
                        })

    return plans
