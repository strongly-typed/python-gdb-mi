#include <iostream>

class dummy {
  const static int dummy_value = 1;
public:
  static const char dummy_bytes[];
  dummy(int value){state = value;};
  int proc(void){return dummy_value;};
  int state;
};

const char dummy::dummy_bytes[] = "ABCDEFGH";

static dummy *test_static = new dummy(2);
dummy *test_global = new dummy(3);

namespace xxx {
  dummy test_namespaced(3);
}

int yyy(void){
  static dummy test_in_block(3);
  return test_in_block.proc();
}

int main(){
  std::cout << test_static->proc() << std::endl;
  std::cout << test_global->proc() << std::endl;
  yyy();
  return 0;
}
