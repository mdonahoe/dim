/*** includes ***/

#define _BSD_SOURCE
#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <termios.h>
#include <time.h>
#include <sys/time.h>
#include <dirent.h>
#include <tree_sitter/api.h>
#include <unistd.h>

TSLanguage *tree_sitter_c(void);
TSLanguage *tree_sitter_python(void);

/*** defines ***/

#define DIM_VERSION "0.0.1"
#define DIM_TAB_STOP 4
#define DIM_QUIT_TIMES 3
#define CTRL_KEY(k) ((k) & 0x1f)
#define DIM_NORMAL_MODE 1
#define DIM_INSERT_MODE 2
#define DIM_VISUAL_MODE 3

enum editorKey {
  BACKSPACE = 127,
  ARROW_LEFT = 1000,
  ARROW_RIGHT,
  ARROW_UP,
  ARROW_DOWN,
  HOME_KEY,
  END_KEY,
  PAGE_UP,
  PAGE_DOWN,
  DEL_KEY
};

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

#define HL_HIGHLIGHT_NUMBERS (1 << 0)
#define HL_HIGHLIGHT_STRINGS (1 << 1)

/*** data ***/

struct editorSyntax {
  char *filetype;
  char **filematch;
  char **keywords;
  char *singleline_comment_start;
  char *multiline_comment_start;
  char *multiline_comment_end;
  int flags;
  TSLanguage *(*ts_language)(void);
};

typedef struct erow {
  int idx;
  int size;
  int rsize;
  char *chars;
  char *render;
  unsigned char *hl;
  int hl_open_comment;
} erow;

typedef struct markpt {
  int x;
  int y;
} markpt;

typedef struct undoState {
  erow *row;
  int numrows;
  int cx;
  int cy;
} undoState;

struct editorConfig {
  int cx, cy;
  int rx;
  int rowoff;
  int coloff;
  int screenrows;
  int screencols;
  int numrows;
  erow *row;
  int dirty;
  char *filename;
  char statusmsg[80];
  time_t statusmsg_time;
  struct editorSyntax *syntax;
  struct termios orig_termios;
  TSParser *ts_parser;
  TSTree *ts_tree;
  int mode;
  int prevNormalKey;
  int repeatCount;  // For number prefix (e.g., 3j, 5x)
  char *searchString;
  int searchIndex;
  int searchDirection;
  markpt v_start;
  markpt v_end;
  char *clipboard;
  int clipboard_len;
  time_t last_ts_parse;
  undoState *undo_stack;
  int undo_stack_size;
  int undo_stack_capacity;
  char pendingInsertKey;  // For jj escape detection
  long pendingInsertTimeMs;  // Timestamp in milliseconds for jj timing
};

struct editorConfig E;

/*** filetypes ***/

char *C_HL_extensions[] = {".c", ".h", ".cpp", NULL};
char *C_HL_keywords[] = {
    "switch",   "if",    "while",     "for",     "break",   "continue",
    "return",   "else",  "struct",    "union",   "typedef", "static",
    "enum",     "class", "case",      "int|",    "long|",   "double|",
    "float|",   "char|", "unsigned|", "signed|", "void|",   "#define",
    "#include", NULL};

char *PY_HL_extensions[] = {".py", NULL};
char *PY_HL_keywords[] = {
    "and",    "as",         "assert", "async",      "await",    "break",
    "class",  "continue",   "def",    "del",        "elif",     "else",
    "except", "finally",    "for",    "from",       "global",   "if",
    "import", "in",         "is",     "lambda",     "nonlocal", "not",
    "or",     "pass",       "raise",  "return",     "try",      "while",
    "with",   "yield",      "True",   "False",      "None",     "int|",
    "float|", "str|",       "bool|",  "list|",      "dict|",    "tuple|",
    "set|",   "frozenset|", "bytes|", "bytearray|", "range|",   "object|",
    "type|",  "len|",       "print|", "input|",     "open|",    NULL};

struct editorSyntax HLDB[] = {
    {"c",                                         // lang
     C_HL_extensions,                             // filetypes
     C_HL_keywords,                               // keywords
     "//",                                        // line comment start sequence
     "/*",                                        // multi-line start
     "*/",                                        // multi-line end
     HL_HIGHLIGHT_NUMBERS | HL_HIGHLIGHT_STRINGS, // flags
     tree_sitter_c},                              // tree-sitter language
    {"python",                                    // lang
     PY_HL_extensions,                            // filetypes
     PY_HL_keywords,                              // keywords
     "#",                                         // line comment start sequence
     "\"\"\"", // multi-line start (Python doesn't have traditional multi-line
               // comments)
     "\"\"\"", // multi-line end
     HL_HIGHLIGHT_NUMBERS | HL_HIGHLIGHT_STRINGS, // flags
     tree_sitter_python},                         // tree-sitter language
};

#define HLDB_ENTRIES (sizeof(HLDB) / sizeof(HLDB[0]))

/*** prototypes ***/

void editorReparseTreeSitter(void);
void editorSetStatusMessage(const char *fmt, ...);
void editorRefreshScreen(void);
char *editorPrompt(char *prompt, void (*callback)(char *, int));
char *editorRowsToString(int *buflen);
void editorRowDelSpan(erow *row, int start, int end);
void editorPushUndoState(void);
void editorUndo(void);
char *findFileCompletion(const char *prefix);
char *editorPromptWithFileCompletion(char *prompt);

/*** terminal ***/

long getCurrentTimeMs(void) {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return (long)(tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

void clearScreen(void) {
  (void)write(STDOUT_FILENO, "\x1b[2J", 4);
  (void)write(STDOUT_FILENO, "\x1b[H", 3);
}

void die(const char *s) {
  clearScreen();
  perror(s);
  exit(1);
}

void disableRawMode(void) {
  if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &E.orig_termios) == -1)
    die("tcsetattr");
}

void enableRawMode(void) {
  if (tcgetattr(STDIN_FILENO, &E.orig_termios) == -1)
    die("tcgetattr");
  atexit(disableRawMode);
  struct termios raw = E.orig_termios;
  raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
  raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
  raw.c_oflag &= ~(OPOST);
  raw.c_cflag |= ~(CS8);
  raw.c_cc[VMIN] = 0;
  raw.c_cc[VTIME] = 1;
  if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == -1)
    die("tcsetattr");
}

int editorReadKey(void) {
  int nread;
  char c;
  while ((nread = read(STDIN_FILENO, &c, 1)) != 1) {
    if (nread == -1 && errno != EAGAIN)
      die("read");
  }
  if (c == '\x1b') {
    char seq[3];
    if (read(STDIN_FILENO, &seq[0], 1) != 1)
      return '\x1b';
    if (read(STDIN_FILENO, &seq[1], 1) != 1)
      return '\x1b';

    if (seq[0] == '[') {
      if (seq[1] >= '0' && seq[1] <= '9') {
        if (read(STDIN_FILENO, &seq[2], 1) != 1)
          return '\x1b';
        if (seq[2] == '~') {
          switch (seq[1]) {
          case '1':
            return HOME_KEY;
          case '2':
            return END_KEY;
          case '3':
            return DEL_KEY;
          case '5':
            return PAGE_UP;
          case '6':
            return PAGE_DOWN;
          }
        }
      } else {
        switch (seq[1]) {
        case 'A':
          return ARROW_UP;
        case 'B':
          return ARROW_DOWN;
        case 'C':
          return ARROW_RIGHT;
        case 'D':
          return ARROW_LEFT;
        case 'H':
          return HOME_KEY;
        case 'F':
          return END_KEY;
        }
      }
    } else if (seq[0] == 'O') {
      switch (seq[1]) {
      case 'H':
        return HOME_KEY;
      case 'F':
        return END_KEY;
      }
    }
    return '\x1b';
  }
  return c;
}

int getCursorPosition(int *rows, int *cols) {
  char buf[32];
  unsigned int i = 0;
  *rows = *cols;
  if (write(STDOUT_FILENO, "\x1b[6n", 4) != 4)
    return -1;
  while (i < sizeof(buf) - 1) {
    if (read(STDIN_FILENO, &buf[i], 1) != 1)
      break;
    if (buf[i] == 'R')
      break;
    i++;
  }
  buf[i] = '\0';
  printf("\r\n&buf[1]: '%s'\r\n", &buf[1]);
  if (buf[0] != '\x1b' || buf[1] != '[')
    return -1;
  if (sscanf(&buf[2], "%d;%d", rows, cols) != 2)
    return -1;
  return 0;
}

int getWindowSize(int *rows, int *cols) {
  struct winsize ws;
  if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == -1 || ws.ws_col == 0) {
    if (write(STDOUT_FILENO, "\x1b[999C\x1b[999B", 12) != 12)
      return -1;
    return getCursorPosition(rows, cols);
  } else {
    *cols = ws.ws_col;
    *rows = ws.ws_row;
    return 0;
  }
}

/*** syntax highlighting ***/

int is_separator(int c) {
  return isspace(c) || c == '\0' || strchr(",.()+-/*=~%<>[];", c) != NULL;
}

static void ts_highlight_node(erow *row, TSNode n, int start_col, int end_col) {
  const char *type = ts_node_type(n);
  int hl_type = HL_NORMAL;

  // Map node types to highlight types
  if (strcmp(type, "comment") == 0) {
    hl_type = HL_COMMENT;
  } else if (strcmp(type, "string_start") == 0 ||
             strcmp(type, "string_end") == 0) {
    // For Python, check if it's a triple-quoted string (docstring)
    // Triple quotes should be cyan (comment color), single quotes should be
    // magenta (string color)
    int len = end_col - start_col;
    if (len >= 3) {
      // Triple-quoted string delimiter
      hl_type = HL_COMMENT;
    } else {
      // Single or double quote
      hl_type = HL_STRING;
    }
  } else if (strcmp(type, "string_literal") == 0 ||
             strcmp(type, "string") == 0 ||
             strcmp(type, "string_content") == 0) {
    hl_type = HL_STRING;
  } else if (strcmp(type, "number_literal") == 0 ||
             strcmp(type, "integer") == 0 || strcmp(type, "float") == 0) {
    hl_type = HL_NUMBER;
  } else if (strcmp(type, "primitive_type") == 0 ||
             strcmp(type, "type_identifier") == 0 ||
             strcmp(type, "sized_type_specifier") == 0 ||
             strcmp(type, "type_qualifier") == 0) {
    hl_type = HL_KEYWORD2;
  } else if (strcmp(type, "if") == 0 || strcmp(type, "else") == 0 ||
             strcmp(type, "while") == 0 || strcmp(type, "for") == 0 ||
             strcmp(type, "return") == 0 || strcmp(type, "break") == 0 ||
             strcmp(type, "continue") == 0 || strcmp(type, "switch") == 0 ||
             strcmp(type, "case") == 0 || strcmp(type, "def") == 0 ||
             strcmp(type, "class") == 0 || strcmp(type, "import") == 0 ||
             strcmp(type, "from") == 0 || strcmp(type, "struct") == 0 ||
             strcmp(type, "union") == 0 || strcmp(type, "enum") == 0 ||
             strcmp(type, "typedef") == 0 || strcmp(type, "static") == 0 ||
             strcmp(type, "extern") == 0 || strcmp(type, "const") == 0 ||
             strcmp(type, "volatile") == 0 || strcmp(type, "#include") == 0 ||
             strcmp(type, "#define") == 0 || strcmp(type, "#ifdef") == 0 ||
             strcmp(type, "#ifndef") == 0 || strcmp(type, "#endif") == 0) {
    hl_type = HL_KEYWORD1;
  }

  // Apply highlighting to the range
  if (hl_type != HL_NORMAL) {
    for (int i = start_col; i < end_col && i < row->rsize; i++) {
      row->hl[i] = hl_type;
    }
  }
}

static void ts_traverse_node(erow *row, TSNode n) {
  TSPoint start = ts_node_start_point(n);
  TSPoint end = ts_node_end_point(n);

  // Check if node intersects with current row
  if ((start.row <= (uint32_t)row->idx && end.row >= (uint32_t)row->idx)) {
    int start_col = (start.row == (uint32_t)row->idx) ? (int)start.column : 0;
    int end_col =
        (end.row == (uint32_t)row->idx) ? (int)end.column : row->rsize;

    uint32_t child_count = ts_node_child_count(n);
    if (child_count == 0) {
      // Leaf node - apply highlighting
      ts_highlight_node(row, n, start_col, end_col);
    } else {
      // Non-leaf - check if it's a named node type we want to highlight
      if (ts_node_is_named(n)) {
        const char *type = ts_node_type(n);
        if (strcmp(type, "comment") == 0 ||
            strcmp(type, "string_literal") == 0 ||
            strcmp(type, "string") == 0) {
          // Highlight the entire node even if it has children
          ts_highlight_node(row, n, start_col, end_col);
        }
      }

      // Recurse into children
      for (uint32_t i = 0; i < child_count; i++) {
        TSNode child = ts_node_child(n, i);
        ts_traverse_node(row, child);
      }
    }
  }
}

int editorUpdateSyntaxTreeSitter(erow *row) {
  row->hl = realloc(row->hl, row->rsize);
  memset(row->hl, HL_NORMAL, row->rsize);

  if (E.syntax == NULL || E.syntax->ts_language == NULL || E.ts_tree == NULL)
    return -1;

  TSNode root_node = ts_tree_root_node(E.ts_tree);

  // Create a point for the start of this row
  TSPoint start_point = {.row = row->idx, .column = 0};
  TSPoint end_point = {.row = row->idx, .column = row->rsize};

  // Find nodes that intersect with this row
  TSNode node =
      ts_node_descendant_for_point_range(root_node, start_point, end_point);

  ts_traverse_node(row, node);

  return 0;
}

int editorUpdateSyntax(erow *row) {
  row->hl = realloc(row->hl, row->rsize);
  memset(row->hl, HL_NORMAL, row->rsize);
  if (E.syntax == NULL)
    return -1;

  char **keywords = E.syntax->keywords;

  char *scs = E.syntax->singleline_comment_start;
  int scs_len = scs ? strlen(scs) : 0;

  char *mcs = E.syntax->multiline_comment_start;
  int mcs_len = mcs ? strlen(mcs) : 0;

  char *mce = E.syntax->multiline_comment_end;
  int mce_len = mce ? strlen(mce) : 0;

  int prev_sep = 1;
  int in_string = 0;
  int in_comment = (row->idx > 0 && E.row[row->idx - 1].hl_open_comment);

  int i = 0;
  int hl_count = 0;
  while (i < row->rsize) {
    hl_count++;
    char c = row->render[i];
    unsigned char prev_hl = (i > 0) ? row->hl[i - 1] : HL_NORMAL;

    if (scs_len && !in_string && !in_comment) {
      if (!strncmp(&row->render[i], scs, scs_len)) {
        memset(&row->hl[i], HL_COMMENT, row->rsize - i);
        break;
      }
    }

    // if multi-line comments are defined and we arent in a string...
    if (mcs_len && mce_len && !in_string) {
      // if we are already in comment, check for the ending.
      if (in_comment) {
        row->hl[i] = HL_COMMENT;
        if (!strncmp(&row->render[i], mce, mce_len)) {
          memset(&row->hl[i], HL_MLCOMMENT, mce_len);
          i += mce_len;
          in_comment = 0;
          prev_sep = 1;
          continue;
        } else {
          i++;
          continue;
        }
      } else if (!strncmp(&row->render[i], mcs, mcs_len)) {
        // look for the start of the multi-line
        memset(&row->hl[i], HL_COMMENT, mcs_len);
        i += mcs_len;
        in_comment = 1;
        continue;
      }
    }

    if (E.syntax->flags & HL_HIGHLIGHT_STRINGS) {
      if (in_string) {
        row->hl[i] = HL_STRING;
        hl_count++;
        if (c == '\\' && i + 1 < row->rsize) {
          row->hl[i + 1] = HL_STRING;
          i += 2;
          continue;
        }
        if (c == in_string)
          in_string = 0;
        i++;
        prev_sep = 1;
        continue;
      } else {
        if (c == '"' || c == '\'') {
          in_string = c;
          hl_count++;
          row->hl[i] = HL_STRING;
          i++;
          continue;
        }
      }
    }
    if (E.syntax->flags & HL_HIGHLIGHT_NUMBERS) {
      if ((isdigit(c) && (prev_sep || prev_hl == HL_NUMBER)) ||
          (c == '.' && prev_hl == HL_NUMBER)) {
        row->hl[i] = HL_NUMBER;
        hl_count++;
        i++;
        prev_sep = 0;
        continue;
      }
    }

    if (prev_sep) {
      int j;
      for (j = 0; keywords[j]; j++) {
        int klen = strlen(keywords[j]);
        int kw2 = keywords[j][klen - 1] == '|';
        if (kw2)
          klen--;
        if (!strncmp(&row->render[i], keywords[j], klen) &&
            is_separator(row->render[i + klen])) {
          memset(&row->hl[i], kw2 ? HL_KEYWORD2 : HL_KEYWORD1, klen);
          i += klen;
          break;
        }
      }
      if (keywords[j] != NULL) {
        prev_sep = 0;
        continue;
      }
    }

    prev_sep = is_separator(c);
    i++;
  }

  int changed = (row->hl_open_comment != in_comment);
  row->hl_open_comment = in_comment;
  if (changed && row->idx + 1 < E.numrows)
    editorUpdateSyntax(&E.row[row->idx + 1]);
  return hl_count;
}

int editorSyntaxToColor(int hl) {
  switch (hl) {
  case HL_COMMENT:
  case HL_MLCOMMENT:
    return 36; // cyan
  case HL_KEYWORD1:
    return 33; // yellow
  case HL_KEYWORD2:
    return 32; // green
  case HL_STRING:
    return 35; // magenta
  case HL_NUMBER:
    return 31; // ANSI "foreground red"
  case HL_MATCH:
    return 34; // ANSI blue
  default:
    return 37; // ANSI "foreground white"
  }
}

void editorReparseTreeSitterThrottled() {
  time_t now = time(NULL);
  if (now - E.last_ts_parse >= 1) {
    editorReparseTreeSitter();
    E.last_ts_parse = now;
  }
}

void editorReparseTreeSitter() {
  if (E.syntax == NULL || E.syntax->ts_language == NULL)
    return;

  // Build source string from all rows
  int buflen;
  char *source = editorRowsToString(&buflen);
  if (!source)
    return;

  // Create parser if needed
  if (E.ts_parser == NULL) {
    E.ts_parser = ts_parser_new();
    if (!E.ts_parser) {
      free(source);
      return;
    }
    ts_parser_set_language(E.ts_parser, E.syntax->ts_language());
  }

  // Delete old tree and parse new one
  if (E.ts_tree) {
    ts_tree_delete(E.ts_tree);
  }
  E.ts_tree = ts_parser_parse_string(E.ts_parser, NULL, source, buflen);

  free(source);

  // Re-highlight all rows
  for (int i = 0; i < E.numrows; i++) {
    editorUpdateSyntaxTreeSitter(&E.row[i]);
  }
}

void editorSelectSyntaxHighlight() {
  E.syntax = NULL;
  if (E.filename == NULL)
    return;

  char *ext = strrchr(E.filename, '.');

  for (unsigned int j = 0; j < HLDB_ENTRIES; j++) {
    struct editorSyntax *s = &HLDB[j];
    unsigned int i = 0;
    while (s->filematch[i]) {
      int is_ext = (s->filematch[i][0] == '.');
      if ((is_ext && ext && !strcmp(ext, s->filematch[i])) ||
          (!is_ext && strstr(E.filename, s->filematch[i]))) {
        E.syntax = s;

        // If tree-sitter is available, use it
        if (E.syntax->ts_language) {
          editorReparseTreeSitter();
          editorSetStatusMessage("Tree-sitter highlighting enabled for %s",
                                 s->filetype);
        } else {
          // Fall back to regex highlighting
          int filerow;
          int hl_counts = 0;
          int lines = 0;
          for (filerow = 0; filerow < E.numrows; filerow++) {
            int hl_count = editorUpdateSyntax(&E.row[filerow]);
            hl_counts += hl_count;
            lines++;
          }
          editorSetStatusMessage("hl_counts = %d, lines = %d", hl_counts,
                                 lines);
        }
        return;
      }
      i++;
    }
  }
}

/*** row operations ***/

int editorRowCxToRx(erow *row, int cx) {
  int rx = 0;
  int j;
  for (j = 0; j < cx; j++) {
    if (row->chars[j] == '\t')
      rx += (DIM_TAB_STOP - 1) - (rx % DIM_TAB_STOP);
    rx++;
  }
  return rx;
}

int editorRowRxToCx(erow *row, int rx) {
  int cur_rx = 0;
  int cx;
  for (cx = 0; cx < row->size; cx++) {
    if (row->chars[cx] == '\t')
      cur_rx += (DIM_TAB_STOP - 1) - (cur_rx % DIM_TAB_STOP);
    if (cur_rx > rx)
      return cx;
  }
  return cx;
}

void editorUpdateRow(erow *row) {
  int tabs = 0;
  int j;
  for (j = 0; j < row->size; j++)
    if (row->chars[j] == '\t')
      tabs++;

  free(row->render);
  row->render = malloc(row->size + tabs * (DIM_TAB_STOP - 1) + 1);

  int idx = 0;
  for (j = 0; j < row->size; j++) {
    if (row->chars[j] == '\t') {
      row->render[idx++] = ' ';
      while (idx % DIM_TAB_STOP != 0)
        row->render[idx++] = ' ';
    } else {
      row->render[idx++] = row->chars[j];
    }
  }
  row->render[idx] = '\0';
  row->rsize = idx;

  // Use tree-sitter highlighting if available, fall back to regex
  if (E.syntax && E.syntax->ts_language && E.ts_tree) {
    editorUpdateSyntaxTreeSitter(row);
  } else {
    editorUpdateSyntax(row);
  }
}

void editorInsertRow(int at, char *s, size_t len) {
  if (at < 0 || at > E.numrows)
    return;

  E.row = realloc(E.row, sizeof(erow) * (E.numrows + 1));
  memmove(&E.row[at + 1], &E.row[at], sizeof(erow) * (E.numrows - at));
  for (int j = at + 1; j <= E.numrows; j++)
    E.row[j].idx++;

  E.row[at].idx = at;

  E.row[at].size = len;
  E.row[at].chars = malloc(len + 1);
  memcpy(E.row[at].chars, s, len);
  E.row[at].chars[len] = '\0';

  E.row[at].rsize = 0;
  E.row[at].render = NULL;
  E.row[at].hl = NULL;
  E.row[at].hl_open_comment = 0;
  editorUpdateRow(&E.row[at]);

  E.numrows++;
  E.dirty++;
}

void editorFreeRow(erow *row) {
  free(row->render);
  free(row->chars);
  free(row->hl);
}

void editorDelRow(int at) {
  if (at < 0 || at >= E.numrows)
    return;
  editorFreeRow(&E.row[at]);
  memmove(&E.row[at], &E.row[at + 1], sizeof(erow) * (E.numrows - at - 1));
  for (int j = at; j < E.numrows - 1; j++)
    E.row[j].idx--;
  E.numrows--;
  E.dirty++;
}

void editorDelRows(int start, int end) {
  int i = start;
  while (i < end) {
    editorDelRow(start);
    i++;
  }
}

void editorDelSpan(markpt a, markpt b) {
  int start_y;
  int start_x;
  int end_y;
  int end_x;
  if (a.y < b.y) {
    start_y = a.y;
    start_x = a.x;
    end_y = b.y;
    end_x = b.x;
  } else if (a.y > b.y) {
    start_y = b.y;
    start_x = b.x;
    end_y = a.y;
    end_x = a.x;
  } else {
    start_y = a.y;
    end_y = b.y;
    if (a.x < b.x) {
      start_x = a.x;
      end_x = b.x;
    } else {
      start_x = b.x;
      end_x = a.x;
    }
  }
  if (start_y < end_y) {
    erow *row = &E.row[end_y];
    if (end_x < row->size - 1) {
      editorRowDelSpan(row, 0, end_x + 1);
    } else {
      editorDelRow(end_y);
    }
    editorDelRows(start_y + 1, end_y);
    row = &E.row[start_y];
    if (start_x > 0) {
      editorRowDelSpan(row, start_x, row->size);
    } else {
      editorDelRow(start_y);
    }
  } else {
    erow *row = &E.row[start_y];
    if (start_x == 0 && end_x == row->size - 1) {
      editorDelRow(end_x);
    } else {
      editorRowDelSpan(row, start_x, end_x + 1);
    }
  }
  E.cx = start_x;
  E.cy = start_y;
}

void editorRowInsertChar(erow *row, int at, int c) {
  if (at < 0 || at > row->size)
    at = row->size;
  row->chars = realloc(row->chars, row->size + 2);
  memmove(&row->chars[at + 1], &row->chars[at], row->size - at + 1);
  row->size++;
  row->chars[at] = c;
  editorUpdateRow(row);
  E.dirty++;
  if (E.syntax && E.syntax->ts_language) {
    editorReparseTreeSitterThrottled();
  }
}

void editorRowAppendString(erow *row, char *s, size_t len) {
  row->chars = realloc(row->chars, row->size + len + 1);
  memcpy(&row->chars[row->size], s, len);
  row->size += len;
  row->chars[row->size] = '\0';
  editorUpdateRow(row);
  E.dirty++;
  if (E.syntax && E.syntax->ts_language) {
    editorReparseTreeSitterThrottled();
  }
}

void editorRowDelChar(erow *row, int at) {
  if (at < 0 || at >= row->size)
    return;
  memmove(&row->chars[at], &row->chars[at + 1], row->size - at);
  row->size--;
  editorUpdateRow(row);
  E.dirty++;
  if (E.syntax && E.syntax->ts_language) {
    editorReparseTreeSitterThrottled();
  }
}

void editorRowDelSpan(erow *row, int start, int end) {
  if (start >= end || start < 0 || end > row->size) {
    return;
  }
  memmove(&row->chars[start], &row->chars[end], row->size - end);
  row->size = row->size - end + start;
  editorUpdateRow(row);
  E.dirty++;
  if (E.syntax && E.syntax->ts_language) {
    editorReparseTreeSitter();
  }
}

/*** editor operations ***/

void editorInsertChar(int c) {
  if (E.cy == E.numrows) {
    editorInsertRow(E.numrows, "", 0);
  }
  editorRowInsertChar(&E.row[E.cy], E.cx, c);
  E.cx++;
}

enum { CLASS_WHITESPACE, CLASS_PUNCTUATION, CLASS_WORD };

int get_char_class(int c) {
  if (isspace(c) || c == '\0')
    return CLASS_WHITESPACE;
  if (isalnum(c) || c == '_')
    return CLASS_WORD;
  return CLASS_PUNCTUATION;
}

int getStartOfWord(int x, erow *row) {
  if (x <= 0)
    return 0; // Already at start of line

  int start_class = get_char_class(row->chars[x]);

  // 1. Move before characters of the same class
  while (x > 0 && get_char_class(row->chars[x]) == start_class) {
    x--;
  }
  return x;
}

int getEndOfWord(int x, erow *row) {
  if (x >= row->size)
    return x; // Already at end of line

  int start_class = get_char_class(row->chars[x]);

  // 1. Move past characters of the same class
  while (x < row->size && get_char_class(row->chars[x]) == start_class) {
    x++;
  }
  return x;
}

void editorDelSurroundingWord() {
  erow *row = &E.row[E.cy];
  int start = getStartOfWord(E.cx, row);
  int end = getEndOfWord(E.cx, row);
  editorRowDelSpan(row, start, end);
  E.cx = start;
}

void editorDelToEndOfWord() {
  erow *row = &E.row[E.cy];
  int end = getEndOfWord(E.cx, row);
  editorRowDelSpan(row, E.cx, end);
}

void editorMoveWordForward() {
  erow *row = &E.row[E.cy];

  E.cx = getEndOfWord(E.cx, row);

  // 2. If we landed on whitespace, skip it to find the start of the next word
  if (E.cx < row->size &&
      get_char_class(row->chars[E.cx]) == CLASS_WHITESPACE) {
    while (E.cx < row->size &&
           get_char_class(row->chars[E.cx]) == CLASS_WHITESPACE) {
      E.cx++;
    }
  }

  // 3. Optional: If end of line is reached, move to the first char of the next
  // row
  if (E.cx >= row->size && E.cy < E.numrows - 1) {
    E.cy++;
    E.cx = 0;
    // Skip leading whitespace on the next line if desired
    row = &E.row[E.cy];
    while (E.cx < row->size && isspace(row->chars[E.cx]))
      E.cx++;
  }
}

void editorInsertNewLine(void) {
  if (E.cx == 0) {
    editorInsertRow(E.cy, "", 0);
  } else {
    erow *row = &E.row[E.cy];
    editorInsertRow(E.cy + 1, &row->chars[E.cx], row->size - E.cx);
    row = &E.row[E.cy];
    row->size = E.cx;
    row->chars[row->size] = '\0';
    editorUpdateRow(row);
  }
  E.cy++;
  E.cx = 0;
  if (E.syntax && E.syntax->ts_language) {
    editorReparseTreeSitterThrottled();
  }
}

void editorXChar(void) {
  if (E.cy == E.numrows)
    return;
  erow *row = &E.row[E.cy];
  if (E.cx < row->size) {
    editorRowDelChar(row, E.cx);
  } else {
    editorDelRow(E.cy);
  }
}

void editorDelChar(void) {
  if (E.cy == E.numrows)
    return;
  if (E.cx == 0 && E.cy == 0)
    return;
  erow *row = &E.row[E.cy];
  if (E.cx > 0) {
    editorRowDelChar(row, E.cx - 1);
    E.cx--;
  } else {
    E.cx = E.row[E.cy - 1].size;
    editorRowAppendString(&E.row[E.cy - 1], row->chars, row->size);
    editorDelRow(E.cy);
    E.cy--;
  }
}

/*** file i/o ***/

char *editorRowsToString(int *buflen) {
  int totlen = 0;
  int j;
  for (j = 0; j < E.numrows; j++)
    totlen += E.row[j].size + 1;
  *buflen = totlen;

  char *buf = malloc(totlen);
  char *p = buf;
  for (j = 0; j < E.numrows; j++) {
    memcpy(p, E.row[j].chars, E.row[j].size);
    p += E.row[j].size;
    *p = '\n';
    p++;
  }

  return buf;
}

void editorClearBuffer(void) {
  // Free all rows
  for (int i = 0; i < E.numrows; i++) {
    editorFreeRow(&E.row[i]);
  }
  free(E.row);
  E.row = NULL;
  E.numrows = 0;
  E.cx = 0;
  E.cy = 0;
  E.rowoff = 0;
  E.coloff = 0;
  E.dirty = 0;
}

void editorOpenFile(char *filename) {
  // Clear current buffer
  editorClearBuffer();

  // Free old filename and set new one
  free(E.filename);
  E.filename = strdup(filename);

  // Try to open the file
  FILE *fp = fopen(filename, "r");
  if (!fp) {
    editorSetStatusMessage("Can't open file: %s", filename);
    return;
  }

  char *line = NULL;
  size_t linecap = 0;
  ssize_t linelen;
  while ((linelen = getline(&line, &linecap, fp)) != -1) {
    while (linelen > 0 &&
           (line[linelen - 1] == '\n' || line[linelen - 1] == '\r'))
      linelen--;
    editorInsertRow(E.numrows, line, linelen);
  }
  free(line);
  fclose(fp);
  E.dirty = 0;
  editorSelectSyntaxHighlight();
}

void editorOpen(char *filename) {
  free(E.filename);
  E.filename = strdup(filename);
  editorSelectSyntaxHighlight();
  FILE *fp = fopen(filename, "r");
  if (!fp)
    die("fopen");

  char *line = NULL;
  size_t linecap = 0;
  ssize_t linelen;
  while ((linelen = getline(&line, &linecap, fp)) != -1) {
    while (linelen > 0 &&
           (line[linelen - 1] == '\n' || line[linelen - 1] == '\r'))
      linelen--;
    editorInsertRow(E.numrows, line, linelen);
  }
  free(line);
  fclose(fp);
  E.dirty = 0;
  editorSelectSyntaxHighlight();
}

void editorSave(void) {
  if (E.filename == NULL) {
    E.filename = editorPrompt("Save as: %s", NULL);
    if (E.filename == NULL) {
      editorSetStatusMessage("Save aborted!");
      return;
    }
    editorSelectSyntaxHighlight();
  }

  int len;
  char *buf = editorRowsToString(&len);

  int fd = open(E.filename, O_RDWR | O_CREAT, 0644);
  if (fd != -1) {
    if (ftruncate(fd, len) != -1) {
      if (write(fd, buf, len) == len) {
        close(fd);
        free(buf);
        E.dirty = 0;
        editorSetStatusMessage("%d bytes written to disk", len);
        return;
      }
    }
    close(fd);
  }
  free(buf);
  editorSetStatusMessage("Can't save! I/O error: %s", strerror(errno));
}

/*** find ***/
void exModeCallback(char *query, int key) {
  static int foo = -1;
  if (key == '\r' || key == '\x1b') {
    foo = -1;
    return;
  } else if (key == ARROW_UP) {
    // TODO: cycle through previous commands
    foo = 1;
  } else {
  }
}

void editorOpenFile(char *filename);  // Forward declaration

void exMode() {
  char *query = editorPrompt("ex: %s", exModeCallback);

  if (query == NULL) {
    return;
  }

  if (strcmp(query, "q") == 0) {
    clearScreen();
    exit(0);
  } else if (strcmp(query, "w") == 0) {
    editorSave();
  } else if (strcmp(query, "wq") == 0) {
    editorSave();
    clearScreen();
    exit(0);
  } else if (strncmp(query, "e ", 2) == 0) {
    // :e filename - open file
    char *filename = query + 2;
    // Skip leading whitespace
    while (*filename == ' ') filename++;
    if (*filename) {
      editorOpenFile(filename);
    }
  } else if (strcmp(query, "e") == 0) {
    // :e without filename - prompt for file with completion
    free(query);
    char *filename = editorPromptWithFileCompletion("Open file: %s");
    if (filename && *filename) {
      editorOpenFile(filename);
      free(filename);
    }
    return;
  }
  free(query);
}

static inline int is_word_char(int c) { return isalnum(c) || c == '_'; }

char *editorGetWordUnderCursor(void) {
  if (E.cy < 0 || E.cy >= E.numrows)
    return NULL;

  erow *row = &E.row[E.cy];
  if (row->size == 0)
    return NULL;
  if (E.cx < 0 || E.cx >= row->size)
    return NULL;

  if (!is_word_char(row->chars[E.cx]))
    return NULL;

  int start = E.cx;
  int end = E.cx;

  // walk left
  while (start > 0 && is_word_char(row->chars[start - 1])) {
    start--;
  }

  // walk right
  while (end < row->size && is_word_char(row->chars[end])) {
    end++;
  }

  int len = end - start;
  if (len <= 0)
    return NULL;

  char *word = malloc(len + 1);
  memcpy(word, &row->chars[start], len);
  word[len] = '\0';

  return word;
}

void nextSearch() {
  if (E.searchString == NULL) {
    return;
  }
  int current = E.searchIndex;
  int i;
  for (i = 0; i < E.numrows; i++) {
    current += E.searchDirection;
    if (current == -1)
      current = E.numrows - 1;
    else if (current == E.numrows)
      current = 0;

    erow *row = &E.row[current];
    char *match = strstr(row->render, E.searchString);
    if (match) {
      E.searchIndex = current;
      E.cy = current;
      E.cx = editorRowRxToCx(row, match - row->render);
      E.rowoff = E.numrows; // hack to scroll to line!

      // saved_hl_line = current;
      // saved_hl = malloc(row->rsize);
      // memcpy(saved_hl, row->hl, row->rsize);
      // memset(&row->hl[match - row->render], HL_MATCH, strlen(query));
      break;
    }
  }
}

void editorSearchWordUnderCursor(void) {
  char *word = editorGetWordUnderCursor();
  if (!word)
    return;

  free(E.searchString);
  E.searchString = word;

  E.searchIndex = -1;
  E.searchDirection = 1;

  // optionally jump to next match immediately, like vim
  nextSearch();
}

void editorFindCallback(char *query, int key) {
  static int last_match = -1;
  static int direction = 1;
  static int saved_hl_line;
  static char *saved_hl = NULL;

  if (saved_hl) {
    memcpy(E.row[saved_hl_line].hl, saved_hl, E.row[saved_hl_line].rsize);
    free(saved_hl);
    saved_hl = NULL;
  }
  if (key == '\r' || key == '\x1b') {
    last_match = -1;
    direction = 1;
    return;
  } else if (key == ARROW_RIGHT || key == ARROW_DOWN) {
    direction = 1;
  } else if (key == ARROW_LEFT || key == ARROW_UP) {
    direction = -1;
  } else {
    last_match = -1;
    direction = 1;
  }

  if (last_match == -1)
    direction = 1;
  int current = last_match;
  int i;
  for (i = 0; i < E.numrows; i++) {
    current += direction;
    if (current == -1)
      current = E.numrows - 1;
    else if (current == E.numrows)
      current = 0;

    erow *row = &E.row[current];
    char *match = strstr(row->render, query);
    if (match) {
      last_match = current;
      E.cy = current;
      E.cx = editorRowRxToCx(row, match - row->render);
      E.rowoff = E.numrows; // hack to scroll to line!

      saved_hl_line = current;
      saved_hl = malloc(row->rsize);
      memcpy(saved_hl, row->hl, row->rsize);
      memset(&row->hl[match - row->render], HL_MATCH, strlen(query));
      break;
    }
  }
  E.searchIndex = last_match;
  E.searchDirection = direction;
}

/*** undo ***/

void editorFreeRows(erow *rows, int numrows) {
  if (!rows)
    return;
  for (int i = 0; i < numrows; i++) {
    free(rows[i].chars);
    free(rows[i].render);
    free(rows[i].hl);
  }
  free(rows);
}

erow *editorCopyRows(int *out_numrows) {
  if (E.numrows == 0) {
    *out_numrows = 0;
    return NULL;
  }

  erow *copy = malloc(E.numrows * sizeof(erow));
  for (int i = 0; i < E.numrows; i++) {
    copy[i].idx = E.row[i].idx;
    copy[i].size = E.row[i].size;
    copy[i].rsize = E.row[i].rsize;
    copy[i].hl_open_comment = E.row[i].hl_open_comment;

    // Copy chars
    copy[i].chars = malloc(E.row[i].size + 1);
    memcpy(copy[i].chars, E.row[i].chars, E.row[i].size + 1);

    // Copy render
    copy[i].render = malloc(E.row[i].rsize + 1);
    memcpy(copy[i].render, E.row[i].render, E.row[i].rsize + 1);

    // Copy highlight
    copy[i].hl = malloc(E.row[i].rsize);
    memcpy(copy[i].hl, E.row[i].hl, E.row[i].rsize);
  }
  *out_numrows = E.numrows;
  return copy;
}

void editorPushUndoState(void) {
  // Resize stack if needed
  if (E.undo_stack_size >= E.undo_stack_capacity) {
    E.undo_stack_capacity =
        E.undo_stack_capacity == 0 ? 10 : E.undo_stack_capacity * 2;
    E.undo_stack =
        realloc(E.undo_stack, E.undo_stack_capacity * sizeof(undoState));
  }

  undoState *state = &E.undo_stack[E.undo_stack_size];
  state->numrows = 0;
  state->row = editorCopyRows(&state->numrows);
  state->cx = E.cx;
  state->cy = E.cy;

  E.undo_stack_size++;
}

void editorUndo(void) {
  if (E.undo_stack_size == 0) {
    editorSetStatusMessage("Nothing to undo");
    return;
  }

  E.undo_stack_size--;
  undoState *state = &E.undo_stack[E.undo_stack_size];

  // Free current state
  editorFreeRows(E.row, E.numrows);

  // Restore from undo state
  E.row = state->row;
  E.numrows = state->numrows;
  E.cx = state->cx;
  E.cy = state->cy;
  E.dirty = 1;

  // Reparse syntax
  editorReparseTreeSitter();
}

void editorFind() {
  int saved_cx = E.cx;
  int saved_cy = E.cy;
  int saved_coloff = E.coloff;
  int saved_rowoff = E.rowoff;

  char *query =
      editorPrompt("Search: %s (Use ESC/Arrows/Enter)", editorFindCallback);
  if (query) {
    if (E.searchString != NULL) {
      free(E.searchString);
    }
    E.searchString = query;
    // free(query);
  } else {
    E.cx = saved_cx;
    E.cy = saved_cy;
    E.coloff = saved_coloff;
    E.rowoff = saved_rowoff;
  }
}

/*** append buffer ***/

struct abuf {
  char *b;
  int len;
};

void abAppend(struct abuf *ab, const char *s, int len) {
  char *new = realloc(ab->b, ab->len + len);
  if (new == NULL)
    return;
  memcpy(&new[ab->len], s, len);
  ab->b = new;
  ab->len += len;
}

void abFree(struct abuf *ab) { free(ab->b); }

/*** output ***/

void editorScroll(void) {
  E.rx = 0;
  if (E.cy < E.numrows) {
    E.rx = editorRowCxToRx(&E.row[E.cy], E.cx);
  }

  if (E.cy < E.rowoff) {
    E.rowoff = E.cy;
  }
  if (E.cy >= E.rowoff + E.screenrows) {
    E.rowoff = E.cy - E.screenrows + 1;
  }
  if (E.rx < E.coloff) {
    E.coloff = E.rx;
  }
  if (E.rx > E.coloff + E.screencols) {
    E.coloff = E.rx - E.screencols + 1;
  }
}

int isInVisualSelection(int x, int y) {
  if (E.mode != DIM_VISUAL_MODE)
    return 0;

  int start_y = E.v_start.y;
  int end_y = E.v_end.y;
  int start_x = E.v_start.x;
  int end_x = E.v_end.x;

  // Normalize so start is before end
  if (start_y > end_y || (start_y == end_y && start_x > end_x)) {
    int tmp = start_y;
    start_y = end_y;
    end_y = tmp;
    tmp = start_x;
    start_x = end_x;
    end_x = tmp;
  }

  if (y < start_y || y > end_y)
    return 0;
  if (y == start_y && y == end_y)
    return x >= start_x && x <= end_x;
  if (y == start_y)
    return x >= start_x;
  if (y == end_y)
    return x <= end_x;
  return 1;
}

// Returns the length of search match at position x, or 0 if no match
int getSearchMatchLength(int x, int y) {
  if (!E.searchString)
    return 0;
  if (y < 0 || y >= E.numrows)
    return 0;

  erow *row = &E.row[y];
  int search_len = strlen(E.searchString);

  // Check if x position starts a search match
  if (x + search_len <= row->rsize) {
    if (strncmp(&row->render[x], E.searchString, search_len) == 0) {
      return search_len;
    }
  }
  return 0;
}

void editorDrawRows(struct abuf *ab) {
  int y;
  for (y = 0; y < E.screenrows; y++) {
    int filerow = y + E.rowoff;
    if (filerow >= E.numrows) {
      if (E.numrows == 0 && y == E.screenrows / 3) {
        char welcome[80];
        int welcomelen = snprintf(welcome, sizeof(welcome),
                                  "Dim editor -- version %s", DIM_VERSION);
        if (welcomelen > E.screencols)
          welcomelen = E.screencols;
        int padding = (E.screencols - welcomelen) / 2;
        if (padding) {
          abAppend(ab, "~", 1);
          padding--;
        }
        while (padding--)
          abAppend(ab, " ", 1);
        abAppend(ab, welcome, welcomelen);
      } else {
        abAppend(ab, "~", 1);
      }
    } else {
      int len = E.row[filerow].rsize - E.coloff;
      if (len < 0)
        len = 0;
      if (len > E.screencols)
        len = E.screencols;
      char *c = &E.row[filerow].render[E.coloff];
      unsigned char *hl = &E.row[filerow].hl[E.coloff];
      int current_color = -1;
      int in_selection = 0;
      int in_search = 0;
      int search_match_end = 0; // Track when current search match ends
      int j;
      for (j = 0; j < len; j++) {
        int char_x = E.coloff + j;
        int is_selected = isInVisualSelection(char_x, filerow);

        // Determine if this character is in a search match
        int is_search = 0;
        if (char_x < search_match_end) {
          // We're still in the previous match
          is_search = 1;
        } else {
          // Check if a new match starts here
          int match_len = getSearchMatchLength(char_x, filerow);
          if (match_len > 0) {
            is_search = 1;
            search_match_end = char_x + match_len;
          }
        }

        // Search matches take priority over visual selection
        if (is_search && !in_search) {
          abAppend(ab, "\x1b[48;5;226m\x1b[30m",
                   17); // bright yellow background, black text
          in_search = 1;
        } else if (!is_search && in_search) {
          // If we're leaving search, check if we enter selection
          if (is_selected) {
            abAppend(ab, "\x1b[48;5;237m", 11);
            in_selection = 1;
          } else {
            abAppend(ab, "\x1b[49m\x1b[39m",
                     10); // reset background and foreground
          }
          in_search = 0;
          // Restore syntax color if not in selection
          if (!is_selected) {
            current_color = -1;
          }
        } else if (is_selected && !in_selection && !in_search) {
          // Toggle selection background (only if not in search)
          abAppend(ab, "\x1b[48;5;237m", 11); // dark gray background
          in_selection = 1;
        } else if (!is_selected && in_selection && !in_search) {
          abAppend(ab, "\x1b[49m", 5); // reset background
          in_selection = 0;
        }

        if (iscntrl(c[j])) {
          char sym = (c[j] < 26) ? '@' + c[j] : '?';
          abAppend(ab, "\x1b[7m", 4);
          abAppend(ab, &sym, 1);
          abAppend(ab, "\x1b[m", 3);
          if (current_color != -1) {
            char buf[16];
            int clen = snprintf(buf, sizeof(buf), "\x1b[%dm", current_color);
            abAppend(ab, buf, clen);
          }
          if (in_search) {
            abAppend(ab, "\x1b[48;5;226m\x1b[30m", 17);
          } else if (in_selection) {
            abAppend(ab, "\x1b[48;5;237m", 11);
          }
        } else if (in_search) {
          // In search match: ignore syntax coloring, just output character
          abAppend(ab, &c[j], 1);
        } else if (0 && hl[j] == HL_NORMAL) {
          if (current_color != -1) {
            abAppend(ab, "\x1b[39m", 5);
            current_color = -1;
          }
          abAppend(ab, &c[j], 1);
        } else {
          int color = editorSyntaxToColor(hl[j]);
          if (color != current_color) {
            char buf[16];
            int clen = snprintf(buf, sizeof(buf), "\x1b[%dm", color);
            abAppend(ab, buf, clen);
            current_color = color;
          }
          abAppend(ab, &c[j], 1);
        }
      }
      if (in_search || in_selection) {
        abAppend(ab, "\x1b[49m", 5); // reset background at line end
      }
      abAppend(ab, "\x1b[39m", 5);
    }
    abAppend(ab, "\x1b[K", 3); // clear line
    abAppend(ab, "\r\n", 2);
  }
}

void editorDrawStatusBar(struct abuf *ab) {
  abAppend(ab, "\x1b[7m", 4);
  char status[80], rstatus[80];
  int len = snprintf(
      status, sizeof(status), "%.20s - %d lines %s -- %s %d -- %d",
      E.filename ? E.filename : "[No Name]", E.numrows,
      E.mode == DIM_NORMAL_MODE ? "NORMAL" : "INSERT",
      E.dirty ? "(modified)" : "", E.v_end.y - E.v_start.y, E.prevNormalKey);
  int rlen =
      snprintf(rstatus, sizeof(status), "%s | %d/%d",
               E.syntax ? E.syntax->filetype : "no ft", E.cy + 1, E.numrows);
  if (len > E.screencols)
    len = E.screencols;
  abAppend(ab, status, len);
  while (len < E.screencols) {
    if (E.screencols - len == rlen) {
      abAppend(ab, rstatus, rlen);
      break;
    } else {
      abAppend(ab, " ", 1);
      len++;
    }
  }
  abAppend(ab, "\x1b[m", 3);
  abAppend(ab, "\r\n", 2);
}

void editorDrawMessageBar(struct abuf *ab) {
  abAppend(ab, "\x1b[K", 3);
  int msglen = strlen(E.statusmsg);
  if (msglen > E.screencols)
    msglen = E.screencols;
  if (msglen && time(NULL) - E.statusmsg_time < 5)
    abAppend(ab, E.statusmsg, msglen);
}

void editorRefreshScreen(void) {
  editorScroll();
  struct abuf ab = { NULL, 0};
  abAppend(&ab, "\x1b[?25l", 6);
  // abAppend(&ab, "\x1b[2J", 4);
  abAppend(&ab, "\x1b[H", 3);
  editorDrawRows(&ab);
  editorDrawStatusBar(&ab);
  editorDrawMessageBar(&ab);

  char buf[32];
  snprintf(buf, sizeof(buf), "\x1b[%d;%dH", (E.cy - E.rowoff) + 1,
           (E.rx - E.coloff) + 1);
  abAppend(&ab, buf, strlen(buf));
  abAppend(&ab, "\x1b[?25h", 6);
  (void)write(STDOUT_FILENO, ab.b, ab.len);
  abFree(&ab);
}

void editorSetStatusMessage(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(E.statusmsg, sizeof(E.statusmsg), fmt, ap);
  va_end(ap);
  E.statusmsg_time = time(NULL);
}

/*** input ***/

char *editorPrompt(char *prompt, void (*callback)(char *, int)) {
  size_t bufsize = 128;
  char *buf = malloc(bufsize);

  size_t buflen = 0;
  buf[0] = '\0';

  while (1) {
    editorSetStatusMessage(prompt, buf);
    editorRefreshScreen();

    int c = editorReadKey();
    if (c == DEL_KEY || c == CTRL_KEY('h') || c == BACKSPACE) {
      if (buflen != 0)
        buf[--buflen] = '\0';
    } else if (c == '\x1b') {
      editorSetStatusMessage("");
      if (callback)
        callback(buf, c);
      free(buf);
      return NULL;
    } else if (c == '\r') {
      if (buflen != 0) {
        editorSetStatusMessage("");
        if (callback)
          callback(buf, c);
        return buf;
      }
    } else if (c == '\t') {
      // Tab completion for :e command
      if (strncmp(buf, "e ", 2) == 0) {
        char *prefix = buf + 2;
        char *completion = findFileCompletion(prefix);
        if (completion) {
          // Rebuild buffer with completed filename
          size_t newlen = 2 + strlen(completion);
          if (newlen >= bufsize) {
            bufsize = newlen + 1;
            buf = realloc(buf, bufsize);
          }
          strcpy(buf + 2, completion);
          buflen = newlen;
          free(completion);
        }
      }
    } else if (!iscntrl(c) && c < 128) {
      if (buflen == bufsize - 1) {
        bufsize *= 2;
        buf = realloc(buf, bufsize);
      }
      buf[buflen++] = c;
      buf[buflen] = '\0';
    }

    if (callback)
      callback(buf, c);
  }
}

// File completion helper - finds files matching prefix
// Returns longest common prefix of all matches
char *findFileCompletion(const char *prefix) {
  DIR *dir = opendir(".");
  if (!dir) return NULL;

  char *match = NULL;
  size_t prefix_len = strlen(prefix);

  struct dirent *entry;
  while ((entry = readdir(dir)) != NULL) {
    if (strncmp(entry->d_name, prefix, prefix_len) == 0) {
      if (match == NULL) {
        match = strdup(entry->d_name);
      } else {
        // Find common prefix between match and new entry
        size_t i = 0;
        while (match[i] && entry->d_name[i] && match[i] == entry->d_name[i]) {
          i++;
        }
        match[i] = '\0';
      }
    }
  }
  closedir(dir);

  // Only return if we found something longer than the original prefix
  if (match && strlen(match) > prefix_len) {
    return match;
  }
  free(match);
  return NULL;
}

// Prompt with file completion (for :e command)
char *editorPromptWithFileCompletion(char *prompt) {
  size_t bufsize = 128;
  char *buf = malloc(bufsize);

  size_t buflen = 0;
  buf[0] = '\0';

  while (1) {
    editorSetStatusMessage(prompt, buf);
    editorRefreshScreen();

    int c = editorReadKey();
    if (c == DEL_KEY || c == CTRL_KEY('h') || c == BACKSPACE) {
      if (buflen != 0)
        buf[--buflen] = '\0';
    } else if (c == '\x1b') {
      editorSetStatusMessage("");
      free(buf);
      return NULL;
    } else if (c == '\r') {
      if (buflen != 0) {
        editorSetStatusMessage("");
        return buf;
      }
    } else if (c == '\t') {
      // Tab completion
      char *completion = findFileCompletion(buf);
      if (completion) {
        free(buf);
        buf = completion;
        buflen = strlen(buf);
        bufsize = buflen + 1;
      }
    } else if (!iscntrl(c) && c < 128) {
      if (buflen == bufsize - 1) {
        bufsize *= 2;
        buf = realloc(buf, bufsize);
      }
      buf[buflen++] = c;
      buf[buflen] = '\0';
    }
  }
}

void editorJumpToMatchingBrace() {
  // Check if current character is an opening or closing brace
  if (E.cy >= E.numrows)
    return;

  erow *row = &E.row[E.cy];
  if (E.cx >= row->size)
    return;

  char current_char = row->chars[E.cx];
  char target_char = '\0';
  int direction = 0; // 1 for forward, -1 for backward

  // Determine what brace we're on and what to search for
  switch (current_char) {
  case '{':
    target_char = '}';
    direction = 1;
    break;
  case '}':
    target_char = '{';
    direction = -1;
    break;
  case '(':
    target_char = ')';
    direction = 1;
    break;
  case ')':
    target_char = '(';
    direction = -1;
    break;
  case '[':
    target_char = ']';
    direction = 1;
    break;
  case ']':
    target_char = '[';
    direction = -1;
    break;
  default:
    return; // Not on a brace
  }

  // Search for matching brace with nesting support
  int depth = 1;
  int x = E.cx + direction;
  int y = E.cy;

  while (y >= 0 && y < E.numrows) {
    erow *search_row = &E.row[y];

    // Set bounds for this row
    if (direction == 1) {
      if (x >= search_row->size) {
        y++;
        x = 0;
        continue;
      }
    } else {
      if (x < 0) {
        y--;
        if (y >= 0)
          x = E.row[y].size - 1;
        continue;
      }
    }

    char c = search_row->chars[x];

    // Check for matching brace or nested brace
    if (c == target_char) {
      depth--;
      if (depth == 0) {
        E.cy = y;
        E.cx = x;
        return;
      }
    } else if (c == current_char) {
      depth++;
    }

    x += direction;
  }
}

void editorMoveCursor(int key) {
  erow *row = (E.cy >= E.numrows) ? NULL : &E.row[E.cy];
  switch (key) {
  case HOME_KEY:
    E.cx = 0;
    break;
  case END_KEY:
    if (E.cy < E.numrows)
      E.cx = E.row[E.cy].size - 1;
    break;
  case ARROW_LEFT:
    if (E.cx != 0) {
      E.cx--;
    } else if (E.cy > 0) {
      E.cy--;
      E.cx = E.row[E.cy].size;
    }
    break;
  case ARROW_RIGHT:
    if (row && E.cx < row->size) {
      E.cx++;
    } else if (row && E.cx == row->size) {
      E.cy++;
      E.cx = 0;
    }
    break;
  case ARROW_DOWN:
    if (E.cy < E.numrows - 1) {
      E.cy++;
    }
    break;
  case ARROW_UP:
    if (E.cy != 0) {
      E.cy--;
    }
    break;
  }
  row = (E.cy >= E.numrows) ? NULL : &E.row[E.cy];
  int rowlen = row ? row->size : 0;
  if (E.cx > rowlen) {
    E.cx = rowlen;
  }
}

void setEndVisualMark() {
  E.v_end.x = E.cx;
  E.v_end.y = E.cy;
}

void startVisualMarks() {
  E.v_start.x = E.cx;
  E.v_start.y = E.cy;
  setEndVisualMark();
}

void deleteSelection() { editorDelSpan(E.v_start, E.v_end); }

void yankSelection() {
  int start_y = E.v_start.y;
  int end_y = E.v_end.y;
  int start_x = E.v_start.x;
  int end_x = E.v_end.x;

  // Normalize so start is before end
  if (start_y > end_y || (start_y == end_y && start_x > end_x)) {
    int tmp = start_y;
    start_y = end_y;
    end_y = tmp;
    tmp = start_x;
    start_x = end_x;
    end_x = tmp;
  }

  // Calculate buffer size needed
  int buflen = 0;
  for (int y = start_y; y <= end_y; y++) {
    if (y >= E.numrows)
      break;
    int x_start = (y == start_y) ? start_x : 0;
    int x_end = (y == end_y) ? end_x : E.row[y].size;
    buflen += (x_end - x_start);
    if (y < end_y)
      buflen++; // for newline
  }

  // Allocate and copy
  free(E.clipboard);
  E.clipboard = malloc(buflen + 1);
  E.clipboard_len = buflen;

  int pos = 0;
  for (int y = start_y; y <= end_y; y++) {
    if (y >= E.numrows)
      break;
    int x_start = (y == start_y) ? start_x : 0;
    int x_end = (y == end_y) ? end_x : E.row[y].size;
    int len = x_end - x_start;
    memcpy(&E.clipboard[pos], &E.row[y].chars[x_start], len);
    pos += len;
    if (y < end_y) {
      E.clipboard[pos++] = '\n';
    }
  }
  E.clipboard[pos] = '\0';

  editorSetStatusMessage("Yanked %d chars", buflen);
}

void pasteClipboard() {
  if (!E.clipboard || E.clipboard_len == 0) {
    editorSetStatusMessage("Clipboard is empty");
    return;
  }

  // Insert below cursor
  editorInsertNewLine();

  // Insert clipboard content
  for (int i = 0; i < E.clipboard_len; i++) {
    if (E.clipboard[i] == '\n') {
      editorInsertNewLine();
    } else {
      editorInsertChar(E.clipboard[i]);
    }
  }
}

// Returns 1 if key was a movement command, 0 otherwise
int handleMovementKey(int key, int prev) {
  switch (key) {
  case 'j':
    editorMoveCursor(ARROW_DOWN);
    return 1;
  case 'k':
    editorMoveCursor(ARROW_UP);
    return 1;
  case 'h':
    editorMoveCursor(ARROW_LEFT);
    return 1;
  case 'l':
    editorMoveCursor(ARROW_RIGHT);
    return 1;
  case 'w':
    if (prev != 0)
      return 0;
    editorMoveWordForward();
    return 1;
  case '0':
    editorMoveCursor(HOME_KEY);
    return 1;
  case '$':
    editorMoveCursor(END_KEY);
    return 1;
  case 'g':
    // 'g' needs special handling for 'gg', so return 0 to let caller handle it
    return 0;
  case 'G':
    E.cy = E.numrows > 0 ? E.numrows - 1 : 0;
    return 1;
  default:
    return 0;
  }
}

void handleVisualModeKeypress(int key) {
  int prev = 0; // TODO
  switch (key) {
  case 'v':
    E.mode = DIM_NORMAL_MODE;
    return;
  case 'y':
    yankSelection();
    E.mode = DIM_NORMAL_MODE;
    return;
  case 'x':
  case 'd':
    editorPushUndoState();
    deleteSelection();
    E.mode = DIM_NORMAL_MODE;
    break;
  case '%':
    editorJumpToMatchingBrace();
    setEndVisualMark();
    break;
  default:
    if (handleMovementKey(key, prev)) {
      setEndVisualMark();
    }
    break;
  }
}

void handleNormalModeKeypress(int key) {
  int prev = E.prevNormalKey;
  E.prevNormalKey = 0;

  // Handle digit keys for repeat count
  if (key >= '1' && key <= '9') {
    E.repeatCount = E.repeatCount * 10 + (key - '0');
    return;
  }
  if (key == '0' && E.repeatCount > 0) {
    E.repeatCount = E.repeatCount * 10;
    return;
  }

  // Get the repeat count (default to 1 if not set)
  int count = E.repeatCount > 0 ? E.repeatCount : 1;
  E.repeatCount = 0;  // Reset for next command

  // Try to handle as movement first (with repeat)
  if (handleMovementKey(key, prev)) {
    for (int i = 1; i < count; i++) {
      handleMovementKey(key, 0);
    }
    return;
  }

  switch (key) {
  case 'c':
    E.prevNormalKey = 'c';
    break;
  case 'i':
    if (prev == 'c') {
      E.prevNormalKey = 'i';
    } else {
      E.mode = DIM_INSERT_MODE;
    }
    break;
  case 'o':
    // insert line, enter INSERT mode
    editorInsertRow(E.cy + 1, "", 0);
    E.cy++;
    E.cx = 0;
    E.mode = DIM_INSERT_MODE;
    break;
  case 'd':
    if (prev == 'd') {
      // delete row(s)
      editorPushUndoState();
      for (int i = 0; i < count && E.cy < E.numrows; i++) {
        editorDelRow(E.cy);
      }
    } else {
      E.prevNormalKey = key;
      E.repeatCount = count;  // Preserve count for dd
    }
    break;
  case 'x':
    // delete char(s) and remain
    editorPushUndoState();
    for (int i = 0; i < count; i++) {
      editorXChar();
    }
    break;
  case 'A':
    editorMoveCursor(END_KEY);
    E.mode = DIM_INSERT_MODE;
    break;
  case 'g':
    if (prev == 'g') {
      E.cy = 0;
    } else {
      // save this g
      E.prevNormalKey = key;
    }
    break;
  case 'w':
    switch (prev) {
    case 'c':
      editorPushUndoState();
      editorDelToEndOfWord();
      E.mode = DIM_INSERT_MODE;
      break;
    case 'i':
      editorPushUndoState();
      editorDelSurroundingWord();
      E.mode = DIM_INSERT_MODE;
      break;
    case 'd':
      editorPushUndoState();
      editorDelToEndOfWord();
      break;
    case 0:
      editorMoveWordForward();
      break;
    default:
      break;
    }
    break;
  case ':':
    exMode();
    break;
  case '/':
    editorFind();
    break;
  case 'n':
    E.searchDirection = 1;
    nextSearch();
    break;
  case 'N':
    E.searchDirection = -1;
    nextSearch();
    break;
  case '*':
    editorSearchWordUnderCursor();
    break;
  case 'v':
    E.mode = DIM_VISUAL_MODE;
    startVisualMarks();
    break;
  case 'y':
    if (prev == 'y') {
      // yy - yank current line
      if (E.cy < E.numrows) {
        erow *row = &E.row[E.cy];
        free(E.clipboard);
        E.clipboard = malloc(row->size + 1);
        memcpy(E.clipboard, row->chars, row->size);
        E.clipboard[row->size] = '\0';
        E.clipboard_len = row->size;
        editorSetStatusMessage("Yanked line: %d chars", row->size);
      }
    } else {
      E.prevNormalKey = 'y';
    }
    break;
  case 'p':
    editorPushUndoState();
    pasteClipboard();
    break;
  case '%':
    editorJumpToMatchingBrace();
    break;
  case 'u':
    editorUndo();
    break;
  case 'f':
  case 't': {
    // Check if this is ct{char}, cf{char}, dt{char}, df{char}
    if (prev == 'c' || prev == 'd') {
      int target = editorReadKey();
      if (E.cy < E.numrows) {
        erow *row = &E.row[E.cy];
        int found = -1;
        for (int i = E.cx; i < row->size; i++) {
          if (row->chars[i] == target) {
            found = (key == 'f') ? i + 1 : i;  // f includes char, t excludes
            break;
          }
        }
        if (found > E.cx) {
          editorPushUndoState();
          editorRowDelSpan(row, E.cx, found);
          if (prev == 'c') {
            E.mode = DIM_INSERT_MODE;
          }
        }
      }
    } else {
      // Plain f{char} or t{char} - jump to character
      int target = editorReadKey();
      if (E.cy < E.numrows) {
        erow *row = &E.row[E.cy];
        for (int i = E.cx + 1; i < row->size; i++) {
          if (row->chars[i] == target) {
            E.cx = (key == 'f') ? i : i - 1;
            break;
          }
        }
      }
    }
    break;
  }
  default:
    break;
  }
}

void handleInsertModeKeypress(int c) {
  static int quit_times = DIM_QUIT_TIMES;

  // Handle jj escape sequence
  #define JJ_TIMEOUT_MS 150
  if (c == 'j') {
    long now = getCurrentTimeMs();
    if (E.pendingInsertKey == 'j' && (now - E.pendingInsertTimeMs) < JJ_TIMEOUT_MS) {
      // Second j within timeout - escape to normal mode
      // Delete the first j that was inserted
      editorDelChar();
      editorPushUndoState();
      E.mode = DIM_NORMAL_MODE;
      E.pendingInsertKey = 0;
      quit_times = DIM_QUIT_TIMES;
      return;
    }
    // First j or timeout expired - insert it and mark as pending
    editorInsertChar(c);
    E.pendingInsertKey = 'j';
    E.pendingInsertTimeMs = now;
    quit_times = DIM_QUIT_TIMES;
    return;
  }

  // Any other key clears the pending j
  E.pendingInsertKey = 0;

  switch (c) {
  case '\r':
    editorInsertNewLine();
    break;

  case CTRL_KEY('q'):
    if (E.dirty && quit_times > 0) {
      editorSetStatusMessage("WARNING!!! File has unsaved changes. "
                             "Press Ctrl-Q %d more times to quit.",
                             quit_times);
      quit_times--;
      return;
    }
    clearScreen();
    exit(0);
    break;

  case CTRL_KEY('s'):
    editorSave();
    break;

  case PAGE_UP:
  case PAGE_DOWN: {
    if (c == PAGE_UP) {
      E.cy = E.rowoff;
    } else if (c == PAGE_DOWN) {
      E.cy = E.rowoff + E.screenrows - 1;
      if (E.cy > E.numrows)
        E.cy = E.numrows;
    }
    int times = E.screenrows;
    while (times--) {
      editorMoveCursor(c == PAGE_UP ? ARROW_UP : ARROW_DOWN);
    }
    break;
  }
  case ARROW_LEFT:
  case ARROW_RIGHT:
  case ARROW_UP:
  case ARROW_DOWN:
  case HOME_KEY:
  case END_KEY:
    editorMoveCursor(c);
    break;

  case BACKSPACE:
  case CTRL_KEY('h'):
  case DEL_KEY:
    if (c == DEL_KEY)
      editorMoveCursor(ARROW_RIGHT);
    editorDelChar();
    break;

  case CTRL_KEY('l'):
  case '\x1b':
    editorPushUndoState();
    E.mode = DIM_NORMAL_MODE;
    break;

  case CTRL_KEY('f'):
    editorFind();
    break;

  case '\t': {
    // Check if file uses tabs (scan for tab character in any row)
    int useTabs = 0;
    for (int i = 0; i < E.numrows && !useTabs; i++) {
      for (int j = 0; j < E.row[i].size; j++) {
        if (E.row[i].chars[j] == '\t') {
          useTabs = 1;
          break;
        }
      }
    }
    if (useTabs) {
      editorInsertChar('\t');
    } else {
      // Insert 4 spaces instead of tab character
      for (int i = 0; i < DIM_TAB_STOP; i++) {
        editorInsertChar(' ');
      }
    }
    break;
  }

  default:
    editorInsertChar(c);
    break;
  }

  quit_times = DIM_QUIT_TIMES;
}

void editorProcessKeypress(void) {

  int c = editorReadKey();
  switch (E.mode) {
  case DIM_NORMAL_MODE:
    handleNormalModeKeypress(c);
    break;
  case DIM_INSERT_MODE:
    handleInsertModeKeypress(c);
    break;
  case DIM_VISUAL_MODE:
    handleVisualModeKeypress(c);
    break;
  default:
    break;
  }
}

/*** init ***/

void initEditor(void) {
  E.cx = 0;
  E.cy = 0;
  E.rx = 0;
  E.rowoff = 0;
  E.coloff = 0;
  E.numrows = 0;
  E.row = NULL;
  E.dirty = 0;
  E.filename = NULL;
  E.statusmsg[0] = '\0';
  E.statusmsg_time = 0;
  E.syntax = NULL;
  E.ts_parser = NULL;
  E.ts_tree = NULL;
  E.mode = DIM_NORMAL_MODE;
  E.prevNormalKey = 0;
  E.repeatCount = 0;
  E.pendingInsertKey = 0;
  E.pendingInsertTimeMs = 0;
  E.searchString = NULL;
  E.searchIndex = 0;
  E.searchDirection = 1;
  E.clipboard = NULL;
  E.clipboard_len = 0;
  E.last_ts_parse = time(NULL);
  E.undo_stack = NULL;
  E.undo_stack_size = 0;
  E.undo_stack_capacity = 0;

  if (getWindowSize(&E.screenrows, &E.screencols) == -1)
    die("getWindowSize");
  E.screenrows -= 2;
}

int main(int argc, char *argv[]) {
  enableRawMode();
  initEditor();
  if (argc >= 2) {
    editorOpen(argv[1]);
  }

  // editorSetStatusMessage("HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F =
  // find");

  while (1) {
    editorRefreshScreen();
    editorProcessKeypress();
  }
  return 0;
}
