#!/usr/bin/env python3
import json
import sys

def find_function_declarators(node, parent_def=None):
    """Recursively find function_declarator nodes and their parent function_definition"""
    results = []

    node_type = node.get('type')

    # Track if this is a function_definition
    if node_type == 'function_definition':
        parent_def = node

    # If we found a function_declarator, extract the identifier
    if node_type == 'function_declarator' and parent_def:
        # Find the identifier child
        for child in node.get('children', []):
            if child.get('type') == 'identifier':
                func_name = child.get('text', '')
                start_line = parent_def['start']['row'] + 1  # Convert to 1-indexed
                end_line = parent_def['end']['row'] + 1      # Convert to 1-indexed
                results.append((func_name, start_line, end_line))
                break

    # Recursively process children
    for child in node.get('children', []):
        results.extend(find_function_declarators(child, parent_def))

    return results

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <json-file>", file=sys.stderr)
        print(f"Example: ./tree_print --json example.c > ast.json && {sys.argv[0]} ast.json", file=sys.stderr)
        sys.exit(1)

    json_file = sys.argv[1]

    if json_file != "-":
        with open(json_file, 'r') as f:
            ast = json.load(f)
    else:
        ast = json.load(sys.stdin)


    functions = find_function_declarators(ast)

    for func_name, start_line, end_line in functions:
        print(f"{func_name}:{start_line},{end_line}")

if __name__ == '__main__':
    main()
