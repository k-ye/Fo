#ifndef RUNTIME_MEMORY_H_
#define RUNTIME_MEMORY_H_

#include <stdlib.h>
#include "runtime/base.h"

// Runtime memory layout:
//
// ------------
// |          |
// |          |
// |          |
// |          |
// |  global  |
// |   heap   |
// |          |
// |          |
// |          |
// |          |
// ------------ stack_top(n) / heap_begin()
// | cn stack |
// ------------ stack_top(n - 1) / stack_bottom(n)
// |          |
// |   ....   |
// |          |
// ------------ stack_top(1) / stack_bottom(2)
// | c2 stack |
// ------------ stack_top(0) / stack_bottom(1)
// | c1 stack |
// ------------ stack_bottom(0)
// |/  /  /  /|
// |  /  /  / |
// | /  /  /  |
// ------------ runtime_reserved_begin()
//
void init_memory(size_t runtime_reserved_size, size_t per_stack_size,
                 int num_stacks, size_t heap_size);
void free_memory();

// Stack grows downward.
char* stack_top(int stack_i);
char* stack_bottom(int stack_i);

char* alloc_runtime_reserved(size_t size);
char* alloc_heap(size_t size);
size_t heap_usage();

#endif  // RUNTIME_MEMORY_H_