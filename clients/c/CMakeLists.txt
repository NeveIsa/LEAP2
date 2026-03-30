cmake_minimum_required(VERSION 3.14)
project(leap_client C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

find_package(CURL REQUIRED)

# --- Static library ---
add_library(leap_client STATIC
    src/leap_client.c
    src/cJSON.c
)
target_include_directories(leap_client
    PUBLIC  include
    PRIVATE src
)
target_link_libraries(leap_client PUBLIC CURL::libcurl m)

# --- C example ---
add_executable(example examples/example.c)
target_link_libraries(example PRIVATE leap_client)

# --- C++ example ---
add_executable(example_cpp examples/example.cpp)
target_link_libraries(example_cpp PRIVATE leap_client)
