#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <tree_sitter/api.h>

// Declare the C language parser
TSLanguage *tree_sitter_c(void);
TSLanguage *tree_sitter_python(void);

// Read file contents into a string
char* read_file(const char* filename) {
    FILE* file = fopen(filename, "r");
    if (!file) {
        fprintf(stderr, "Error: Cannot open file '%s'\n", filename);
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    fseek(file, 0, SEEK_SET);

    char* content = malloc(length + 1);
    if (!content) {
        fclose(file);
        return NULL;
    }

    fread(content, 1, length, file);
    content[length] = '\0';
    fclose(file);

    return content;
}

// Extract text from source code given a node
void print_node_text(const char* source, TSNode node) {
    uint32_t start = ts_node_start_byte(node);
    uint32_t end = ts_node_end_byte(node);

    for (uint32_t i = start; i < end; i++) {
        putchar(source[i]);
    }
    putchar('\n');
}

// Print escaped string for JSON
void print_json_escaped_string(const char* str, uint32_t start, uint32_t end) {
    for (uint32_t i = start; i < end; i++) {
        char c = str[i];
        switch (c) {
            case '"':  printf("\\\""); break;
            case '\\': printf("\\\\"); break;
            case '\b': printf("\\b"); break;
            case '\f': printf("\\f"); break;
            case '\n': printf("\\n"); break;
            case '\r': printf("\\r"); break;
            case '\t': printf("\\t"); break;
            default:
                if ((unsigned char)c < 32) {
                    printf("\\u%04x", c);
                } else {
                    putchar(c);
                }
        }
    }
}

// Recursively print the AST tree structure in JSON format
void print_ast_tree_json(TSNode node, const char* source, int depth, bool is_last) {
    // Print indentation
    for (int i = 0; i < depth; i++) {
        printf("  ");
    }

    printf("{\n");

    // Print node type
    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"type\": \"");
    const char* type = ts_node_type(node);
    for (const char* p = type; *p; p++) {
        switch (*p) {
            case '"':  printf("\\\""); break;
            case '\\': printf("\\\\"); break;
            case '\b': printf("\\b"); break;
            case '\f': printf("\\f"); break;
            case '\n': printf("\\n"); break;
            case '\r': printf("\\r"); break;
            case '\t': printf("\\t"); break;
            default:
                if ((unsigned char)*p < 32) {
                    printf("\\u%04x", *p);
                } else {
                    putchar(*p);
                }
        }
    }
    printf("\",\n");

    // Print position information
    TSPoint start_point = ts_node_start_point(node);
    TSPoint end_point = ts_node_end_point(node);

    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"start\": {\"row\": %u, \"column\": %u},\n",
           start_point.row, start_point.column);

    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"end\": {\"row\": %u, \"column\": %u},\n",
           end_point.row, end_point.column);

    // Print byte range
    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"startByte\": %u,\n", ts_node_start_byte(node));

    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"endByte\": %u,\n", ts_node_end_byte(node));

    // Print named status
    for (int i = 0; i <= depth; i++) printf("  ");
    printf("\"isNamed\": %s,\n", ts_node_is_named(node) ? "true" : "false");

    // Print text content for leaf nodes
    uint32_t child_count = ts_node_child_count(node);
    if (child_count == 0) {
        for (int i = 0; i <= depth; i++) printf("  ");
        printf("\"text\": \"");
        print_json_escaped_string(source, ts_node_start_byte(node), ts_node_end_byte(node));
        printf("\"");
        if (child_count > 0) printf(",");
        printf("\n");
    }

    // Print children
    if (child_count > 0) {
        for (int i = 0; i <= depth; i++) printf("  ");
        printf("\"children\": [\n");

        for (uint32_t i = 0; i < child_count; i++) {
            TSNode child = ts_node_child(node, i);
            print_ast_tree_json(child, source, depth + 1, i == child_count - 1);
        }

        for (int i = 0; i <= depth; i++) printf("  ");
        printf("]\n");
    }

    for (int i = 0; i < depth; i++) printf("  ");
    printf("}");
    if (!is_last) printf(",");
    printf("\n");
}

// Recursively print the AST tree structure
void print_ast_tree(TSNode node, const char* source, int depth) {
    // Print indentation
    for (int i = 0; i < depth; i++) {
        printf("  ");
    }

    // Print node type
    const char* type = ts_node_type(node);
    printf("%s", type);

    // If it's a named node, print its text if it has no children
    uint32_t child_count = ts_node_child_count(node);
    if (ts_node_is_named(node) && child_count == 0) {
        printf(": \"");
        uint32_t start = ts_node_start_byte(node);
        uint32_t end = ts_node_end_byte(node);
        for (uint32_t i = start; i < end; i++) {
            char c = source[i];
            if (c == '\n') {
                printf("\\n");
            } else if (c == '\t') {
                printf("\\t");
            } else if (c == '"') {
                printf("\\\"");
            } else {
                putchar(c);
            }
        }
        printf("\"");
    }

    printf("\n");

    // Recursively print children
    for (uint32_t i = 0; i < child_count; i++) {
        TSNode child = ts_node_child(node, i);
        print_ast_tree(child, source, depth + 1);
    }
}

int main(int argc, char** argv) {
    if (argc < 2 || argc > 4) {
        fprintf(stderr, "Usage: %s [--json] <filename> [query]\n", argv[0]);
        fprintf(stderr, "Example: %s example.c \"(string_literal)\"\n", argv[0]);
        fprintf(stderr, "         %s example.c  (prints entire AST)\n", argv[0]);
        fprintf(stderr, "         %s --json example.c  (prints AST in JSON format)\n", argv[0]);
        return 1;
    }

    bool json_output = false;
    int file_arg_index = 1;

    // Check for --json flag
    if (argc >= 3 && strcmp(argv[1], "--json") == 0) {
        json_output = true;
        file_arg_index = 2;
    }

    const char* filename = argv[file_arg_index];
    const char* query_string = NULL;

    // Determine if there's a query string
    if (json_output && argc == 4) {
        query_string = argv[3];
    } else if (!json_output && argc == 3) {
        query_string = argv[2];
    }

    // Read source file
    char* source_code = read_file(filename);
    if (!source_code) {
        return 1;
    }

    // Determine language based on file extension
    TSLanguage* language = NULL;
    const char* ext = strrchr(filename, '.');
    if (ext) {
        if (strcmp(ext, ".c") == 0 || strcmp(ext, ".h") == 0) {
            language = tree_sitter_c();
        } else if (strcmp(ext, ".py") == 0) {
            language = tree_sitter_python();
        }
    }
    
    // Default to C if no extension or unknown extension
    if (!language) {
        language = tree_sitter_c();
    }

    // Create parser
    TSParser* parser = ts_parser_new();
    if (!parser) {
        fprintf(stderr, "Error: Failed to create parser\n");
        free(source_code);
        return 1;
    }

    // Set language
    if (!ts_parser_set_language(parser, language)) {
        fprintf(stderr, "Error: Failed to set language\n");
        ts_parser_delete(parser);
        free(source_code);
        return 1;
    }

    // Parse the source code
    TSTree* tree = ts_parser_parse_string(parser, NULL, source_code, strlen(source_code));
    if (!tree) {
        fprintf(stderr, "Error: Failed to parse source code\n");
        ts_parser_delete(parser);
        free(source_code);
        return 1;
    }

    TSNode root_node = ts_tree_root_node(tree);

    // If no query provided, print the entire AST
    if (!query_string) {
        if (json_output) {
            print_ast_tree_json(root_node, source_code, 0, true);
        } else {
            print_ast_tree(root_node, source_code, 0);
        }
    } else {
        // Create query
        uint32_t error_offset;
        TSQueryError error_type;
        TSQuery* query = ts_query_new(
            language,
            query_string,
            strlen(query_string),
            &error_offset,
            &error_type
        );

        if (!query) {
            fprintf(stderr, "Error: Failed to create query\n");
            fprintf(stderr, "Query error at offset %u: ", error_offset);
            switch (error_type) {
                case TSQueryErrorSyntax:
                    fprintf(stderr, "Syntax error\n");
                    break;
                case TSQueryErrorNodeType:
                    fprintf(stderr, "Invalid node type\n");
                    break;
                case TSQueryErrorField:
                    fprintf(stderr, "Invalid field\n");
                    break;
                case TSQueryErrorCapture:
                    fprintf(stderr, "Invalid capture\n");
                    break;
                default:
                    fprintf(stderr, "Unknown error\n");
                    break;
            }
            ts_tree_delete(tree);
            ts_parser_delete(parser);
            free(source_code);
            return 1;
        }

        // Execute query
        TSQueryCursor* cursor = ts_query_cursor_new();
        ts_query_cursor_exec(cursor, query, root_node);

        // Iterate through matches
        TSQueryMatch match;
        int match_count = 0;

        while (ts_query_cursor_next_match(cursor, &match)) {
            for (uint16_t i = 0; i < match.capture_count; i++) {
                TSQueryCapture capture = match.captures[i];
                print_node_text(source_code, capture.node);
                match_count++;
            }
        }

        if (match_count == 0) {
            fprintf(stderr, "No matches found\n");
        }

        // Cleanup
        ts_query_cursor_delete(cursor);
        ts_query_delete(query);
    }
    ts_tree_delete(tree);
    ts_parser_delete(parser);
    free(source_code);

    return 0;
}
