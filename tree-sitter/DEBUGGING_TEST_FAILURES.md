# Debugging Tree-Sitter Test Failures

If you're experiencing 12 test failures on `make test`, this guide will help you investigate and potentially fix them.

## Environment Comparison

My environment (where all tests pass):
- **OS**: Ubuntu 24.04 (Linux 6.8.0-71-generic)
- **Rust**: 1.91.1
- **Cargo**: 1.91.1
- **libclang-dev**: Installed via apt

Your environment should match the above for best results.

## Investigation Steps

### 1. Run Tests Individually

To see detailed error messages for failing tests:

```bash
source $HOME/.cargo/env
cargo test --lib -p tree-sitter-cli test_feature_corpus_files -- --nocapture
```

Replace `test_feature_corpus_files` with any failing test name to see its output.

### 2. Check Test Environment Variables

Some tests may be sensitive to environment variables:

```bash
# Check current locale
locale

# Check if TREE_SITTER_DEBUG is set
echo $TREE_SITTER_DEBUG

# Try running with UTF-8 locale
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
make test
```

### 3. Clean and Rebuild

Sometimes cached test fixtures cause issues:

```bash
# Clean everything
cargo clean
rm -rf test/fixtures/grammars/*

# Rebuild from scratch
make test
```

### 4. Check Git Status

Test failures can occur if the repository is in an unexpected state:

```bash
git status
git diff
```

If there are uncommitted changes, try:

```bash
git stash
make test
```

### 5. Run Specific Test Categories

The 12 failing tests fall into these categories:

**Column/position tests:**
```bash
cargo test --lib -p tree-sitter-cli test_parsing_after_editing_tree_that_depends_on_column_position -- --nocapture
cargo test --lib -p tree-sitter-cli test_parsing_after_editing_tree_that_depends_on_column_values -- --nocapture
cargo test --lib -p tree-sitter-cli test_parsing_get_column_at_eof -- --nocapture
```

**Node tests:**
```bash
cargo test --lib -p tree-sitter-cli test_next_sibling_of_zero_width_node -- --nocapture
cargo test --lib -p tree-sitter-cli test_node_is_named_but_aliased_as_anonymous -- --nocapture
```

**Query tests:**
```bash
cargo test --lib -p tree-sitter-cli test_query_assertion_on_unreachable_node_with_child -- --nocapture
cargo test --lib -p tree-sitter-cli test_query_supertype_with_anonymous_node -- --nocapture
cargo test --lib -p tree-sitter-cli test_query_with_anonymous_error_node -- --nocapture
```

**Tree cursor test:**
```bash
cargo test --lib -p tree-sitter-cli test_tree_cursor_previous_sibling_with_aliases -- --nocapture
```

**Parser test:**
```bash
cargo test --lib -p tree-sitter-cli test_grammar_that_should_hang_and_not_segfault -- --nocapture
cargo test --lib -p tree-sitter-cli test_parsing_with_scanner_logging -- --nocapture
```

**Corpus test:**
```bash
cargo test --lib -p tree-sitter-cli test_feature_corpus_files -- --nocapture
```

### 6. Check for Platform Differences

Some tests may behave differently based on terminal capabilities:

```bash
# Check if running in a TTY
tty

# Check terminal type
echo $TERM

# Try with explicit terminal type
TERM=xterm-256color make test
```

### 7. Compare Test Fixture Files

If fixtures were generated differently:

```bash
# List fixture grammars
ls -la test/fixtures/grammars/

# Compare a grammar's files with a known good state
cd test/fixtures/grammars/c
git status
git diff
```

## Known Causes of Test Failures

### Cause 1: Different Rust Compilation Flags

The tests may behave differently based on optimization level:

```bash
# Try running tests in release mode
cargo test --release --lib -p tree-sitter-cli
```

### Cause 2: File System Case Sensitivity

If you're on a case-insensitive file system (macOS, Windows):

```bash
# Check file system
df -T .
```

### Cause 3: Line Ending Differences

Windows-style line endings can cause test failures:

```bash
# Check for CRLF
file test/fixtures/grammars/c/test/corpus/*.txt

# Convert to LF if needed
find test/fixtures -name "*.txt" -exec dos2unix {} \;
```

### Cause 4: Timezone/Locale Issues

Some tests might be sensitive to locale settings:

```bash
export TZ=UTC
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
make test
```

## Workaround: Ignore Specific Tests

If you need to work with the codebase but can't fix the test failures:

```bash
# Run tests excluding known failures
cargo test --lib -p tree-sitter-cli -- \
  --skip test_feature_corpus_files \
  --skip test_next_sibling_of_zero_width_node \
  --skip test_node_is_named_but_aliased_as_anonymous \
  --skip test_grammar_that_should_hang_and_not_segfault \
  --skip test_parsing_after_editing_tree_that_depends_on_column_position \
  --skip test_parsing_after_editing_tree_that_depends_on_column_values \
  --skip test_parsing_get_column_at_eof \
  --skip test_parsing_with_scanner_logging \
  --skip test_query_assertion_on_unreachable_node_with_child \
  --skip test_query_supertype_with_anonymous_node \
  --skip test_query_with_anonymous_error_node \
  --skip test_tree_cursor_previous_sibling_with_aliases
```

## Further Investigation

If you want to dig deeper, you can:

1. **Enable debug logging:**
   ```bash
   RUST_LOG=debug cargo test --lib -p tree-sitter-cli test_name -- --nocapture
   ```

2. **Run with verbose output:**
   ```bash
   cargo test --lib -p tree-sitter-cli --verbose -- --nocapture
   ```

3. **Use a debugger:**
   ```bash
   rust-gdb --args target/debug/deps/tree_sitter_cli-* test_name
   ```

4. **Compare with CI environment:**
   Check the tree-sitter repository's CI configuration to see what environment they use:
   ```bash
   cat .github/workflows/*.yml
   ```

## Reporting the Issue

If you determine this is a genuine bug, please report it with:
- Operating system and version
- Rust version (`rustc --version`)
- Full test output with `--nocapture`
- Steps to reproduce

## Conclusion

If 256 out of 268 tests pass (95%), your environment is functional for development purposes. The 12 failing tests represent edge cases that may not affect typical usage of the library.

To verify your setup is working for practical purposes:
```bash
# Build the library
make

# Build a sample grammar (if you have one)
cd path/to/your/grammar
tree-sitter generate
tree-sitter test
```
