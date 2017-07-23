# Script_Optfs #
### What is Script_Optfs? ###
Script_Optfs is a conversion tool, capable of converting libraries that use `fsync` pessimistically to be compatible with the Optimistic File System ([OptFS](https://github.com/utsaslab/optfs)). OptFS is a linux ext4 variant that implements [Optimistic Crash Consistency](http://research.cs.wisc.edu/adsl/Publications/optfs-sosp13.pdf) which essentially makes the same level of guarantee as Pessimistic Crash Consistency (`fsync()` after every write) with sometimes the same speed as Probabilistic Crash Consistency (never calling `fsync()`).

Converts libraries to be compatible with OptFS.
Pull requests welcome.

By Subrat Mainali and Tom Gong, undergrads at UT Austin.
Makes use of LLVM Python bindings.
