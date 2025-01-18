#!/bin/bash



##########
## Before compile, you can modify build.sh for eaiser preparation here
##########
# install libclang for our python usage, do this for all oss-fuzz projects
# make sure pip3 is installed
if ! command -v pip3 &> /dev/null; then
    apt-get update && apt-get install -y python3-pip
fi

# install libclang
pip3 install libclang==15.0.6.1 -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple



export MAKEFLAGS="-j`nproc`"
set -eux
# FILL HERE
cat >> /src/build.sh << 'EOF'

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
#while true
#do
#	sleep 1h
#done


#INSTALL=/root/workspace/fuzzdrivergpt/install
#mkdir -p ${INSTALL}
## copy the headers to /root/workspace/fuzzdrivergpt/install/include
#cp -r /src/libyaml/fuzzdrivergpt-install/include ${INSTALL}/include
#
## copy the libs to /root/workspace/fuzzdrivergpt/install/lib
#cp -r /src/libyaml/fuzzdrivergpt-install/lib ${INSTALL}/lib
