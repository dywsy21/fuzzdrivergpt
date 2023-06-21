#!/bin/bash



##########
## Before compile, you can modify build.sh for eaiser preparation here
##########
# install libclang for our python usage, do this for all oss-fuzz projects
pip3 install libclang
export MAKEFLAGS="-j`nproc`"
set -eux
# FILL HERE
#while true
#do
#	sleep 1h
#done

cat >> /src/build.sh << 'EOF'

cd /src/libpcap
# build project
mkdir build1
cd build1
cmake --install-prefix=/src/libpcap/fuzzdrivergpt-install  ..
make -j$(nproc) install

EOF
set +eux

#
# do what should be done in build_fuzzers command
#
compile
#
#
#

##########
## After compile, you can prepare the include/lib staff here
##########

set -eux

##########
# UNCOMMENT this for manual exploration on how to write this fuzzdrivergpt_build.sh
# COMMENT this for testing the real logic of fuzzdrivergpt_build.sh
##########


INSTALL=/root/workspace/fuzzdrivergpt/install
mkdir -p ${INSTALL}
# copy the headers to /root/workspace/fuzzdrivergpt/install/include
cp -r /src/libpcap/fuzzdrivergpt-install/include ${INSTALL}/include

# copy the libs to /root/workspace/fuzzdrivergpt/install/lib
cp -r /src/libpcap/fuzzdrivergpt-install/lib ${INSTALL}/lib
