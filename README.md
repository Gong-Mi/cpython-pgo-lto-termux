# cpython-pgo-lto-termux

在 Termux/aarch64(设备 rothko,Redmi K70 Ultra,D9300+)上验证:官方 Termux Python 3.14.6 未开 PGO/LTO/JIT,自构建 PGO+LTO 版本能快多少。

## 证据分层

1. **源码/构建配置**: sysconfig CONFIG_ARGS/CFLAGS(`evidence/*/00-config.txt`)
2. **二进制**: readelf/nm 检查 LTO/PGO 痕迹(profile 符号、段类型)
3. **运行时 A/B**: 同设备、同一 bench 脚本、A/B 交替轮询(round-robin)+ 中位数 + 几何平均,消除 dvfs/热漂移(`evidence/ab/`)
4. **独立第三方复核**: 通过 dahetao 代理(deepseek-v4.1-flash)交叉验证配置声称、方法论与数字一致性(`evidence/review/`)

## 构建

`build/cpython-pgo-lto-build.sh`(在本机后台执行,PGO profile-opt 两轮编译):
- CPython 3.14.6 源码,sha256 记录于 build.log
- `./configure --enable-optimizations --with-lto --with-system-ffi --with-system-expat`
- `make -j8 profile-opt`,安装到私有前缀 `~/opt/pgo-python-3.14.6`(不碰系统 `$PREFIX`)

## 结论

A/B 实测(15 轮交替,taskset 固定 core 5,中位数,设备 rothko / D9300+):

| 用例 | stock | PGO+LTO | B/A |
|---|---|---|---|
| float_loop (10万次) | 15.82 ms | 7.73 ms | 0.489 |
| call_overhead (单次) | 53.0 ns | 38.6 ns | 0.727 |
| list_comp (10万元素) | 15.84 ms | 10.00 ms | 0.631 |
| str_utf8 | 9.32 µs | 8.14 µs | 0.874 |
| json_roundtrip | 100.2 µs | 63.4 µs | 0.633 |
| regex | 760.2 µs | 627.2 µs | 0.825 |
| dict_build (10万项) | 19.23 ms | 11.58 ms | 0.602 |

**几何平均 B/A = 0.672,即 PGO+thin LTO 构建在这组纯 Python 微基准上约快 1.49 倍。**
收益最大的是解释器热循环(float_loop 2.05x);接近 C 扩展的用例(str_utf8)收益最小(1.14x),符合 PGO/LTO 主要优化解释器自身的机理。

适用边界:微基准以解释器热路径为主,不代表 I/O 密集、数值计算(numpy 走外部 BLAS)或启动延迟场景;第三方后台负载造成的共模尖峰在原始数据(evidence/ab/01-ab-result.txt raw_A/raw_B)中可见并已用中位数抑制。

## 构建/测试过程中的平台差异(非回归)

- `_posixshmem` 缺失:stub libc(API24)无 shm_open,构建脚本已加 `-landroid-shmem` 修复,本轮未重编。
- `test_time` 退出 PGO 语料:seccomp 拦 `clock_settime`(strace 实证 SIGSYS)。
- test_re/test_functools/test_base64 失败:stock Termux python 同样失败(平台继承)。
- make install 的 ensurepip 在 -j8 负载下 SIGABRT,单独重跑成功(环境性,非构建缺陷)。

## 独立第三方复核(dahetao 代理 deepseek-v4.1-flash)

见 evidence/review/(构建声称核验 / 方法论审计 / 数字复算)。
