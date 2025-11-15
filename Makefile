dim: dim.c
	$(CC) dim.c -g -O0 -o dim -Wall -Wextra -pedantic -std=c99

color_test: color_test.c
	$(CC) -Wall -Wextra -O2 -o color_test color_test.c
