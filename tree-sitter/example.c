
// This is a simple example demonstrating tree-sitter's basic API
// Note: This requires a language grammar to parse actual code
// For a working example, you need to link against a grammar like tree-sitter-json

#include <stdio.h>
#include <string.h>


char* foo()
{
return "hello world";
};

int bar()
{
  return 0;
};

int main() {
    printf("example\n");

    return 0;
}
