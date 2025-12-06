#!/bin/bash

# Script to run make test with environment diagnostics
# Output will be saved to test_output.log

OUTPUT_FILE="test_output.log"

echo "==================================================================" | tee "$OUTPUT_FILE"
echo "Tree-Sitter Test Run with Environment Diagnostics" | tee -a "$OUTPUT_FILE"
echo "==================================================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Timestamp: $(date)" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== System Information ===" | tee -a "$OUTPUT_FILE"
uname -a | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if command -v lsb_release &> /dev/null; then
    echo "OS Release:" | tee -a "$OUTPUT_FILE"
    lsb_release -a 2>&1 | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

echo "=== Rust Environment ===" | tee -a "$OUTPUT_FILE"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
source $HOME/.cargo/env

echo "Rust version:" | tee -a "$OUTPUT_FILE"
rustc --version 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Cargo version:" | tee -a "$OUTPUT_FILE"
cargo --version 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Node version:" | tee -a "$OUTPUT_FILE"
node --version 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== Environment Variables ===" | tee -a "$OUTPUT_FILE"
echo "SHELL: $SHELL" | tee -a "$OUTPUT_FILE"
echo "TERM: $TERM" | tee -a "$OUTPUT_FILE"
echo "LANG: $LANG" | tee -a "$OUTPUT_FILE"
echo "LC_ALL: $LC_ALL" | tee -a "$OUTPUT_FILE"
echo "LC_CTYPE: $LC_CTYPE" | tee -a "$OUTPUT_FILE"
echo "TZ: $TZ" | tee -a "$OUTPUT_FILE"
echo "PWD: $PWD" | tee -a "$OUTPUT_FILE"
echo "USER: $USER" | tee -a "$OUTPUT_FILE"
echo "HOME: $HOME" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== Terminal Information ===" | tee -a "$OUTPUT_FILE"
if tty -s; then
    echo "Running in TTY: $(tty)" | tee -a "$OUTPUT_FILE"
else
    echo "Not running in a TTY" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

echo "=== C/C++ Toolchain ===" | tee -a "$OUTPUT_FILE"
echo "GCC version:" | tee -a "$OUTPUT_FILE"
gcc --version 2>&1 | head -n 1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Clang version:" | tee -a "$OUTPUT_FILE"
clang --version 2>&1 | head -n 1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "libclang location:" | tee -a "$OUTPUT_FILE"
dpkg -L libclang-dev 2>&1 | grep "libclang.so" | head -n 3 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== Git Repository State ===" | tee -a "$OUTPUT_FILE"
echo "Current branch:" | tee -a "$OUTPUT_FILE"
git branch --show-current 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Git status:" | tee -a "$OUTPUT_FILE"
git status --short 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Last commit:" | tee -a "$OUTPUT_FILE"
git log -1 --oneline 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== File System Information ===" | tee -a "$OUTPUT_FILE"
df -T . 2>&1 | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "=== Fixture Grammars Status ===" | tee -a "$OUTPUT_FILE"
if [ -d "test/fixtures/grammars" ]; then
    echo "Grammar fixtures present:" | tee -a "$OUTPUT_FILE"
    ls -1 test/fixtures/grammars/ 2>&1 | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
else
    echo "No fixture grammars directory found" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

echo "=== Cargo/Rust Cache Information ===" | tee -a "$OUTPUT_FILE"
echo "Cargo home: $CARGO_HOME" | tee -a "$OUTPUT_FILE"
if [ -d "$HOME/.cargo" ]; then
    du -sh "$HOME/.cargo" 2>&1 | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

if [ -d "target" ]; then
    echo "Target directory size:" | tee -a "$OUTPUT_FILE"
    du -sh target 2>&1 | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

echo "==================================================================" | tee -a "$OUTPUT_FILE"
echo "Starting make test..." | tee -a "$OUTPUT_FILE"
echo "==================================================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Run make test and capture both stdout and stderr
# Also capture the exit code
set -o pipefail
make test 2>&1 | tee -a "$OUTPUT_FILE"
TEST_EXIT_CODE=$?

echo "" | tee -a "$OUTPUT_FILE"
echo "==================================================================" | tee -a "$OUTPUT_FILE"
echo "Test run completed" | tee -a "$OUTPUT_FILE"
echo "Exit code: $TEST_EXIT_CODE" | tee -a "$OUTPUT_FILE"
echo "==================================================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Count test results if possible
if grep -q "test result:" "$OUTPUT_FILE"; then
    echo "=== Test Summary ===" | tee -a "$OUTPUT_FILE"
    grep "test result:" "$OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

# Look for failures
if grep -q "failures:" "$OUTPUT_FILE"; then
    echo "=== Failed Tests ===" | tee -a "$OUTPUT_FILE"
    sed -n '/^failures:/,/^test result:/p' "$OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

echo "Complete output saved to: $OUTPUT_FILE"
echo "You can view it with: cat $OUTPUT_FILE"
echo "Or grep for failures: grep -A 20 'failures:' $OUTPUT_FILE"

exit $TEST_EXIT_CODE
