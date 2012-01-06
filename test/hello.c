#include <stdio.h>
#include <stdint.h>

static uint32_t i1 = 0x1234;
static uint32_t i2 = 0x12345678;

void hello(int test_int_in_arg){
    int test_int_in_hello = 11;
    static int test_static_int_in_hello = 12;
    {
        int test_int_in_block = 13;
        static int test_static_int_in_block = 14;
        printf("hello %08x %08x\n", i1, i2);
    }
}


int test_global_int = 0x0102;
const int test_const_global_int = 0x0102;

static int test_static_int = 0x1234;
static const int test_static_const_int = 0x1234;

static double test_static_double = 1.234;
static const double test_static_const_double = 1.234;

int main(){
    int test_int_in_main = 1;
    const int test_const_int_in_main = 2;

    static int test_static_int_in_main = 3;
    static const int test_static_const_int_in_main = 4;

    hello(5);

    return 6;
}
