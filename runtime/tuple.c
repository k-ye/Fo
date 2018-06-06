#include "runtime/tuple.h"
#include "runtime/gc.h"

static size_t tuple_bytes_by_num(size_t num) {
  return (sizeof(size_t) * 2) + sizeof(val_t*) + (sizeof(val_t) * num);
}

static size_t tuple_get_bytes(val_t* o) {
  tuple_t* t = (tuple_t*)o;
  return tuple_bytes_by_num(t->num);
}

static void tuple_gc_visitor(val_t* o, gc_visit_func visit) {
  tuple_t* t = (tuple_t*)o;
  size_t gc_mask = t->gc_mask;
  val_t* begin = t->begin;
  for (int i = 0; i < t->num; ++i) {
    if (gc_mask & 1) {
      visit((gc_header_t*)begin[i]);
    }
    gc_mask >>= 1;
  }
}

const obj_operators_t* get_tuple_operators() {
  static obj_operators_t ops = {.get_bytes = tuple_get_bytes,
                                .gc_visitor = tuple_gc_visitor};
  return &ops;
}

gc_header_t* alloc_tuple(size_t num) {
  size_t size_bytes = tuple_bytes_by_num(num);
  gc_header_t* gc_t = gc_alloc_nontrivial(size_bytes, get_tuple_operators());
  if (gc_t != NULL) {
    tuple_t* t = (tuple_t*)gc_t->obj;
    t->num = num;
    t->gc_mask = 0;
    t->begin = (val_t*)(((char*)t) + tuple_bytes_by_num(0));
  }
  return gc_t;
}

void set_tuple_at(gc_header_t* gt, int i, val_t val, bool needs_gc) {
  tuple_t* t = GC_TO_OBJ(tuple_t, gt);
  CHECK((0 <= i) && (i < t->num));
  size_t mask_i = (1 << i);
  if (needs_gc) {
    gc_header_t* g = (gc_header_t*)val;
    gc_ref(g);
    t->gc_mask |= mask_i;
  } else {
    mask_i = (~mask_i);
    t->gc_mask &= mask_i;
  }
  t->begin[i] = val;
}

val_t get_tuple_at(gc_header_t* gt, int i) {
  tuple_t* t = GC_TO_OBJ(tuple_t, gt);
  CHECK((0 <= i) && (i < t->num));
  return t->begin[i];
}

val_t* get_tuple_addr_at(tuple_t* t, int i) {
  CHECK((0 <= i) && (i < t->num));
  return &(t->begin[i]);
}