#include <iostream>
#include <assets/message_txt.h>

int main(int argc, char** argv) {
    std::string message(reinterpret_cast<const char*>(message_txt_buffer), message_txt_length);
    std::cout << message << std::endl;
    return 0;
}
