# PTorrent core — POSIX build.
#
# The core builds with a C compiler and libc alone. No SDK, no UI toolkit, no
# network library at this layer. If this Makefile ever needs a platform SDK to
# produce libptorrent, the layering has failed.
#
#   make            static + shared library, and the test binaries
#   make test       build and run the test suite
#   make static     libptorrent.a only
#   make shared     libptorrent.so only
#   make clean
#
# Cross-compiling is the normal case, not the exception:
#   make CC=aarch64-linux-android21-clang            (Android NDK)
#   make CC="xcrun -sdk iphoneos clang -arch arm64"  (iOS)
#   make CC=x86_64-w64-mingw32-gcc SHLIB=ptorrent.dll

CC      ?= cc
AR      ?= ar
PREFIX  ?= /usr/local

# -std=c99 rather than gnu99: the core must not acquire GNU extensions by
# accident, because MSVC and the iOS toolchain will not have them.
CFLAGS  ?= -std=c99 -O2 -g
CFLAGS  += -Iinclude -Isrc
CFLAGS  += -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion \
           -Wstrict-prototypes -Wmissing-prototypes -Wpointer-arith \
           -Wwrite-strings -Wcast-qual -Wvla
CFLAGS  += -fvisibility=hidden
LDLIBS  += -lm

SRC     := src/pt_core.c src/pt_util.c src/pt_json.c src/pt_jexpr.c \
           src/pt_sigma.c src/pt_ptfile.c src/pt_corpus.c
OBJ     := $(SRC:.c=.o)
PICOBJ  := $(SRC:.c=.pic.o)

STATIC  := libptorrent.a
SHLIB   ?= libptorrent.so

TESTSRC := $(wildcard tests/test_*.c)
TESTBIN := $(TESTSRC:.c=)

.PHONY: all static shared test clean install

all: static shared $(TESTBIN)

static: $(STATIC)
shared: $(SHLIB)

$(STATIC): $(OBJ)
	$(AR) rcs $@ $^

%.pic.o: %.c
	$(CC) $(CFLAGS) -DPT_BUILDING_SHARED -fPIC -c $< -o $@

$(SHLIB): $(PICOBJ)
	$(CC) -shared -o $@ $^ $(LDLIBS)

tests/test_%: tests/test_%.c $(STATIC)
	$(CC) $(CFLAGS) $< $(STATIC) -o $@ $(LDLIBS)

test: $(TESTBIN)
	@fail=0; \
	for t in $(TESTBIN); do \
	  if ./$$t; then :; else fail=1; fi; \
	done; \
	if [ $$fail -eq 0 ]; then \
	  printf '\n\033[32mall suites passed\033[0m\n'; \
	else \
	  printf '\n\033[31mFAILURES\033[0m\n'; exit 1; \
	fi

install: static shared
	install -d $(DESTDIR)$(PREFIX)/include $(DESTDIR)$(PREFIX)/lib
	install -m 644 include/ptorrent.h $(DESTDIR)$(PREFIX)/include/
	install -m 644 $(STATIC)          $(DESTDIR)$(PREFIX)/lib/
	install -m 755 $(SHLIB)           $(DESTDIR)$(PREFIX)/lib/

clean:
	rm -f $(OBJ) $(PICOBJ) $(STATIC) $(SHLIB) $(TESTBIN)
