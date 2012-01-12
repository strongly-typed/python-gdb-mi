#include <stdio.h>
#include <time.h>
#include <poll.h>
#include <unistd.h>

static char buffer [4096];
static int filled = 0;

static int on_read(int fd)
{
    int num = read(fd, buffer, sizeof(buffer));
    if(num > 0){
        filled = num;
    }
    return num;
}

static int on_write(int fd)
{
    int num = write(fd, buffer, filled);
    if(num > 0){
        filled = 0;
    }
    return num;
}

static int dummy(int *src)
{
    *src++;
    return *src;
}

static int loop(int fd, int t1, int t2){

    struct pollfd fds[] = {
        {
            .fd = fd,
            .events = POLLIN|((filled > 0)?(POLLOUT):0),
        },
    };
    if(poll(fds, 1, 1000/*ms*/) > 0){
        struct pollfd *p = fds;
        if(p->revents & POLLIN){
            if(on_read(p->fd) < 0)
                return -1;
        }
        if(p->revents & POLLOUT){
            if(on_write(p->fd) < 0)
                return -1;
        }
        if(p->revents & POLLHUP){
            return -1;
        }
    }
    return 0;
}

int main(){
    int fd = 0;

    int test_1 = 0;
    int test_2 = 0;

    test_2 = dummy(&test_1);

    while(1){
        if(loop(fd, test_1, test_2) < 0)
            return -1;
    }
    return 0;
}
