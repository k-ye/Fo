#ifndef RUNTIME_TUPLE_H_
#define RUNTIME_TUPLE_H_

#include "runtime/gc_header.h"

typedef struct tuple {
  // number of elements in this tuple.
  // <= sizeof(size_t) * 8 (in this case, 64)
  size_t num;
  // mask whether each element needs gc
  // 1: needs gc
  // 0: trivially destructable
  size_t gc_mask;
  val_t* begin;
} tuple_t;

const obj_operators_t* get_tuple_operators();

gc_header_t* alloc_tuple(size_t num);
void set_tuple_at(gc_header_t* gt, int i, val_t val, bool needs_gc);
val_t get_tuple_at(gc_header_t* gt, int i);

#endif  // RUNTIME_TUPLE_H_