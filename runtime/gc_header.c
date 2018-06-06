#include "runtime/gc_header.h"

static size_t trivial_obj_get_bytes(val_t* o) { return sizeof(val_t); }
static void trivial_obj_gc_visitor(val_t* o, gc_visit_func visit) {}

const obj_operators_t* get_trivial_obj_operators() {
  static obj_operators_t ops = {.get_bytes = trivial_obj_get_bytes,
                                .gc_visitor = trivial_obj_gc_visitor};
  return &ops;
}