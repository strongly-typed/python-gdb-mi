#include <stdio.h>
int main(){
     __attribute__((__section__(SECT))) static int alt_sect;
    printf("%d\n", alt_sect);
    return 0;
}
