CFLAGS = -Wall -gdwarf-4
CXXFLAGS = -Wall -gdwarf-4

all: hello hello_nodebug mangled loop hw

hello: hello.c

hello_nodebug: hello.c
	$(CC) -o $@ $<

mangled: mangled.cpp