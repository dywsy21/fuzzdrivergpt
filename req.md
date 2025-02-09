# req

## 概述

拓展[fuzzdrivergpt](https://github.com/occia/fuzzdrivergpt.git) (一个用ai自动迭代生成可用的fuzz driver的工具，目前只支持生成C/C++代码的fuzzdriver)，使其能支持生成更多语言的fuzz driver。(fuzz driver: 模糊测试的驱动程序，用于调用模糊测试工具，如libfuzzer，afl等)

**最终目的**：提供一种自动化的方式，验证软件供应链中上游的漏洞是否能真正地传播到下游(通过实际触发出来)，有现成例子，如下：
![CVE-2023-49468的传播](fc0c5b9b7d2baa888e6ae7e2cbe1c0b.jpg)

这张图展示了一个js库是如何因为底层依赖了C/C++而触发了C/C++的内存漏洞的。

## fuzzdrivergpt概述

1. 在[SourceGraph](https://sourcegraph.com/search)这个网站上查找当前需要生成fuzz driver的这个库的函数的信息，作为prompt喂给ai
2. 拿回ai给出的fuzz driver，然后在本地验证其可用性，包括编译能不能过等。拓展到python，js等语言得重新考虑如何验证。(在docker容器内验证fuzz driver的可用性。所以想要拓展需要同样使用docker架构：[Fuzzer images](https://github.com/WiseSecurity/dockerized-fuzzers) 这个库可能用的上。)
3. 出现问题就喂回给ai重新生成，直到生成的fuzz driver可用为止。

## 分级目标

能做到的越多越好:D

### 对于js, 能调用下游函数后验证上游漏洞函数被触发了

可以对上游的那个目标函数打桩来验证其被call了。

### 对于js, 能调用下游函数后验证上游漏洞函数被触发了，并且进行模糊测试，真正触发了内存漏洞

拓展好fuzzdrivergpt，得到有效的fuzzdriver，然后在实际的模糊测试中触发漏洞。使用上图的例子即可。

几乎肯定需要使用address sanitizer。

### 对于js和python, 能调用下游函数后验证上游漏洞函数被触发了，并且在模糊测试中真正触发了内存漏洞

对于python再重复一遍上面的步骤。

