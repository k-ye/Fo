cmake_minimum_required(VERSION 3.1)
enable_language(C ASM)
project(fo)

include_directories(.)

set(SOURCES runtime/base.c runtime/gc_header.c runtime/gc.c runtime/tuple.c)
# file(GLOB SOURCES "runtime/*.c")

set (CMAKE_C_STANDARD 11)

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-deprecated-declarations")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Werror")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fno-asynchronous-unwind-tables -fno-exceptions -mno-red-zone")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g")

SET(ASM_OPTIONS "-x assembler-with-cpp")
SET(CMAKE_ASM_FLAGS "${CFLAGS} ${ASM_OPTIONS}" )

add_library(fo_lib STATIC ${SOURCES})

add_executable(gc_test test/gc_test.c)
link_directories(.)
target_link_libraries(gc_test LINK_PUBLIC fo_lib)

add_executable(closure_test test/closure_test.c)
target_link_libraries(closure_test LINK_PUBLIC fo_lib)