#include <iostream>

class dummy {
  const static int dummy_value = 1;
public:
  dummy(int value){state = value;};
  int proc(void){return dummy_value;};
  int state;
};

static dummy *test_static = new dummy(2);
dummy *test_global = new dummy(3);

int main(){
  std::cout << test_static->proc() << std::endl;
  std::cout << test_global->proc() << std::endl;
  return 0;
}
