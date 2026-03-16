cmake_minimum_required(VERSION 3.14)
project(atlas_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Optimization flags
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")

# Find pybind11
find_package(pybind11 REQUIRED)

# Build Python module
pybind11_add_module(atlas_cpp
    bindings.cpp
)

target_include_directories(atlas_cpp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Install
install(TARGETS atlas_cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/lib)
