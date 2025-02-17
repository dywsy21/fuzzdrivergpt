#!/bin/bash
set -e

# 基础配置
INSTALL_DIR="${HOME}/opt/heif_stack"  # 自定义安装路径
CPU_CORES=$(nproc)
export PKG_CONFIG_PATH="${INSTALL_DIR}/lib/pkgconfig:${PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="${INSTALL_DIR}/lib:${LD_LIBRARY_PATH}"
export PATH="${INSTALL_DIR}/bin:${PATH}"

# 创建安装目录
mkdir -p ${INSTALL_DIR} ${INSTALL_DIR}/src
cd ${INSTALL_DIR}/src

# 1. 编译安装libde265
echo "Building libde265..."
wget https://github.com/strukturag/libde265/releases/download/v1.0.15/libde265-1.0.15.tar.gz
tar xzf libde265-1.0.15.tar.gz
cd libde265-1.0.15
./configure \
  --prefix=${INSTALL_DIR} \
  --disable-dec265 \
  --disable-sherlock265
make -j${CPU_CORES}
make install
cd ..

# 2. 编译安装 libheif（需手动去掉CMakeLists.txt的-Werror选项）
git clone https://github.com/strukturag/libheif.git
cd libheif
mkdir build && cd build
# 暂停等待用户修复-Werror问题
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

# 3. 安装Python环境
python -m pip install --user virtualenv
python -m virtualenv ${INSTALL_DIR}/venv
source ${INSTALL_DIR}/venv/bin/activate

# 4. 安装Pillow（不启用HEIF支持）
echo "Installing Pillow..."
pip install wheel
pip install pillow  # 不启用原生HEIF支持

# 5. 安装pillow-heif并链接到libheif
echo "Building pillow-heif..."
export PILLOW_HEIF_FORCE_BUILD=1
# 传递libheif的头文件和库路径
export HEIF_INCLUDE_DIR="${INSTALL_DIR}/include"
export HEIF_LIBRARY="${INSTALL_DIR}/lib/libheif.so"
CFLAGS="-I${HEIF_INCLUDE_DIR}" LDFLAGS="-L${INSTALL_DIR}/lib" pip install pillow-heif

# 验证安装
echo "Verification:"
python -c "
from PIL import Image, features
import pillow_heif

print('Pillow HEIF support:', features.check('heif'))
heif_file = pillow_heif.open_heif('example.heif') if features.check('heif') else None
if heif_file:
    print('HEIF dimensions:', heif_file.size)
else:
    print('HEIF support not enabled')
