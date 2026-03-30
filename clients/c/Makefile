CC      = gcc
CXX     = g++
CFLAGS  = -Wall -Wextra -Iinclude -Isrc
LDFLAGS = -lcurl -lm

SRC     = src/leap_client.c src/cJSON.c
OBJ     = $(SRC:.c=.o)
LIB     = libleap_client.a

all: $(LIB)

$(LIB): $(OBJ)
	ar rcs $@ $^

src/%.o: src/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

example: examples/example.c $(LIB)
	$(CC) $(CFLAGS) -o $@ $< -L. -lleap_client $(LDFLAGS)

example_cpp: examples/example.cpp $(LIB)
	$(CXX) $(CFLAGS) -std=c++17 -o $@ $< -L. -lleap_client $(LDFLAGS)

clean:
	rm -f src/*.o $(LIB) example example_cpp

.PHONY: all clean example example_cpp
