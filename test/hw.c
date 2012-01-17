#include <stdio.h>
#include <sys/time.h>

int int_g = 1;
static int int_s = 2;
extern int xxx;
int ia[10];

struct timeval tv;

int main(){
    static int int_l = 3;
    __attribute__((__section__(".bss"))) static int alt_sect;
    printf("g%d, s%d, l%d %x\n", int_g, int_s, int_l, alt_sect);
    alt_sect = 0x1234;
    printf("g%d, s%d, l%d %x\n", int_g, int_s, int_l, alt_sect);
    return 0;
}
