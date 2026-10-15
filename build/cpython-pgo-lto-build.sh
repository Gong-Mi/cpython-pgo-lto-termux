#!/data/data/com.termux/files/usr/bin/bash
# Build PGO+LTO CPython 3.14.6 natively on Termux/aarch64 (rothko, D9300+)
# Evidence-first: every stage logs to build.log; failures stop the script.
set -euo pipefail

HOME_D=/data/data/com.termux/files/home
WORK=$HOME_D/build/cpython-pgo-lto
SRC=Python-3.14.6
TARBALL=Python-3.14.6.tar.xz
URL=https://www.python.org/ftp/python/3.14.6/$TARBALL
PREFIX=$HOME_D/opt/pgo-python-3.14.6
LOG=$WORK/build.log

mkdir -p "$WORK" && cd "$WORK"
: > "$LOG"

step() { echo "=== [$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

step "download source"
if [ ! -f "$TARBALL" ]; then
  curl -fSL --retry 3 -o "$TARBALL" "$URL" 2>&1 | tail -2 | tee -a "$LOG"
fi
echo "$(sha256sum $TARBALL)" | tee -a "$LOG"

step "memfd_create stub (ndk-multilib stub libc lacks it; clang_rt.builtins references it)"
cat > "$WORK/memfd_stub.c" <<'EOF'
/* ndk-multilib stub libc (API24) has no memfd_create wrapper, but
   clang_rt.builtins (clang23) and CPython's posixmodule reference it.
   Device is Android 16: implement via raw syscall. */
#include <sys/syscall.h>
#ifndef __NR_memfd_create
#define __NR_memfd_create 279 /* aarch64 */
#endif
extern long syscall(long number, ...);
int memfd_create(const char *name, unsigned int flags) {
    return (int) syscall(__NR_memfd_create, name, flags);
}
EOF
clang -O2 -c "$WORK/memfd_stub.c" -o "$WORK/memfd_stub.o"

step "extract"
rm -rf "$SRC"
tar xf "$TARBALL"

step "toolchain versions"
clang --version | head -1 | tee -a "$LOG"
lld --version 2>/dev/null | head -1 | tee -a "$LOG" || true

cd "$SRC"

step "configure (PGO + thin LTO)"
./configure \
  --prefix="$PREFIX" \
  --enable-optimizations \
  --with-lto \
  --with-system-expat \
  --enable-loadable-sqlite-extensions \
  CC=clang \
  CFLAGS="-O3 -fstack-protector-strong" \
  LIBS="$WORK/memfd_stub.o -landroid-shmem" \
  ac_cv_search_shm_open="-landroid-shmem" \
  2>&1 | tail -5 | tee -a "$LOG"

step "make profile-opt -j8 (this is the long stage)"
# test_time is excluded: clock_settime is blocked by Android seccomp (SIGSYS kill),
# verified via strace (si_syscall=__NR_clock_settime). Other failures
# (test_re/test_functools/test_base64) reproduce on stock Termux python.
make -j8 profile-opt PROFILE_TASK="-m test --pgo --timeout=1200 -x test_time || true" 2>&1 | tail -20 | tee -a "$LOG"

step "install to private prefix (NOT \$PREFIX)"
make install 2>&1 | tail -5 | tee -a "$LOG"

step "build evidence"
"$PREFIX/bin/python3" -VV | tee -a "$LOG"
"$PREFIX/bin/python3" -c "import sysconfig; c=sysconfig.get_config_vars(); print('CFLAGS =', c['CFLAGS']); print('CONFIG_ARGS has optimizations:', '--enable-optimizations' in c['CONFIG_ARGS'])" | tee -a "$LOG"
readelf -h "$PREFIX/lib/libpython3.14.so" | grep Type | tee -a "$LOG"
nm "$PREFIX/lib/libpython3.14.so" 2>/dev/null | grep -c llvm_profile | tee -a "$LOG" || true
ls -la "$PREFIX/lib/libpython3.14.so" | tee -a "$LOG"

step "DONE"
