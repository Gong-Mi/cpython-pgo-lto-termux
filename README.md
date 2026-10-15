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

(待 A/B 完成后填写)
