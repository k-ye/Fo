#include "runtime/memory.h"

static char* memory_raw_begin_;
static intptr_t memory_begin_;

static intptr_t runtime_reserved_seg_begin_;
static intptr_t runtime_reserved_cur_;

static intptr_t stacks_seg_begin_;
static size_t per_stack_size_;

static intptr_t heap_seg_begin_;
static intptr_t heap_cur_;
static intptr_t heap_seg_end_;

void init_memory(size_t runtime_reserved_size, size_t per_stack_size,
                 int num_stacks, size_t heap_size) {
  runtime_reserved_size = roundup_aligned(runtime_reserved_size);
  per_stack_size_ = roundup_aligned(per_stack_size);
  heap_size = roundup_aligned(heap_size);

  size_t size =
      runtime_reserved_size + per_stack_size_ * num_stacks + heap_size + 8;
  memory_raw_begin_ = (char*)malloc(size);
  memory_begin_ = roundup_aligned((intptr_t)memory_raw_begin_);

  runtime_reserved_seg_begin_ = memory_begin_;
  runtime_reserved_cur_ = runtime_reserved_seg_begin_;

  stacks_seg_begin_ = runtime_reserved_seg_begin_ + runtime_reserved_size;

  heap_seg_begin_ = stacks_seg_begin_ + per_stack_size_ * num_stacks;
  heap_cur_ = heap_seg_begin_;
  heap_seg_end_ = heap_seg_begin_ + heap_size;
}

void free_memory() { free(memory_raw_begin_); }

char* runtime_reserved_begin() { return (char*)runtime_reserved_seg_begin_; }

char* stack_top(int stack_i) {
  intptr_t result = stacks_seg_begin_ + per_stack_size_ * (stack_i + 1);
  if (result <= heap_seg_begin_) {
    return (char*)result;
  }
  return NULL;
}

char* stack_bottom(int stack_i) {
  intptr_t result = stacks_seg_begin_ + per_stack_size_ * stack_i;
  return (char*)result;
}

char* heap_begin() { return (char*)heap_seg_begin_; }

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
  if (next > heap_seg_end_) {
    return NULL;
  }

  heap_cur_ = next;
  return (char*)result;
}

size_t heap_usage() { return heap_cur_ - heap_seg_begin_; }
