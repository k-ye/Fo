#ifndef RUNTIME_BASE_H_
#define RUNTIME_BASE_H_

#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// Can be either a copy of the primitive value, or the memory address of the
// more complex data structure.
typedef int64_t val_t;

size_t roundup_aligned(size_t size);

void die(const char* format, ...);

void print_stack();

#define LOG(...) printf(__VA_ARGS__)
#define ERRLOG(...) fprintf(stderr, __VA_ARGS__)

#define CHECK(b)                                                         \
  do {                                                                   \
    if ((bool)(b) == false) {                                            \
      fprintf(stderr, "[file:%s, line:%d] CHECK failed: %s\n", __FILE__, \
              __LINE__, #b);                                             \
      print_stack();                                                     \
      abort();                                                           \
    }                                                                    \
  } while (0)

// TODO: remove this once we finish debugging
#ifdef NDEBUG
#undef NDEBUG
#endif

#ifdef NDEBUG
#define DCHECK(b) ((void)0)
#define DLOG(...) ((void)0)
#else
#define DCHECK(b) CHECK(b)
#define DLOG(...) LOG(__VA_ARGS__)
#endif

#endif  // RUNTIME_BASE_H_