#ifndef RUNTIME_GC_HEADER_H_
#define RUNTIME_GC_HEADER_H_

#include "runtime/base.h"

struct gc_header;
struct obj_operators;

#define GC_HEAD_FIELDS                 \
  val_t* obj;                          \
  const struct obj_operators* obj_ops; \
  struct gc_header* prev;              \
  struct gc_header* next;              \
  int32_t ref_count;                   \
  int32_t meta_ref_count;

typedef struct gc_header {
  GC_HEAD_FIELDS
} gc_header_t;

// typedef void (*obj_destructor)(val_t*);
typedef size_t (*obj_bytes_getter)(val_t*);
typedef void (*gc_visit_func)(gc_header_t*);
typedef void (*obj_gc_visitor)(val_t*, gc_visit_func);

typedef struct obj_operators {
  obj_bytes_getter get_bytes;
  // a bunch of gc related operators
  obj_gc_visitor gc_visitor;
} obj_operators_t;

const obj_operators_t* get_trivial_obj_operators();

#define GC_TO_OBJ(type, g) ((type*)((g)->obj))
#define GC_TO_FUNC_PTR(func_type, g) ((func_type)((g)->obj))

#endif  // RUNTIME_GC_HEADER_H_