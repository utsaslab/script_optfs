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

#### Run the Converted Library ####
Download the` OptFS VM`: [Link to VM](http://pages.cs.wisc.edu/~vijayc/optfs-vm.tar.gz).
It's already setup, so you just need to install the dependencies for the covnerted library, compile it, and then benchmark it to observe the performance difference.

By Subrat Mainali and Tom Gong, undergrads at UT Austin.Authors: Tom Gong and Subrat Mainali

### Overview of the Tool ###
This tool makes multiple parses of the library directory (pull request with imporevement welcome).
In every parse, it tries to determine a function that is an `fsync_wrapper`, a function that is either `fsync` or eventually calls `fsync`, by parsing down the AST nodes.
Once it has determined all the `fsync_wrappers` in the library directory, it goes through every `fsync_wrapper` AST node and generates two versions of functions (and the associated function declarations) for every `fsync_wrapper`.
1. The first type of function is called an osync definition, and it's simply the function name prepended with `osync_`. The definition on this function is also different in that all the `fsync_wrappers` that are called inside this function are changed so they call the osync wrapper of their functions instead. So, for instance, this:
```C
void foo() {
  bar1();  // bar1 is an fsync wrapper
  bar2();  // bar2 is an fsync wrapper
}

```
would get a second function definition:
```C
void osync_foo() {
  osync_bar1();
  osync_bar2();
}
```
2. The second type of function is called a dsync definition and it's simply the function name prependied with `dsync_`
In this case, all the function calls inside the function definition are converted to `osync`, except the last one, which is converted to `dsync`. So, for instance, this:
```C
void foo() {
  bar1();  // bar1 is an fsync wrapper
  bar2();  // bar2 is an fsync wrapper
}

```
would get a second function definition:
```C
void dsync_foo() {
  osync_bar1();  // bar1 is an fsync wrapper
  dsync_bar2();  // bar2 is an fsync wrapper
}

```
3. Special case of `fsync`: Since `fsync` is an `fsync_wrapper` too, it must get its own version of osync definition and dsync definition. And it does! The osync definition of `fsync` is called `osync` and it's a system call that guarantees order and eventual durability. The dsync definition of `fsync` is called `dsync` and it's a system call that guaratess immediate durability (blocks). For more details, check the Optimistic Crash Cosnsistency paper linked above.
### Safety of the Script_Optfs ###
The script is safe in most cases, but there certainly are cases we don't account for.
This script can deal with scope, so you can have functions with the same name in multiple files, as long as more than one of those functions doesn't have external linkage, our script will take care it. We went through great lengths to ensure that.
However, cases where a switch statement is used, like the following:
```C
function foo(fd1, fd2, expression) {
  switch (expression) {
    case 1:
      fsync(fd1);
      break;
    case 2:
     fsync(fd2);
     break;
    default:
      fsync(fd1);
      fsync(fd2);
  }
 }
```
would get converted to the following:
```C
function osync_foo(fd1, fd2, expression) {      /* this definition is correct */
  switch (expression) {
    case 1:
      osync(fd1);
      break;
    case 2:
     osync(fd2);
     break;
    default:
      osync(fd1);
      osync(fd2);
  }
 }
 
function dsync_foo(fd1, fd2, expression) {      /* this definition isn't corrrect */
switch (expression) {
  case 1:
    osync(fd1);                      
    break;                        /* this function is a dsync definition, yet it doesn't ever call dsync if case 1 is called */
  case 2:
   osync(fd2);
   break;                         /* same in this case, dsync definitions should call dsync before they return */
  default:
    osync(fd1);
    dsync(fd2);                   /* only in this case will dsync actually be invoked before the function returns */
  }
 }
```
### Authors ###
Tom Gong (tom.gong@utexas.edu) and Subrat Mainali (mainali.subrat@utexas.edu)

Under [Dr. Vijay Chidambaram](http://www.cs.utexas.edu/~vijay/), UT Austin.
