# How to Get `make test` Working in tree-sitter

This document describes the steps needed to successfully run `make test` in the tree-sitter repository.

## Prerequisites

The tree-sitter test suite requires:
1. **Rust toolchain** (cargo, rustc)
2. **C development headers** (for building native dependencies)
3. **Node.js** (for loading JavaScript grammar files in tests)

## Installation Steps

### 1. Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

Verify installation:
```bash
cargo --version
```

### 2. Install C Development Dependencies

The build process requires `libclang-dev` for generating Rust bindings to C libraries:

```bash
apt-get update
apt-get install -y libclang-dev
```

This installs:
- `libclang-dev` - Clang development libraries
- `libclang-common-18-dev` - Common development files
- `libclang-rt-18-dev` - Compiler runtime library
- Other required dependencies

**Note:** On Debian/Ubuntu systems, `build-essential` is usually already installed. If not:
```bash
apt-get install -y build-essential
```

### 3. Install Node.js

Some tests require Node.js to load JavaScript grammar files. Install using nvm (recommended):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install --lts
```

Or using NodeSource repository:

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs
```

Verify installation:
```bash
node --version
```

### 4. Run the Tests

```bash
make test
```

## What `make test` Does

The `make test` command runs the following steps:

1. **Fetch fixtures** (`cargo xtask fetch-fixtures`)
   - Clones grammar repositories (bash, c, cpp, go, html, java, javascript, json, php, python, ruby, rust, typescript)

2. **Generate fixtures** (`cargo xtask generate-fixtures`)
   - Regenerates parser files for all grammar fixtures

3. **Run tests** (`cargo xtask test`)
   - Compiles all Rust crates
   - Runs 268 tests in the CLI crate
   - Runs 59 tests in the generate crate
   - Runs various other test suites
   - All tests should pass (exit code 0)

## Test Results

Expected output:
- **329+ tests total** across all crates
- Most tests should pass
- Execution time: ~30-60 seconds (after initial compilation)

**Expected result with all prerequisites installed:**
```
test result: ok. 268 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

**If you're missing Node.js, you'll see 12 test failures:**
```
test result: FAILED. 256 passed; 12 failed; 0 ignored; 0 measured; 0 filtered out
```

These 12 failing tests all show the error:
```
Failed to run `node` -- No such file or directory (os error 2)
```

## Troubleshooting

### Problem: 12 tests failing with "No such file or directory (os error 2)"

**Failing tests:**
```
tests::corpus_test::test_feature_corpus_files
tests::node_test::test_next_sibling_of_zero_width_node
tests::node_test::test_node_is_named_but_aliased_as_anonymous
tests::parser_test::test_grammar_that_should_hang_and_not_segfault
tests::parser_test::test_parsing_after_editing_tree_that_depends_on_column_position
tests::parser_test::test_parsing_after_editing_tree_that_depends_on_column_values
tests::parser_test::test_parsing_get_column_at_eof
tests::parser_test::test_parsing_with_scanner_logging
tests::query_test::test_query_assertion_on_unreachable_node_with_child
tests::query_test::test_query_supertype_with_anonymous_node
tests::query_test::test_query_with_anonymous_error_node
tests::tree_test::test_tree_cursor_previous_sibling_with_aliases
```

**Error message:**
```
Failed to run `node` -- No such file or directory (os error 2)
```

**Cause:** Node.js is not installed.

**Solution:** Install Node.js (see step 3 above). These tests need to load JavaScript grammar files.

### Problem: `stdbool.h` file not found

**Error:**
```
fatal error: 'stdbool.h' file not found
```

**Solution:**
Install `libclang-dev`:
```bash
apt-get install -y libclang-dev
```

### Problem: Rust not found

**Error:**
```
cargo: command not found
```

**Solution:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

### Problem: First build takes a long time

This is expected. The initial build compiles:
- All Rust dependencies (~200+ crates)
- Grammar parsers for 15+ languages
- Test fixtures

Subsequent builds will be much faster due to caching.

## System Information

Tested on:
- **OS:** Ubuntu 24.04 (Linux 6.8.0)
- **Rust:** 1.91.1
- **Tree-sitter:** v0.26.0

## Quick Start (All Commands)

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env

# Install C dependencies
apt-get update
apt-get install -y libclang-dev

# Install Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install --lts

# Run tests
cd /path/to/tree-sitter
make test
```

## Exit Code

- **0** = All tests passed ✓ (expected with Rust + libclang-dev + Node.js)
- **1** = Test failures but build successful (12 failures = missing Node.js)
- **2+** = Build errors or missing dependencies

## Summary

To get all 268 tests passing in the tree-sitter codebase, you need:

1. ✓ Rust toolchain (rustc, cargo)
2. ✓ C development headers (libclang-dev)
3. ✓ Node.js (to load JavaScript grammar files)

**Without Node.js:** 256 tests pass, 12 fail (95% success rate)
**With all prerequisites:** All 268 tests pass (100% success rate)

## Debugging Test Failures

If you want to investigate why tests are failing on your system, see the companion guide: [DEBUGGING_TEST_FAILURES.md](DEBUGGING_TEST_FAILURES.md)

This guide covers:
- Running individual tests with detailed output
- Environment variable checks
- Platform-specific issues
- Workarounds for known failures
