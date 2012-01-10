#include <stdio.h>

int int_g = 1;
static int int_s = 2;
extern int xxx;

int main(){
    static int int_l = 3;
    printf("g%d, s%d, l%d\n", int_g, int_s, int_l);
    return 0;
}
