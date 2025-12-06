# tree_print - Tree-Sitter Query Tool

A minimal command-line tool for querying and extracting code patterns from C source files using tree-sitter.

## Files

- `tree_print.c` - Main program source code
- `test_tree_print.py` - Comprehensive test suite (18 tests)
- `TREE_PRINT_USAGE.md` - Detailed usage documentation
- `example.c` - Sample C file used for testing

## Quick Start

### Build

```bash
make  # Build libtree-sitter.a
gcc -o tree_print tree_print.c test/fixtures/grammars/c/src/parser.c \
    -I lib/include -L . -l:libtree-sitter.a
```

### Usage

```bash
./tree_print <filename> <query>
```

### Example

```bash
./tree_print example.c "(string_literal) @str"
```

Output:
```
"Tree-sitter minimal API example\n"
"================================\n\n"
"Failed to create parser\n"
...
```

## Testing

Run the test suite:

```bash
python3 test_tree_print.py
```

The test suite includes:
- **12 functional tests**: String literals, function definitions, function calls, comments, if statements, declarations, pointer types, specific identifiers, return statements, type identifiers, printf calls, call expressions with arguments
- **3 additional tests**: Preprocessor includes, number literals, nested queries
- **1 edge case**: Query without capture (valid but no output)
- **2 error cases**: Invalid query syntax, non-existent file

## Test Coverage

The test suite validates:

1. **Basic queries**: Simple node type matching
2. **Field queries**: Matching with field constraints
3. **Predicate queries**: Using `#eq?` predicates
4. **Nested queries**: Complex parent-child relationships
5. **Error handling**: Invalid queries and missing files
6. **Edge cases**: Queries without captures

## Example Queries

### Find all string literals
```bash
./tree_print example.c "(string_literal) @str"
```

### Find function call names
```bash
./tree_print example.c "(call_expression function: (identifier) @name)"
```

### Find specific functions
```bash
./tree_print example.c '(identifier) @id (#eq? @id "printf")'
```

### Find if statements
```bash
./tree_print example.c "(if_statement) @if"
```

### Find comments
```bash
./tree_print example.c "(comment) @c"
```

## Implementation Details

The tool:
1. Reads the source file into memory
2. Creates a tree-sitter parser configured for C
3. Parses the source into an AST
4. Compiles the user-provided query pattern
5. Executes the query against the AST
6. Prints the source text for each captured node

## Features

- ✅ Supports full tree-sitter query syntax
- ✅ Field-based matching
- ✅ Predicate support (`#eq?`, etc.)
- ✅ Nested queries
- ✅ Multiple captures per query
- ✅ Error reporting with detailed messages
- ✅ Comprehensive test suite

## Limitations

- Currently only supports C files (uses tree-sitter-c grammar)
- Query must include at least one capture for output
- Requires the C grammar from test/fixtures/grammars/c

## Extending to Other Languages

To support other languages:

1. Change the language function declaration
2. Link against that language's parser
3. Update `ts_parser_set_language()` and `ts_query_new()` calls

See TREE_PRINT_USAGE.md for detailed examples.
