#include <stdio.h>
#include <stdint.h>

static uint32_t i1 = 0x1234;
static uint32_t i2 = 0x1234;

void hello(void){
    printf("hello %08x %08x\n", i1, i2);
}
int main(){
    int dummy = 1;
    hello();
}
