#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    const char *term = getenv("TERM");
    int tty_out = isatty(fileno(stdout));
    int tty_err = isatty(fileno(stderr));

    printf("TERM=%s\n", term ? term : "(null)");
    printf("isatty(stdout)=%d\n", tty_out);
    printf("isatty(stderr)=%d\n", tty_err);

    printf("stdout fd=%d, stderr fd=%d\n", fileno(stdout), fileno(stderr));

    printf("Attempting color via stdout:\n");
    printf("\033[31mred text\033[0m\n");
    printf("\033[32mgreen text\033[0m\n");
    printf("\033[33myellow text\033[0m\n");
    fflush(stdout);

    fprintf(stderr, "Attempting color via stderr:\n");
    fprintf(stderr, "\033[34mblue text\033[0m\n");
    fprintf(stderr, "\033[35mmagenta text\033[0m\n");
    fprintf(stderr, "\033[36mcyan text\033[0m\n");
    fflush(stderr);

    return 0;
}

