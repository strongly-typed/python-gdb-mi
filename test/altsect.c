#include <stdio.h>
enum test_op {
    TEST_OP_TEAR_NONE = 0,
    TEST_OP_TEAR_UP,
    TEST_OP_TEAR_DOWN,
    TEST_OP_ASSERT,
};

struct test_case {
    enum test_op op;
    
};

#define SECT "TESTCASES"
int main(){
    __attribute__((used, __section__(SECT)))
         static struct test_case test_xxx[] = \
         {
             {
                 .op = TEST_OP_TEAR_UP,
             }
         };
    return 0;
}
