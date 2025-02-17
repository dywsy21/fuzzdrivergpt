#!/bin/bash
set -e

export INSTALL_DIR="$HOME/local-asan"
export ASAN_OPTIONS="detect_leaks=1:halt_on_error=0"
export UBSAN_OPTIONS="print_stacktrace=1"
export CC=gcc
export CXX=g++
export CFLAGS="-fsanitize=address -fno-omit-frame-pointer -O1 -g"
export CXXFLAGS="-fsanitize=address -fno-omit-frame-pointer -O1 -g"
export LDFLAGS="-fsanitize=address"

mkdir -p $INSTALL_DIR

# 1. 编译libde265（autotools）
git clone https://github.com/strukturag/libde265.git
cd libde265
./autogen.sh
# 显式传递LDFLAGS防止自动去除sanitize参数
./configure --prefix=$INSTALL_DIR \
            LDFLAGS="$LDFLAGS -Wl,--no-as-needed" \
            --disable-dec265 \
            --disable-sherlock265
make -j$(nproc) V=1  # V=1显示详细编译命令
make install
cd ..

# 2. 编译安装 libheif（需手动去掉CMakeLists.txt的-Werror选项）
git clone https://github.com/strukturag/libheif.git
cd libheif
mkdir build && cd build
while true; do
    echo "Have you fixed the -WError issue? (y/n)"
    read answer
    case $answer in
        [Yy]* ) break;;
        [Nn]* ) continue;;
        * ) echo "Please answer y or n.";;
    esac
done
cmake .. -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR \
         -DCMAKE_PREFIX_PATH=$INSTALL_DIR \
         -DWITH_DE265=ON \
         -DBUILD_SHARED_LIBS=ON \
         -DCMAKE_C_FLAGS="-Wall -Wextra -Wpedantic -Wshadow $CFLAGS" \
         -DCMAKE_CXX_FLAGS="-Wall -Wextra -Wpedantic -Wshadow $CXXFLAGS" \
         -DCMAKE_EXE_LINKER_FLAGS="$LDFLAGS" \
         -DCMAKE_SHARED_LINKER_FLAGS="$LDFLAGS"
make -j$(nproc)
make install
cd ../..

# 3. 编译libvips（Meson）
sudo apt install -y glib-2.0-dev gobject-introspection libexif-dev
git clone https://github.com/libvips/libvips.git
cd libvips
# Meson专用sanitize配置
meson setup build --prefix=$INSTALL_DIR \
                  -Db_sanitize=address \
                  -Dcpp_args="$CXXFLAGS" \
                  -Dc_args="$CFLAGS" \
                  --buildtype=debugoptimized
cd build
ninja -v  # 显示详细编译命令
meson install
cd ../..

# 4. 安装sharp（Node.js插件）
# 配置Node.js环境
export SHARP_IGNORE_GLOBAL_LIBVIPS=1
export npm_config_build_from_source=true
# export NODE_OPTIONS="--require=/usr/lib/gcc/x86_64-linux-gnu/13/libasan.so"  # 根据实际路径调整
unset NODE_OPTIONS  # 删除之前设置的--require参数


# 创建测试项目
mkdir sharp-test && cd sharp-test
npm init -y

# 在package.json中添加编译配置
cat << EOF > binding.gyp
{
  "targets": [{
    "target_name": "sharp",
    "cflags": ["$CFLAGS"],
    "ldflags": ["$LDFLAGS"]
  }]
}
EOF

# 安装sharp并链接自定义libvips
npm install sharp --prefix=$INSTALL_DIR \
                  --nodedir=$(dirname $(which node))/include/node \
                  --sharp-libvips=$INSTALL_DIR
