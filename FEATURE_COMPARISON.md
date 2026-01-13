# Dim vs Neovim Feature Comparison

This document compares the editor features implemented in **Dim** (a minimal vim-like editor written in C) with their corresponding implementations in **Neovim**.

## Overview

| Aspect | Dim | Neovim |
|--------|-----|--------|
| Language | C (~2000 LOC) | C with Lua integration (~500K+ LOC) |
| Architecture | Single-file monolithic | Modular with plugin system |
| Dependencies | tree-sitter only | libuv, tree-sitter, luajit, msgpack, etc. |
| Extensibility | None (compile-time only) | Lua scripting, RPC API, plugins |

---

## Feature Comparison by Category

### 1. Modal Editing System

#### Dim Implementation
- **Three modes**: Normal, Insert, Visual (defined as constants `DIM_NORMAL_MODE`, `DIM_INSERT_MODE`, `DIM_VISUAL_MODE`)
- **Mode state**: Single integer in `editorConfig.mode`
- **Mode transitions**: Direct assignment (e.g., `E.mode = DIM_INSERT_MODE`)
- **Key handling**: Single `switch` statement dispatches based on current mode
- **Source location**: `dim.c:114` (`E.mode` field), key handling in `editorProcessKeypress()`

```c
// Dim's mode constants
#define DIM_NORMAL_MODE 1
#define DIM_INSERT_MODE 2
#define DIM_VISUAL_MODE 3
```

#### Neovim Implementation
- **Seven+ modes**: Normal, Insert, Visual, Select, Command-line, Ex, Terminal, Operator-pending
- **Mode state**: Global `State` variable with bitfield flags
- **Mode transitions**: Complex state machine with `ModeChanged` autocmd events
- **Key handling**: Static command table `nv_cmds[]` generated at build time maps keys to handler functions
- **Source files**: `src/nvim/normal.c`, `src/nvim/edit.c`, `src/nvim/state.c`

**Key Differences:**
- Neovim's mode system is far more complex, supporting sub-modes and mode-specific mappings
- Neovim fires events on mode changes, allowing plugins to react
- Dim's implementation is ~50 lines; Neovim's spans thousands

---

### 2. Text Storage & Buffer Management

#### Dim Implementation
- **Data structure**: Dynamic array of `erow` (editor row) structs
- **Line storage**: Each `erow` contains `char *chars` (raw) and `char *render` (display)
- **Buffer count**: Single buffer only
- **Memory model**: Full rows reallocated on each edit

```c
typedef struct erow {
  int idx;
  int size;
  int rsize;
  char *chars;      // Raw character data
  char *render;     // Rendered for display (tabs expanded)
  unsigned char *hl; // Syntax highlighting
  int hl_open_comment;
} erow;
```

#### Neovim Implementation
- **Data structure**: `memline_T` using block-based B-tree storage
- **Line storage**: Lines packed into data blocks with index tables
- **Buffer count**: Unlimited buffers (`buf_T` double-linked list)
- **Memory model**: Copy-on-write with scratch buffer for multiple small edits
- **Source files**: `src/nvim/memline.c`, `src/nvim/buffer.c`

**Key Differences:**
| Aspect | Dim | Neovim |
|--------|-----|--------|
| Multi-buffer | No | Yes |
| Large file handling | O(n) operations | O(log n) with B-tree |
| Memory efficiency | Low (full row copies) | High (block packing) |
| Swap file support | No | Yes |

---

### 3. Undo System

#### Dim Implementation
- **Architecture**: Linear stack of full-state snapshots
- **Storage**: Array of `undoState` structs containing complete row copies
- **Granularity**: One undo state per operation
- **Operations**: `u` only (no redo)

```c
typedef struct undoState {
  erow *row;      // Complete copy of all rows
  int numrows;
  int cx;         // Cursor position
  int cy;
} undoState;
```

#### Neovim Implementation
- **Architecture**: Tree-based undo with branching
- **Storage**: `u_header` nodes forming undo tree
- **Granularity**: Configurable (per-keystroke to per-operation)
- **Operations**: `u`, `Ctrl-R`, `g-`, `g+`, `:earlier`, `:later`
- **Features**: Time-based navigation, persistent undo across sessions
- **Source file**: `src/nvim/undo.c`

**Key Differences:**
| Aspect | Dim | Neovim |
|--------|-----|--------|
| Redo support | No | Yes |
| Undo branches | No | Yes (tree structure) |
| Persistent undo | No | Yes (`undofile` option) |
| Time-based undo | No | Yes (`:earlier 5m`) |
| Memory usage | High (full snapshots) | Low (delta-based) |

---

### 4. Search System

#### Dim Implementation
- **Entry**: `/` opens prompt, `*` searches word under cursor
- **Navigation**: `n` (next), `N` (previous)
- **Algorithm**: Linear scan through all rows with `strstr()`
- **Highlighting**: `HL_MATCH` color applied to matches
- **State**: `searchString`, `searchIndex`, `searchDirection` in config

#### Neovim Implementation
- **Entry**: `/`, `?`, `*`, `#`, `g*`, `g#`
- **Navigation**: `n`, `N`, `gn`, `gN`
- **Algorithm**: Compiled regex patterns via `search_regcomp()`
- **Highlighting**: `hlsearch` option with `:nohlsearch` toggle
- **Features**: Regex support, case options (`ignorecase`, `smartcase`), `incsearch`
- **Source file**: `src/nvim/search.c`

**Key Differences:**
| Aspect | Dim | Neovim |
|--------|-----|--------|
| Regex support | No (literal only) | Full regex |
| Incremental search | No | Yes (`incsearch`) |
| Case options | No | `ignorecase`, `smartcase` |
| Search history | No | Yes (accessible via arrows) |
| Very magic modes | No | Yes (`\v`, `\V`, etc.) |

---

### 5. Syntax Highlighting

#### Dim Implementation
- **Primary**: Tree-sitter integration via C API
- **Fallback**: Regex-based keyword matching
- **Languages**: C/C++ and Python (compile-time)
- **Reparse**: Throttled to 1-second intervals
- **Colors**: 8 highlight types mapped to ANSI colors

```c
enum editorHighlight {
  HL_NORMAL = 0,
  HL_COMMENT,
  HL_MLCOMMENT,
  HL_KEYWORD1,
  HL_KEYWORD2,
  HL_STRING,
  HL_NUMBER,
  HL_MATCH
};
```

#### Neovim Implementation
- **Primary**: Tree-sitter with query-based captures
- **Fallback**: Regex-based syntax files (legacy Vim syntax)
- **Languages**: 100+ via nvim-treesitter plugin
- **Reparse**: Incremental parsing on every change
- **Features**: Language injection, semantic highlighting
- **Source**: Lua runtime + `src/nvim/treesitter.c`

**Key Differences:**
| Aspect | Dim | Neovim |
|--------|-----|--------|
| Language count | 2 | 100+ |
| Query system | No | Yes (`.scm` files) |
| Incremental parse | Throttled | True incremental |
| Language injection | No | Yes (embedded languages) |
| Custom highlights | Compile-time | Runtime configurable |

---

### 6. Navigation Commands

#### Dim Implementation
| Command | Implementation |
|---------|---------------|
| `hjkl` | Direct cursor adjustment |
| `w` | Loop scanning for word boundary |
| `0`, `$` | Set `cx` to 0 or line length |
| `gg`, `G` | Set `cy` to 0 or `numrows-1` |
| `f{char}`, `t{char}` | Linear scan on current line |
| `%` | Bracket matching with nesting counter |
| Number prefix | `repeatCount` accumulator |

#### Neovim Implementation
| Command | Implementation |
|---------|---------------|
| `hjkl` | Motion functions in `cursor.c` |
| `w`, `W`, `b`, `B`, `e`, `E` | Word motion functions with class detection |
| `0`, `$`, `^`, `g_` | Line motion handlers |
| `gg`, `G`, `{count}G` | File position motions |
| `f`, `F`, `t`, `T`, `;`, `,` | Character search with repeat |
| `%` | `findmatch()` with configurable pairs |
| Operator-motion | `oparg_T` structure for composability |

**Key Differences:**
- Neovim supports operator-motion composition (`d3w`, `c$`, `y%`)
- Neovim has text objects (`iw`, `a"`, `i{`, etc.)
- Dim has basic motions; Neovim has ~50+ motion commands

---

### 7. File Operations

#### Dim Implementation
- **Commands**: `:w`, `:e`, `:q`, `:wq`
- **Tab completion**: Custom `findFileCompletion()` for `:e`
- **Unsaved changes**: Counter requiring 3 quit attempts

#### Neovim Implementation
- **Commands**: `:w`, `:e`, `:q`, `:wq`, `:wa`, `:qa`, `:saveas`, `:write !cmd`, etc.
- **Tab completion**: Full command-line completion engine
- **Features**: Auto-commands, file type detection, encoding handling

---

### 8. Visual Mode & Clipboard

#### Dim Implementation
- **Selection**: `v_start` and `v_end` mark points
- **Operations**: `y` (yank), `d`/`x` (delete)
- **Clipboard**: Internal `char *clipboard` buffer
- **Line mode**: No (character selection only)

#### Neovim Implementation
- **Selection**: Visual, Visual-Line, Visual-Block modes
- **Operations**: All operators work with visual selection
- **Clipboard**: Multiple registers (`"a`-`"z`, `"+`, `"*`, etc.)
- **System clipboard**: Via `clipboard` option

---

### 9. Terminal Handling

#### Dim Implementation
- **Mode**: Raw mode via `termios`
- **Output**: Direct ANSI escape sequences
- **Input**: Blocking `read()` with timeout
- **Resize**: `TIOCGWINSZ` ioctl

#### Neovim Implementation
- **Mode**: libuv-based terminal abstraction
- **Output**: TUI module with terminal capability detection
- **Input**: Async event loop
- **Features**: True color, mouse support, terminal emulator (`:terminal`)

---

## Summary Table

| Feature | Dim | Neovim |
|---------|-----|--------|
| Lines of Code | ~2,000 | ~500,000+ |
| Modes | 3 | 7+ |
| Multiple Buffers | No | Yes |
| Undo Tree | No (linear stack) | Yes |
| Redo | No | Yes |
| Regex Search | No | Yes |
| Text Objects | No | Yes |
| Operator-Motion | Partial | Full |
| Plugins | No | Lua/Vimscript |
| LSP Support | No | Built-in |
| Tree-sitter | Basic | Advanced |
| Async I/O | No | Yes |
| Remote API | No | Yes (RPC) |
| Mouse Support | No | Yes |
| True Color | No | Yes |

---

## Architectural Philosophy

### Dim
Dim follows the philosophy of being a **minimal, dependency-light vim-like editor**. It prioritizes:
- Single C file compilation
- Fast startup
- Basic vim keybindings
- No runtime configuration

### Neovim
Neovim follows the philosophy of being an **extensible, modern text editor platform**. It prioritizes:
- Plugin ecosystem
- Language server integration
- Async architecture
- Backwards compatibility with Vim

---

## References

- [Neovim Mode System Documentation](https://deepwiki.com/neovim/neovim/2.5-mode-system-and-text-operations)
- [Neovim Buffer and Window Management](https://deepwiki.com/neovim/neovim/2.3-buffer-and-window-management)
- [Neovim Tree-sitter Documentation](https://neovim.io/doc/user/treesitter.html)
- [Neovim Undo Documentation](https://neovim.io/doc/user/undo.html)
- [Neovim Search Documentation](https://neovim.io/doc/user/pattern.html)
- [nvim-treesitter GitHub](https://github.com/nvim-treesitter/nvim-treesitter)
