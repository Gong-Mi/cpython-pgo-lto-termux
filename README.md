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

最终 A/B(主指标=进程 CPU 时间 time.process_time,ABBA 交替顺序,15 轮,taskset 固定 core 5,设备 rothko / D9300+,测试时存在间歇第三方后台负载):

| 用例 | stock CPU | PGO+LTO CPU | B/A |
|---|---|---|---|
| float_loop (10万次) | 12.77 ms | 7.00 ms | 0.548 |
| call_overhead (单次) | 47.2 ns | 32.9 ns | 0.698 |
| list_comp (10万元素) | 13.67 ms | 7.72 ms | 0.565 |
| str_utf8 | 8.37 µs | 6.63 µs | 0.792 |
| json_roundtrip | 88.2 µs | 51.4 µs | 0.583 |
| regex | 645.5 µs | 528.9 µs | 0.819 |
| dict_build (10万项) | 16.28 ms | 9.95 ms | 0.611 |

**几何平均 B/A = 0.652,bootstrap 95% CI [0.642, 0.662](10000 次重采样),CI 不含 1.0 → 差异显著。**
安慰剂 A/A 对照(同法):geomean 1.014,CI [0.984, 1.039] 含 1.0 → 测量系统无位置偏置,噪声底约 ±3%。
即:PGO+thin LTO 构建在这组 CPU-bound 紧循环微基准上 **CPU 消耗约为 stock 的 65%,约 1.53 倍效率**。

诚实边界(采纳 review2 意见):
- 紧循环形态对 PGO 的代码布局/冷热分离收益最友好,这组数字应视为**收益上界**而非典型应用加速比;真实程序(分支多、调用图深)收益通常更小。
- json/regex/str_utf8 主要在 C 扩展内执行,等权几何平均混入了"C 扩展构建质量"成分;纯解释器循环(float_loop/list_comp/dict_build)B/A 约 0.55-0.61。
- 单进程单线程单核结论,不推论并发/IO/启动场景。
- 墙钟时间版本(v1,ABAB 顺序)结果见 evidence/ab/01/03-v1,结论方向一致(0.672)。

## 构建/测试过程中的平台差异(非回归)

- `_posixshmem` 缺失:stub libc(API24)无 shm_open,构建脚本已加 `-landroid-shmem` 修复,本轮未重编。
- `test_time` 退出 PGO 语料:seccomp 拦 `clock_settime`(strace 实证 SIGSYS)。
- test_re/test_functools/test_base64 失败:stock Termux python 同样失败(平台继承)。
- make install 的 ensurepip 在 -j8 负载下 SIGABRT,单独重跑成功(环境性,非构建缺陷)。

## 独立第三方复核(dahetao 代理 deepseek-v4.1-flash)

见 evidence/review/。三轮独立复核均指出真实问题并已处置:
1. **构建声称核验**:指出"最终产物无插桩符号"不可判别 PGO 是否被消费 → 已补判别器 c 差分实验(ceval.o 带/不带 profile 编译产物不同,profile 确被消费),见 evidence/pgo-lto/01-pgo-consumption.txt。
2. **方法论审计**:指出紧循环形态高估收益、缺安慰剂与 CI、应改用 CPU 时间 → 已全部采纳(主指标改 CPU 时间、ABBA、安慰剂 A/A、bootstrap CI、边界声明)。
3. **数字复算**:独立复算墙钟版 geomean 与发起方一致(0.6715),算术平均>几何平均方向正确。
