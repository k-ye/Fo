#include "runtime/gc.h"

#include <string.h>
#include "runtime/memory.h"

// Runtime memory

static char* memory_raw_begin_;
static intptr_t memory_begin_;

static size_t runtime_reserved_size_;
static intptr_t runtime_reserved_seg_begin_;
static intptr_t runtime_reserved_cur_;

static size_t per_stack_size_;
static intptr_t stacks_seg_begin_;

static size_t per_heap_size_;
static intptr_t heap_seg_begin_;
static intptr_t from_heap_seg_begin_;
static intptr_t to_heap_seg_begin_;

static intptr_t heap_cur_;
static intptr_t heap_end_;

void init_memory(size_t runtime_reserved_size, size_t stack_size,
                 int num_stacks, size_t heap_size) {
  runtime_reserved_size_ = roundup_aligned(runtime_reserved_size);
  per_stack_size_ = roundup_aligned(stack_size);
  per_heap_size_ = roundup_aligned(heap_size);

  size_t size = runtime_reserved_size_ + per_stack_size_ * num_stacks +
                heap_size * 2 + sizeof(val_t);
  memory_raw_begin_ = (char*)malloc(size);
  memory_begin_ = roundup_aligned((intptr_t)memory_raw_begin_);

  runtime_reserved_seg_begin_ = memory_begin_;
  runtime_reserved_cur_ = runtime_reserved_seg_begin_;

  stacks_seg_begin_ = runtime_reserved_seg_begin_ + runtime_reserved_size_;

  heap_seg_begin_ = stacks_seg_begin_ + per_stack_size_ * num_stacks;
  from_heap_seg_begin_ = heap_seg_begin_;
  to_heap_seg_begin_ = heap_seg_begin_ + per_heap_size_;
  heap_cur_ = from_heap_seg_begin_;
  heap_end_ = from_heap_seg_begin_ + per_heap_size_;
}

void free_memory() { free(memory_raw_begin_); }

char* stack_top(int stack_i) {
  intptr_t result = stacks_seg_begin_ + per_stack_size_ * (stack_i + 1);
  DCHECK(result <= heap_seg_begin_);
  return (char*)result;
}

char* stack_bottom(int stack_i) {
  intptr_t result = stacks_seg_begin_ + per_stack_size_ * stack_i;
  return (char*)result;
}

char* alloc_runtime_reserved(size_t size) {
  size = roundup_aligned(size);
  intptr_t result = runtime_reserved_cur_;
  intptr_t next = result + size;

  if (next > stacks_seg_begin_) {
    return NULL;
  }

  runtime_reserved_cur_ = next;
  return (char*)result;
}

char* alloc_heap(size_t size) {
  size = roundup_aligned(size);
  intptr_t result = heap_cur_;
  intptr_t next = result + size;
  if (next > heap_end_) {
    return NULL;
  }

  heap_cur_ = next;
  return (char*)result;
}

size_t heap_usage() { return heap_cur_ - from_heap_seg_begin_; }

// GC

static const int32_t NONTRIVIAL_ROOT_MASK = (1 << 31);
static const int32_t MARKED_AS_UNREACHABLE = (1 << 30);
static const int32_t MAX_REF_COUNT = (1 << 28);
static const int32_t REF_COUNT_MASK = (MAX_REF_COUNT - 1);

// An array containing |num_gc_headers_|
static size_t num_gc_headers_;
static gc_header_t* all_gc_headers;
static size_t num_gc_headers_in_use_;

static gc_header_t* gc_free;
static gc_header_t* gc_trivial_roots;
static gc_header_t* gc_nontrivial_roots;

static void gc_add_to_list(gc_header_t** list, gc_header_t* g) {
  gc_header_t* head = *list;
  if (head == NULL) {
    *list = g;
    return;
  }
  g->prev = NULL;
  g->next = head;
  head->prev = g;
  *list = g;
}

static void gc_remove_from_list(gc_header_t** list, gc_header_t* g) {
  if (g->prev) {
    g->prev->next = g->next;
  }
  if (g->next) {
    g->next->prev = g->prev;
  }
  if (*list == g) {
    *list = g->next;
  }
  g->prev = NULL;
  g->next = NULL;
}

static gc_header_t* gc_alloc_common(size_t size, const obj_operators_t* ops) {
  if (gc_free == NULL) {
    return NULL;
  }
  size = roundup_aligned(size);
  val_t* o = (val_t*)alloc_heap(size);
  if (o == NULL) {
    return NULL;
  }
  gc_header_t* g = gc_free;
  gc_free = gc_free->next;
  ++num_gc_headers_in_use_;

  memset((void*)o, 0, size);
  g->obj = o;
  g->ref_count = 1;
  g->meta_ref_count = 0;
  g->obj_ops = ops;
  g->prev = NULL;
  g->next = NULL;
  return g;
}

gc_header_t* gc_alloc_trivial(size_t size) {
  return gc_alloc_trivial_ops(size, get_trivial_obj_operators());
}

gc_header_t* gc_alloc_trivial_ops(size_t size, const obj_operators_t* ops) {
  gc_header_t* g = gc_alloc_common(size, ops);
  if (g == NULL) {
    return NULL;
  }

  g->meta_ref_count = 0;
  gc_add_to_list(&gc_trivial_roots, g);
  return g;
}

gc_header_t* gc_alloc_nontrivial(size_t size, const obj_operators_t* ops) {
  gc_header_t* g = gc_alloc_common(size, ops);
  if (g == NULL) {
    return NULL;
  }
  g->meta_ref_count = NONTRIVIAL_ROOT_MASK;
  gc_add_to_list(&gc_nontrivial_roots, g);
  return g;
}

static inline bool is_nontrivial_gc(const gc_header_t* g) {
  return ((g->meta_ref_count & NONTRIVIAL_ROOT_MASK) == NONTRIVIAL_ROOT_MASK);
}

static inline bool is_marked_unreachable(const gc_header_t* g) {
  return ((g->meta_ref_count & MARKED_AS_UNREACHABLE) == MARKED_AS_UNREACHABLE);
}

static inline int32_t get_shadow_ref_count(const gc_header_t* g) {
  return (g->meta_ref_count & REF_COUNT_MASK);
}

void gc_ref(gc_header_t* g) {
  g->ref_count += 1;
  CHECK(g->ref_count < MAX_REF_COUNT);
}

static void gc_dealloc(gc_header_t* g) {
  CHECK(g->ref_count == 0);

  g->obj = NULL;
  g->obj_ops = NULL;
  g->ref_count = 0;
  g->meta_ref_count = 0;
  // Move back to free list
  g->prev = NULL;
  g->next = gc_free;
  gc_free = g;
  --num_gc_headers_in_use_;
}

void gc_unref(gc_header_t* g) {
  CHECK(g->ref_count > 0);
  g->ref_count -= 1;

  if (g->ref_count == 0) {
    if (is_nontrivial_gc(g)) {
      gc_remove_from_list(&gc_nontrivial_roots, g);
    } else {
      gc_remove_from_list(&gc_trivial_roots, g);
    }
    g->obj_ops->gc_visitor(g->obj, gc_unref);
    gc_dealloc(g);
  }
}

void init_gc(size_t num_gc_headers) {
  num_gc_headers_ = num_gc_headers;
  all_gc_headers = (gc_header_t*)alloc_runtime_reserved(sizeof(gc_header_t) *
                                                        num_gc_headers_);
  if (all_gc_headers == NULL) {
    die("Cannot allocate memory for GC.");
  }
  for (int i = 0; i < num_gc_headers_; ++i) {
    gc_header_t* g = &all_gc_headers[i];
    g->obj = NULL;
    g->ref_count = 0;
    g->meta_ref_count = 0;
    g->obj_ops = NULL;
    g->prev = NULL;
    g->next = (g + 1);
  }
  gc_free = all_gc_headers;
  all_gc_headers[num_gc_headers_ - 1].next = NULL;

  gc_trivial_roots = NULL;
  gc_nontrivial_roots = NULL;

  num_gc_headers_in_use_ = 0;
}

static void swap_heap_space() {
  intptr_t from = from_heap_seg_begin_;
  from_heap_seg_begin_ = to_heap_seg_begin_;
  to_heap_seg_begin_ = from;

  heap_cur_ = from_heap_seg_begin_;
  heap_end_ = from_heap_seg_begin_ + per_heap_size_;
}

static void copy_refcount_to_shadow() {
  gc_header_t* g = gc_nontrivial_roots;
  for (; g != NULL; g = g->next) {
    int32_t ref_count = g->ref_count;
    CHECK(ref_count < MAX_REF_COUNT);
    g->meta_ref_count = (NONTRIVIAL_ROOT_MASK | ref_count);
    printf("copy_refcount_to_shadow, g=%p, nontrival: %d\n", g,
           g->meta_ref_count);
  }
}

static void visit_subtract_ref_count(gc_header_t* g) {
  if (is_nontrivial_gc(g)) {
    int32_t shadow_ref_count = get_shadow_ref_count(g);
    CHECK(shadow_ref_count > 0);
    shadow_ref_count -= 1;
    printf("visit_subtract_ref_count, g=%p, shadow_ref_count=%d\n", g,
           shadow_ref_count);
    g->meta_ref_count = (NONTRIVIAL_ROOT_MASK | shadow_ref_count);
  }
}

static void subtract_shadow_ref_count() {
  gc_header_t* g = gc_nontrivial_roots;
  for (; g != NULL; g = g->next) {
    g->obj_ops->gc_visitor(g->obj, visit_subtract_ref_count);
  }
}

static void visit_recover_ref_count(gc_header_t* g) {
  if (is_nontrivial_gc(g) && (get_shadow_ref_count(g) == 0)) {
    // |g|'s shadow ref count is zero, bump it up.
    g->meta_ref_count = (NONTRIVIAL_ROOT_MASK | 1);
    g->obj_ops->gc_visitor(g->obj, visit_recover_ref_count);
  }
}

static void find_unreachable() {
  gc_header_t* g = gc_nontrivial_roots;
  for (; g != NULL; g = g->next) {
    if (get_shadow_ref_count(g) > 0) {
      g->obj_ops->gc_visitor(g->obj, visit_recover_ref_count);
    }
  }

  g = gc_nontrivial_roots;
  for (; g != NULL; g = g->next) {
    if (get_shadow_ref_count(g) == 0) {
      g->meta_ref_count = (NONTRIVIAL_ROOT_MASK | MARKED_AS_UNREACHABLE);
      printf("g=%p, marked as unreachable\n", g);
    }
  }
}

static void gc_unref_if_reachable(gc_header_t* g) {
  if (is_marked_unreachable(g)) {
    return;
  }
  gc_unref(g);
}

static void dealloc_unreachable() {
  gc_header_t* g = gc_nontrivial_roots;
  for (; g != NULL; g = g->next) {
    if (is_marked_unreachable(g)) {
      g->obj_ops->gc_visitor(g->obj, gc_unref_if_reachable);
    }
  }

  g = gc_nontrivial_roots;
  while (g != NULL) {
    gc_header_t* next = g->next;
    if (is_marked_unreachable(g)) {
      gc_remove_from_list(&gc_nontrivial_roots, g);
      g->ref_count = 0;
      gc_dealloc(g);
    }
    g = next;
  }
}

static void copy_to_new_heap(gc_header_t* list) {
  gc_header_t* g = list;
  for (; g != NULL; g = g->next) {
    size_t size = g->obj_ops->get_bytes(g->obj);
    val_t* new_mem = (val_t*)alloc_heap(size);
    CHECK(new_mem != NULL);
    memcpy((void*)new_mem, (const void*)g->obj, size);
    g->obj = new_mem;
  }
}

void run_gc() {
  // process circular reference
  copy_refcount_to_shadow();
  subtract_shadow_ref_count();
  find_unreachable();
  dealloc_unreachable();
  // move to new space
  swap_heap_space();
  copy_to_new_heap(gc_trivial_roots);
  copy_to_new_heap(gc_nontrivial_roots);
}

size_t num_gc_headers_in_use() { return num_gc_headers_in_use_; }

// static int32_t TENTAIVE_UNREACHABLE_MASK = (1 << 30);
//
// static inline bool is_gc_tentative_unreachable(const gc_header_t* g) {
//   return ((g->ref_count.c[META_REF_COUNT] & TENTAIVE_UNREACHABLE_MASK) ==
//           TENTAIVE_UNREACHABLE_MASK);
// }
//
// static void move_unreachable() {
//   gc_header_t* g = gc_nontrivial_roots;
//   while (g != NULL) {
//     gc_header_t* next;
//     int32_t shadow_ref_count = get_shadow_ref_count(g);
//     if (shadow_ref_count == 0) {
//       next = g->next;
//       gc_remove_from_list(&gc_nontrivial_roots, g);
//       gc_add_to_list(&gc_unreachable, g);
//       g->ref_count.c[META_REF_COUNT] =
//           (NONTRIVIAL_ROOT_MASK | TENTAIVE_UNREACHABLE_MASK);
//     } else {
//       g->obj_ops->gc_visitor(g->obj, visit_recover_ref_count);
//       next = g->next;
//     }
//     g = next;
//   }
// }