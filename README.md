# Script_Optfs #
### What is Script_Optfs? ###
Script_Optfs is a conversion tool, capable of converting libraries that use `fsync` pessimistically to be compatible with the Optimistic File System ([OptFS](https://github.com/utsaslab/optfs)). 
OptFS is a linux-ext4 variant that implements [Optimistic Crash Consistency](http://research.cs.wisc.edu/adsl/Publications/optfs-sosp13.pdf) which essentially makes the same level of guarantee as Pessimistic Crash Consistency (`fsync()` after every write) with sometimes the same speed as Probabilistic Crash Consistency (never calling `fsync()`).

This means that you can easily speed up the writes in your program by switching to OptFS and running Script_Optfs on the libraries that are in charge of persistence.

### Getting Setup ###
#### Script Dependencies ####
The only dependency for this script besides `Python2.7` is `LLVM` with clang bindings. You need to make sure you have LLVM source code on your computer, and then compile it yourself. 
##### Installing LLVM #####
1. Run the following script after fixing the path, if necessary, to [Install Ninja](https://github.com/JDevlieghere/dotfiles/blob/master/installers/ninja.sh)
1. Then, run this script to actually get the `LLVM` source code. [LLVM](https://github.com/JDevlieghere/dotfiles/blob/master/installers/llvm.sh)

#### Running the Script_Optfs ####
1. Go to the script source, `script.py`, and then modify the `set_library_path` variable to your path to LLVM's `/build/lib`.
Once that is done, you might need to set an environmental variable, if the compiler throws you an error, otherwise, you are done and the script can be run.
1. To run the script, you just type `python script.py /path/to/library` and the script should run and modify everything in a new directory `<library_name>_`.
That's it!

#### Setting Up a VM ####
Download the` OptFS VM`: [Link to VM](http://pages.cs.wisc.edu/~vijayc/optfs-vm.tar.gz).
It's already setup, so you just need to install the dependencies for the covnerted library, compile it, and then benchmark it to observe the performance difference.

By Subrat Mainali and Tom Gong, undergrads at UT Austin.
