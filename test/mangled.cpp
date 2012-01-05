#include <iostream>

class dummy {
  const static int dummy_value = 1;
public:
  int proc(void){return dummy_value;};
};

static dummy *dummyobj = new dummy();

int main(){
  std::cout << dummyobj->proc() << std::endl;
  return 0;
}
