CFLAGS = -Wall -gdwarf-4
CXXFLAGS = -Wall -gdwarf-4

all: hello hello_nodebug mangled loop hw hw_nodebug

hello: hello.c

hello_nodebug: hello.c
	$(CC) -o $@ $<

hw_nodebug: hw.c
	$(CC) -o $@ $<

mangled: mangled.cpp