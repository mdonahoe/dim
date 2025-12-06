# tree_print - Query-based Source Code Printer

A minimal command-line tool that uses tree-sitter to parse C files and print parts of the code that match a tree-sitter query.

## Building

```bash
make              # Build libtree-sitter.a
gcc -o tree_print tree_print.c test/fixtures/grammars/c/src/parser.c -I lib/include -L . -l:libtree-sitter.a
```

## Usage

```bash
./tree_print <filename> <query>
```

The query must include at least one capture (using `@name` syntax).

## Examples

### Find all string literals

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

### Find all function definitions

```bash
./tree_print example.c "(function_definition) @func"
```

Output:
```
int main() {
    printf("Tree-sitter minimal API example\n");
    ...
    return 0;
}
```

### Find all function call names

```bash
./tree_print example.c "(call_expression function: (identifier) @name)"
```

Output:
```
printf
printf
ts_parser_new
fprintf
...
```

### Find all comments

```bash
./tree_print example.c "(comment) @c"
```

### Find all if statements

```bash
./tree_print example.c "(if_statement) @if"
```

### Find variable declarations

```bash
./tree_print example.c "(declaration) @decl"
```

### Find pointer types

```bash
./tree_print example.c "(pointer_declarator) @ptr"
```

## Query Syntax

Tree-sitter queries use S-expression syntax:

- `(node_type)` - Match a node type
- `(node_type) @capture` - Match and capture
- `(parent (child) @c)` - Match parent containing child
- `(node field: (type) @c)` - Match with field constraint
- `(node_type "literal")` - Match literal text

## Node Types for C

Common C node types you can query:

- `function_definition` - Function definitions
- `function_declarator` - Function declarators
- `call_expression` - Function calls
- `identifier` - Variable/function names
- `string_literal` - String literals
- `number_literal` - Numeric literals
- `comment` - Comments
- `if_statement` - If statements
- `for_statement` - For loops
- `while_statement` - While loops
- `declaration` - Variable declarations
- `struct_specifier` - Struct definitions
- `pointer_declarator` - Pointer types
- `type_identifier` - Type names

To see all available node types, check the tree-sitter-c grammar documentation.

## How It Works

1. Reads the source file
2. Creates a tree-sitter parser with the C grammar
3. Parses the source code into a syntax tree
4. Compiles the query pattern
5. Executes the query against the syntax tree
6. Prints the source text for each captured node

## Limitations

- Currently only supports C files (uses tree-sitter-c grammar)
- Must include at least one capture in the query
- Requires the C grammar from test/fixtures/grammars/c

## Extending to Other Languages

To support other languages, modify the code:

1. Include the language header: `TSLanguage *tree_sitter_LANG(void);`
2. Link against the language's parser.c
3. Change `ts_parser_set_language(parser, tree_sitter_LANG())`
4. Update `ts_query_new()` to use `tree_sitter_LANG()`

Example for JavaScript:
```bash
gcc -o tree_print_js tree_print.c \
    test/fixtures/grammars/javascript/src/parser.c \
    test/fixtures/grammars/javascript/src/scanner.c \
    -I lib/include -L . -l:libtree-sitter.a
```
