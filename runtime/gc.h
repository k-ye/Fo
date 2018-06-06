#ifndef RUNTIME_GC_H_
#define RUNTIME_GC_H_

#include "runtime/base.h"
#include "runtime/gc_header.h"
#include "runtime/memory.h"

gc_header_t* gc_alloc_trivial(size_t size);
gc_header_t* gc_alloc_trivial_ops(size_t size, const obj_operators_t* ops);
gc_header_t* gc_alloc_nontrivial(size_t size, const obj_operators_t* ops);

void gc_ref(gc_header_t* g);
void gc_unref(gc_header_t* g);

void init_gc(size_t num_gc_headers);
void run_gc();
size_t num_gc_headers_in_use();

#endif  // RUNTIME_GC_H_