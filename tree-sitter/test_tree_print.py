#!/usr/bin/env python3
"""
Test suite for tree_print tool.
Tests various query patterns against example.c and example.py and validates output.
Supports both C and Python syntax parsing.
"""

import subprocess
import sys
import unittest
import os
from typing import List, Tuple


class TestTreePrint(unittest.TestCase):
    """Test cases for tree_print tool"""

    @classmethod
    def setUpClass(cls):
        """Build tree_print before running tests"""
        res = subprocess.run(["make", "tree_print"], capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write("failed to build tree_print!!!\n")
            sys.stderr.write(res.stderr)
            raise RuntimeError("Failed to build tree_print")

    def setUp(self):
        """Set up test fixtures"""
        self.test_file = "example.c"

    def run_tree_print(self, filename: str, query: str) -> Tuple[str, str, int]:
        """Run tree_print and return (stdout, stderr, returncode)"""
        result = subprocess.run(
            ['./tree_print', filename, query],
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode

    def assert_output_contains(self, query: str, expected: List[str], 
                               should_contain_all: bool = True, 
                               filename: str = None):
        """Helper to test that output contains expected strings"""
        if filename is None:
            filename = self.test_file
        
        stdout, stderr, returncode = self.run_tree_print(filename, query)
        
        self.assertEqual(returncode, 0, 
                        f"tree_print failed with exit code {returncode}\n"
                        f"stdout: {stdout}\nstderr: {stderr}")
        
        matches = [exp in stdout for exp in expected]
        
        if should_contain_all:
            missing = [exp for exp, match in zip(expected, matches) if not match]
            self.assertTrue(all(matches),
                          f"Expected all of {expected} in output, but missing: {missing}\n"
                          f"Got output: {stdout[:500]}")
        else:
            self.assertTrue(any(matches),
                          f"Expected at least one of {expected} in output\n"
                          f"Got output: {stdout[:500]}")

    def assert_output_fails(self, query: str, filename: str = None):
        """Helper to test that a query fails as expected"""
        if filename is None:
            filename = self.test_file
        
        stdout, stderr, returncode = self.run_tree_print(filename, query)
        self.assertNotEqual(returncode, 0,
                          f"Expected query to fail, but it succeeded\n"
                          f"stdout: {stdout}\nstderr: {stderr}")

    def test_string_literals(self):
        """Test finding all string literals"""
        self.assert_output_contains(
            "(string_literal) @str",
            [
                '"example\\n"',
                '"hello world"'
            ]
        )

    def test_function_definitions(self):
        """Test finding function definitions"""
        self.assert_output_contains(
            "(function_definition) @func",
            [
                "int main()",
                "return 0;"
            ]
        )

    def test_function_call_names(self):
        """Test finding function call names"""
        self.assert_output_contains(
            "(call_expression function: (identifier) @name)",
            [
                "printf"
            ]
        )

    def test_comments(self):
        """Test finding comments"""
        self.assert_output_contains(
            "(comment) @c",
            [
                "// This is a simple example"
            ],
            should_contain_all=False
        )

    def test_if_statements(self):
        """Test finding if statements"""
        # example.c doesn't have if statements, so this should find nothing
        # or we can skip it, but let's make it flexible
        stdout, stderr, returncode = self.run_tree_print(self.test_file, "(if_statement) @if")
        # If there are no if statements, the query should still succeed
        self.assertEqual(returncode, 0)

    def test_declarations(self):
        """Test finding declarations"""
        # example.c doesn't have variable declarations, only function definitions
        # So this query should return no matches, which is valid
        stdout, stderr, returncode = self.run_tree_print(self.test_file, "(declaration) @decl")
        self.assertEqual(returncode, 0)
        # It's okay if there are no matches

    def test_pointer_declarators(self):
        """Test finding pointer declarators"""
        # example.c doesn't have pointers, so just check it doesn't crash
        stdout, stderr, returncode = self.run_tree_print(self.test_file, "(pointer_declarator) @ptr")
        self.assertEqual(returncode, 0)

    def test_specific_identifier(self):
        """Test finding identifiers with specific name"""
        # example.c doesn't have "parser", let's test for something that exists
        self.assert_output_contains(
            '(identifier) @id (#eq? @id "main")',
            [
                "main"
            ]
        )

    def test_return_statements(self):
        """Test finding return statements"""
        self.assert_output_contains(
            "(return_statement) @ret",
            [
                "return 0;"
            ]
        )

    def test_type_identifiers(self):
        """Test finding type identifiers"""
        # Use primitive_type instead of type_identifier for built-in types
        self.assert_output_contains(
            "(primitive_type) @type",
            [
                "int"
            ],
            should_contain_all=False
        )

    def test_printf_calls(self):
        """Test finding printf calls specifically"""
        self.assert_output_contains(
            '(call_expression function: (identifier) @fn (#eq? @fn "printf"))',
            [
                "printf"
            ]
        )

    def test_call_expressions_with_arguments(self):
        """Test finding call expressions with arguments"""
        self.assert_output_contains(
            "(call_expression arguments: (argument_list) @args)",
            [
                '("example\\n")'
            ],
            should_contain_all=False
        )

    def test_preprocessor_includes(self):
        """Test finding preprocessor includes"""
        self.assert_output_contains(
            "(preproc_include) @inc",
            [
                "#include <stdio.h>"
            ]
        )

    def test_number_literals(self):
        """Test finding number literals"""
        self.assert_output_contains(
            "(number_literal) @num",
            [
                "0"
            ]
        )

    def test_nested_query(self):
        """Test complex nested query"""
        # example.c doesn't have if with return, so let's test function with return
        self.assert_output_contains(
            "(function_definition body: (compound_statement (return_statement) @ret))",
            [
                "return 0;"
            ],
            should_contain_all=False
        )

    def test_query_without_capture(self):
        """Test query without capture (valid but produces no output)"""
        stdout, stderr, returncode = self.run_tree_print(self.test_file, "(string_literal)")
        self.assertEqual(returncode, 0)
        # Should either have no matches or indicate no matches
        # The behavior depends on tree_print implementation

    def test_invalid_query_syntax(self):
        """Test invalid query syntax"""
        self.assert_output_fails("(invalid_node_type) @x")

    def test_nonexistent_file(self):
        """Test non-existent file"""
        self.assert_output_fails("(string_literal) @str", "nonexistent.c")

    # Python-specific tests
    def test_python_function_definitions(self):
        """Test finding Python function definitions"""
        self.assert_output_contains(
            "(function_definition) @func",
            [
                "def hello()"
            ],
            filename="example.py"
        )

    def test_python_strings(self):
        """Test finding Python string literals"""
        self.assert_output_contains(
            "(string) @str",
            [
                '"Hello, world!"',
                '"__main__"'
            ],
            filename="example.py"
        )

    def test_python_function_calls(self):
        """Test finding Python function calls"""
        self.assert_output_contains(
            "(call) @call",
            [
                "print(",
                "hello()"
            ],
            filename="example.py"
        )

    def test_python_if_statements(self):
        """Test finding Python if statements"""
        self.assert_output_contains(
            "(if_statement) @if",
            [
                "if __name__"
            ],
            filename="example.py"
        )

    def test_python_return_statements(self):
        """Test finding Python return statements"""
        self.assert_output_contains(
            "(return_statement) @ret",
            [
                "return 42"
            ],
            filename="example.py"
        )

    def test_python_identifiers(self):
        """Test finding Python identifiers"""
        self.assert_output_contains(
            '(identifier) @id (#eq? @id "hello")',
            [
                "hello"
            ],
            filename="example.py"
        )

    def test_python_integer_literals(self):
        """Test finding Python integer literals"""
        self.assert_output_contains(
            "(integer) @int",
            [
                "42"
            ],
            filename="example.py"
        )

    def test_python_comparison_operators(self):
        """Test finding Python comparison operators"""
        self.assert_output_contains(
            "(comparison_operator) @op",
            [
                "=="
            ],
            filename="example.py"
        )

    def test_python_expression_statement(self):
        """Test finding Python expression statements"""
        self.assert_output_contains(
            "(expression_statement) @expr",
            [
                "hello()"
            ],
            filename="example.py"
        )

    def test_python_parameters(self):
        """Test finding Python function parameters"""
        # hello() has no parameters, but the function definition should still be found
        stdout, stderr, returncode = self.run_tree_print("example.py", "(parameters) @params")
        self.assertEqual(returncode, 0)

    def test_python_assignment(self):
        """Test finding Python assignment statements"""
        # example.py doesn't have assignments, but test that query works
        stdout, stderr, returncode = self.run_tree_print("example.py", "(assignment) @assign")
        self.assertEqual(returncode, 0)

    def test_language_detection_c(self):
        """Test that C files are detected and parsed correctly"""
        stdout, stderr, returncode = self.run_tree_print("example.c", "(function_definition) @func")
        self.assertEqual(returncode, 0)
        self.assertIn("int main()", stdout)

    def test_language_detection_python(self):
        """Test that Python files are detected and parsed correctly"""
        stdout, stderr, returncode = self.run_tree_print("example.py", "(function_definition) @func")
        self.assertEqual(returncode, 0)
        self.assertIn("def hello()", stdout)

    def test_python_nested_query(self):
        """Test complex nested query for Python"""
        self.assert_output_contains(
            "(if_statement condition: (comparison_operator) @op)",
            [
                "=="
            ],
            filename="example.py",
            should_contain_all=False
        )

    def test_python_module(self):
        """Test finding Python module structure"""
        stdout, stderr, returncode = self.run_tree_print("example.py", "(module) @mod")
        self.assertEqual(returncode, 0)
        # Module should always exist for a valid Python file
        self.assertTrue(len(stdout) > 0 or "No matches found" in stderr)


if __name__ == "__main__":
    unittest.main()
