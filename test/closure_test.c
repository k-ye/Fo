// func counter(int x) func() int {
//   return func() int {
//     x = x - 1
//     return x
//   }
// }

// func main() {
//   var c = counter(3)
//   c()
//   c()
//   c()
// }

#include "runtime/base.h"
#include "runtime/gc.h"
#include "runtime/gc_header.h"
#include "runtime/memory.h"
#include "runtime/tuple.h"

val_t counter_closure1(gc_header_t* g_closure) {
  gc_ref(g_closure);

  gc_header_t* closure_x = (gc_header_t*)get_tuple_at(g_closure, 1);
  *GC_TO_OBJ(val_t, closure_x) = *GC_TO_OBJ(val_t, closure_x) - 1;
  val_t ret = *GC_TO_OBJ(val_t, closure_x);

  gc_unref(g_closure);
  return ret;
}

gc_header_t* counter(val_t x) {
  gc_header_t* g_closure = alloc_tuple(2);
  set_tuple_at(g_closure, 0, (val_t)counter_closure1, /*needs_gc=*/false);
  // This is wrong! We need to allocate |x| on the heap, it can be captured
  // by many closures, and they all have to share the same object.
  gc_header_t* g_x = gc_alloc_trivial(sizeof(val_t));
  *GC_TO_OBJ(val_t, g_x) = x;
  set_tuple_at(g_closure, 1, (val_t)g_x, /*needs_gc=*/true);

  gc_unref(g_x);
  return g_closure;
}

typedef val_t (*counter_closure1_t)(gc_header_t*);

#define RUNTIME_RESERVED_SIZE 1024 * 1024
#define COROUTINE_STACK_SIZE 1024 * 1024
#define NUM_COROUTINES 1
#define HEAP_SIZE 4 * 1024 * 1024
#define NUM_GC_HEADERS 1000

int main() {
  init_memory(RUNTIME_RESERVED_SIZE, COROUTINE_STACK_SIZE, NUM_COROUTINES,
              HEAP_SIZE);
  init_gc(NUM_GC_HEADERS);

  gc_header_t* g_closure = counter(3);

  counter_closure1_t c = (counter_closure1_t)get_tuple_at(g_closure, 0);
  printf("%lld\n", c(g_closure));
  printf("%lld\n", c(g_closure));
  printf("%lld\n", c(g_closure));

  gc_unref(g_closure);
  printf("num gc headers in use: %lu\n", num_gc_headers_in_use());

  free_memory();

  return 0;
}