/********** Fo Generated C Code **********/
#include "runtime/base.h"
#include "runtime/gc.h"
#include "runtime/gc_header.h"
#include "runtime/memory.h"
#include "runtime/tuple.h"

typedef void (*makeClosure_c0_c0_funct)(gc_header_t*);
typedef gc_header_t* (*makeClosure_c0_funct)(gc_header_t*);
typedef int64_t (*main_c0_funct)(gc_header_t*, int64_t, int64_t);
typedef gc_header_t* (*makeClosure_funct)(gc_header_t*, int64_t);

void makeClosure_c0_c0(gc_header_t* context_tuple) {
  gc_ref(context_tuple);

  gc_header_t* i_uniq0 = (gc_header_t*)get_tuple_at(context_tuple, 1);
  gc_header_t* j_uniq0 = (gc_header_t*)get_tuple_at(context_tuple, 2);
  printf("makeClosure_c0_c0, i=%lld, j=%lld\n", *GC_TO_OBJ(int64_t, i_uniq0),
         *GC_TO_OBJ(int64_t, j_uniq0));
  *GC_TO_OBJ(int64_t, i_uniq0) =
      (*GC_TO_OBJ(int64_t, i_uniq0)) + (*GC_TO_OBJ(int64_t, j_uniq0));
  printf("makeClosure_c0_c0, i=%lld\n", *GC_TO_OBJ(int64_t, i_uniq0));

  gc_unref(context_tuple);
}

gc_header_t* makeClosure_c0(gc_header_t* context_tuple) {
  gc_ref(context_tuple);

  val_t i_uniq0 = get_tuple_at(context_tuple, 1);
  gc_header_t* makeClosure_c0_retarg_uniq0;
  {
    gc_header_t* j_uniq0 = gc_alloc_trivial(sizeof(val_t));
    *GC_TO_OBJ(int64_t, j_uniq0) = 2;

    makeClosure_c0_retarg_uniq0 = alloc_tuple(3);
    set_tuple_at(makeClosure_c0_retarg_uniq0, 0, (val_t)makeClosure_c0_c0,
                 false);
    set_tuple_at(makeClosure_c0_retarg_uniq0, 1, (val_t)i_uniq0,
                 /*needs_gc=*/true);
    set_tuple_at(makeClosure_c0_retarg_uniq0, 2, (val_t)j_uniq0,
                 /*needs_gc=*/true);
    gc_unref(j_uniq0);
  }

  gc_unref(context_tuple);
  return makeClosure_c0_retarg_uniq0;
}

gc_header_t* makeClosure(gc_header_t* context_tuple, int64_t i_uniq0_raw) {
  gc_header_t* i_uniq0 = gc_alloc_trivial(sizeof(val_t));
  *GC_TO_OBJ(int64_t, i_uniq0) = i_uniq0_raw;

  gc_header_t* makeClosure_retarg_uniq0;
  gc_header_t* makeClosure_func_call_flat0_uniq0;
  makeClosure_func_call_flat0_uniq0 = alloc_tuple(2);
  set_tuple_at(makeClosure_func_call_flat0_uniq0, 0, (val_t)makeClosure_c0,
               /*needs_gc=*/false);
  set_tuple_at(makeClosure_func_call_flat0_uniq0, 1, (val_t)i_uniq0,
               /*needs_gc=*/true);
  makeClosure_retarg_uniq0 = ((makeClosure_c0_funct)get_tuple_at(
      makeClosure_func_call_flat0_uniq0, 0))(makeClosure_func_call_flat0_uniq0);

  gc_unref(makeClosure_func_call_flat0_uniq0);
  gc_unref(i_uniq0);
  return makeClosure_retarg_uniq0;
}

int64_t main_c0(gc_header_t* context_tuple, int64_t i_uniq2, int64_t j_uniq2) {
  gc_ref(context_tuple);

  int64_t main_c0_retarg_uniq0;
  int64_t main_c0_retarg_rhs_uniq0;
  int64_t main_c0_retarg_rhs_rhs_uniq0;
  main_c0_retarg_rhs_rhs_uniq0 = -(2);
  main_c0_retarg_rhs_uniq0 = (j_uniq2) * (main_c0_retarg_rhs_rhs_uniq0);
  main_c0_retarg_uniq0 = (i_uniq2) + (main_c0_retarg_rhs_uniq0);

  gc_unref(context_tuple);
  return main_c0_retarg_uniq0;
}

void main_entry(gc_header_t* context_tuple) {
  int64_t i_uniq1;
  i_uniq1 = -(2);
  int64_t j_uniq1;
  j_uniq1 = -(22);
  int64_t k_uniq0;
  gc_header_t* main_func_call_flat0_uniq0;
  main_func_call_flat0_uniq0 = alloc_tuple(1);
  set_tuple_at(main_func_call_flat0_uniq0, 0, (val_t)main_c0,
               /*needs_gc=*/false);

  k_uniq0 = ((main_c0_funct)get_tuple_at(main_func_call_flat0_uniq0, 0))(
      main_func_call_flat0_uniq0, i_uniq1, j_uniq1);
  printf("k=%lld\n", k_uniq0);

  gc_header_t* f_uniq0;
  f_uniq0 = makeClosure(NULL, i_uniq1);

  ((makeClosure_c0_c0_funct)get_tuple_at(f_uniq0, 0))(f_uniq0);

  gc_unref(f_uniq0);
  gc_unref(main_func_call_flat0_uniq0);
}

#define RUNTIME_RESERVED_SIZE 4 * 1024 * 1024
#define COROUTINE_STACK_SIZE 1024 * 1024
#define NUM_COROUTINES 1
#define HEAP_SIZE 8 * 1024 * 1024
#define NUM_GC_HEADERS 10000

int main() {
  init_memory(RUNTIME_RESERVED_SIZE, COROUTINE_STACK_SIZE, NUM_COROUTINES,
              HEAP_SIZE);
  init_gc(NUM_GC_HEADERS);

  main_entry(NULL);

  print_gc_mem_stats();
  run_gc();
  print_gc_mem_stats();

  free_memory();

  return 0;
}
