#include <execinfo.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "runtime/base.h"
#include "runtime/gc.h"
#include "runtime/memory.h"
#include "runtime/tuple.h"

#define RUNTIME_RESERVED_SIZE 1024 * 1024
#define COROUTINE_STACK_SIZE 1024 * 1024
#define NUM_COROUTINES 1
#define HEAP_SIZE 4 * 1024 * 1024
#define NUM_GC_HEADERS 1000

void sig_handler(int sig) {
  void* array[20];
  size_t size;

  // get void*'s for all entries on the stack
  size = backtrace(array, 20);

  // print out all the frames to stderr
  fprintf(stderr, "Error: signal %d:\n", sig);
  backtrace_symbols_fd(array, size, STDERR_FILENO);
  exit(1);
}

void setup() {
  signal(SIGSEGV, sig_handler);

  init_memory(RUNTIME_RESERVED_SIZE, COROUTINE_STACK_SIZE, NUM_COROUTINES,
              HEAP_SIZE);
  init_gc(NUM_GC_HEADERS);
  // init_runtime_tuple();
}

void tear_down() { free_memory(); }

void test_gc_basic() {
  printf(">>> test_gc_basic begin\n");
  gc_header_t* gc_t = alloc_tuple(4);
  CHECK(heap_usage() >= get_tuple_operators()->get_bytes((val_t*)(gc_t->obj)));
  CHECK(num_gc_headers_in_use() == 1);

  gc_unref(gc_t);
  CHECK(num_gc_headers_in_use() == 0);

  run_gc();
  CHECK(heap_usage() == 0);
  printf("<<< test_gc_basic passed!\n\n");
}

void test_gc_circular_reference1() {
  printf(">>> test_gc_circular_reference1 begin\n");
  gc_header_t* gc_t1 = alloc_tuple(3);
  gc_header_t* gc_t2 = alloc_tuple(2);
  gc_header_t* gc_t3 = alloc_tuple(2);
  const bool needs_gc = true;
  set_tuple_at(gc_t1, 0, (val_t)gc_t2, needs_gc);
  set_tuple_at(gc_t2, 0, (val_t)gc_t3, needs_gc);
  set_tuple_at(gc_t3, 0, (val_t)gc_t1, needs_gc);

  CHECK(num_gc_headers_in_use() == 3);

  // printf("heap_usage() before gc = %lu\n", heap_usage());

  gc_unref(gc_t1);
  gc_unref(gc_t2);
  gc_unref(gc_t3);
  CHECK(num_gc_headers_in_use() == 3);

  run_gc();
  // printf("after gc, heap_usage()=%lu, num_in_use()=%lu\n", heap_usage(),
  //        num_gc_headers_in_use());
  CHECK(heap_usage() == 0);
  CHECK(num_gc_headers_in_use() == 0);
  printf("<<< test_gc_circular_reference1 passed!\n\n");
}

void test_gc_circular_reference2() {
  printf(">>> test_gc_circular_reference2 begin\n");
  gc_header_t* gc_t1 = alloc_tuple(2);
  gc_header_t* gc_t2 = alloc_tuple(2);
  gc_header_t* gc_t3 = alloc_tuple(4);
  const bool needs_gc = true;
  set_tuple_at(gc_t1, 0, (val_t)gc_t2, needs_gc);
  set_tuple_at(gc_t2, 0, (val_t)gc_t1, needs_gc);
  set_tuple_at(gc_t1, 1, (val_t)gc_t3, needs_gc);

  CHECK(num_gc_headers_in_use() == 3);

  // printf("heap_usage() before gc = %lu\n", heap_usage());

  gc_unref(gc_t1);
  gc_unref(gc_t2);
  CHECK(num_gc_headers_in_use() == 3);

  run_gc();
  CHECK(heap_usage() == get_tuple_operators()->get_bytes(gc_t3->obj));
  CHECK(num_gc_headers_in_use() == 1);
  printf("<<< test_gc_circular_reference2 passed!\n\n");
}

void test_gc_circular_reference3() {
  printf(">>> test_gc_circular_reference3 begin\n");
  gc_header_t* gc_t1 = alloc_tuple(2);
  const bool needs_gc = true;
  set_tuple_at(gc_t1, 0, (val_t)gc_t1, needs_gc);
  CHECK(num_gc_headers_in_use() == 1);

  gc_unref(gc_t1);
  CHECK(num_gc_headers_in_use() == 1);

  run_gc();
  CHECK(heap_usage() == 0);
  CHECK(num_gc_headers_in_use() == 0);
  printf("<<< test_gc_circular_reference3 passed!\n\n");
}

int main() {
  setup();
  test_gc_basic();
  tear_down();

  setup();
  test_gc_circular_reference1();
  tear_down();

  setup();
  test_gc_circular_reference2();
  tear_down();

  setup();
  test_gc_circular_reference3();
  tear_down();
}