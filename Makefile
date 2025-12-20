# Toolchains
GCC   ?= gcc
CLANG ?= clang

# Common
STD    = -std=c99
WARN   = -Wall -Wextra -Wpedantic -Werror=implicit-function-declaration \
         -Wuninitialized -Wmaybe-uninitialized \
         -Werror=uninitialized -Werror=maybe-uninitialized
CPPFLAGS = -D_POSIX_C_SOURCE=200809L
# Keep frames for better reports
FRAME = -fno-omit-frame-pointer

# Debug build that CAN warn on uninitialized (avoid -O0)
CFLAGS_DEBUG   = -Og -g $(STD) $(WARN) $(FRAME)
LDFLAGS_DEBUG  =

# Release
CFLAGS_RELEASE = -O2 $(STD) -Wall -Wextra -Wpedantic

# Sanitizers (ASan/UBSan)
SAN    = -fsanitize=address,undefined
CFLAGS_ASAN  = $(CFLAGS_DEBUG) $(SAN)
LDFLAGS_ASAN = $(SAN)

# Clang MemorySanitizer (detects uninitialized reads) — Linux x86_64 only
MSAN = -fsanitize=memory -fsanitize-memory-track-origins=2
CFLAGS_MSAN  = -O1 -g $(STD) -Wall -Wextra -Wpedantic $(FRAME) $(MSAN)
LDFLAGS_MSAN = $(MSAN)

# Targets
.PHONY: all clean analyze asan msan test

all: dim color_test

test: dim test_dim.py testty.py
	./testty.py --run python3 --input "hello = 1[enter]"
	python3 test_dim.py

TS_SRC := $(wildcard tree-sitter/lib/src/*.c)
TS_SRC := $(filter-out tree-sitter/lib/src/lib.c,$(TS_SRC))

dim: dim.c
	$(GCC) $(CPPFLAGS) $(CFLAGS_DEBUG) -o $@ $< \
		$(TS_SRC) \
		tree-sitter/grammars/c/src/parser.c \
		tree-sitter/grammars/python/src/parser.c \
		tree-sitter/grammars/python/src/scanner.c \
		-I tree-sitter/lib/include \
		-I tree-sitter/lib/src \
		-I tree-sitter/grammars/python/src \
		-D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE \
		-Wno-pedantic -Wno-unused-result -Wno-unused-value \
		$(LDFLAGS_DEBUG)

asan: dim.c
	$(GCC) $(CPPFLAGS) $(CFLAGS_ASAN) -o dim $< $(LDFLAGS_ASAN)

# MSan requires Clang and that ALL deps (including libs) are built with MSan.
msan: dim.c
	$(CLANG) $(CPPFLAGS) $(CFLAGS_MSAN) -o dim $< $(LDFLAGS_MSAN)

color_test: color_test.c
	$(GCC) $(CPPFLAGS) $(CFLAGS_RELEASE) -o $@ $<

clean:
	rm -f dim color_test

format: dim.c
	clang-format dim.c -i

