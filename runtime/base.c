#include "runtime/base.h"

#include <execinfo.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

size_t roundup_aligned(size_t size) { return (size + 7) & (~((size_t)7)); }

void die(const char* format, ...) {
  va_list arg;

  va_start(arg, format);
  fprintf(stderr, format, arg);
  va_end(arg);

  abort();
}

void print_stack() {
  void* array[20];
  size_t size;

  // get void*'s for all entries on the stack
  size = backtrace(array, 20);

  // print out all the frames to stderr
  backtrace_symbols_fd(array, size, STDERR_FILENO);
  exit(1);
}