#!/usr/bin/env python
""" Usage: call with <filename>
"""

import os
import re
import sys
import string
import clang.cindex
from subprocess import call
import shutil, errno

foi = ["printf"]                    # List of functions that affect osync/dsync placement

fsync_wrappers = {}                 # { (str) filepath + "_" + function_name : pointer to AST node }
fsync_lines = {}                    # { (str) filepath + "_" + function_name : [ function call nodes ] }
file_functions = {}                 # { (str) filepath : [ (str) function_name ] }
modified_funcs = {}                 # { (str) filepath : { (str) function_implementation : start line number } }
modified_fwd_decls = {}             # { (str) filepath : [ (str) forward_declaration ] }

# Benchmarking variables
osyncs = 0
dsyncs = 0
osync_wrappers = 0
dsync_wrappers = 0

# Find all lines in fsync_wrappers where fsync_wrappers are called
def W():

    # for every file
    for filepath in file_functions.keys():

        # for every fsync_wrapper in the file
        for func_name in file_functions[filepath]:

            # find the lines where fsync_wrapper function calls occur
            key = filepath + "_" + func_name
            node = fsync_wrappers[key]
            fsync_lines[key] = find_fsync_lines(node)


# Traverse the AST tree and find all functions that eventually call fsync
def find_fsync_wrappers(filename, node):

    fsync_found = False

    # Recurse for children of this node
    for child in node.get_children():
        found = find_fsync_wrappers(filename, child)

        # If one of the children eventually calls fsync,
        # set fsync_found to true so that the node can be added
        # to fsync_wrappers.
        if found:
            fsync_found = True

    # Add the function to fsync_wrappers and file_functions
    if fsync_found & (node.kind == clang.cindex.CursorKind.FUNCTION_DECL):

    	# create {[file]_[function] -> [AST node]} association
    	key = filename + '_' + node.spelling
        fsync_wrappers[key] = node

        file_functions[filename].append(node.spelling)

    # If this node is an function call and the
    # function being called is an fsync_wrapper, set fsync_found to True.
    if node.kind == clang.cindex.CursorKind.CALL_EXPR:
        if is_fsync_wrapper(node) or node.spelling == "fsync":

            fsync_found = True
            #print 'Found %s [line=%s, col=%s]' % (
            #    node.displayname, node.location.line, node.location.column)

    return fsync_found


# Finds all fsync_wrappers in a file
def X(filename, node):

    # Keep calling find_fsync_wrappers() until no more have been added
    before_size = len(fsync_wrappers)
    file_functions[filename] = []
    find_fsync_wrappers(filename, node)
    after_size = len(fsync_wrappers)

    while (before_size < after_size):
        before_size = after_size
        find_fsync_wrappers(filename, node)
        after_size = len(fsync_wrappers)


# Do fsync_wrapper lookup for every file in project
def Y(files):

    for filename in files:

        tu = index.parse(filename)

        # Compile a list of all functions that eventually call fsync
        X(filename, tu.cursor)

        print(filename)
        print(len(fsync_wrappers.keys()))
        print("")


# Find all fsync_wrappers across all files in a project
def Z(files):

    # Keep calling Y() until no more fsync_wrappers have been added
    before_size = len(fsync_wrappers)
    Y(files)
    after_size = len(fsync_wrappers)

    while(before_size < after_size):
        before_size = after_size
        Y(files)
        after_size = len(fsync_wrappers)

# tells if a function is an fsync wrapper
def is_fsync_wrapper(node):

    # this fancy ding-a-doodle is needed to get the location of a node
    if node.referenced is None:
        return False

    node_data = node.referenced.location.__repr__().split(',')
    func_name = node.spelling
    filepath = node_data[0].split('\'')[1]

    key = filepath + '_' + func_name

    if key in fsync_wrappers.keys():
        return True

    return False

# Compile a list of line numbers where fsync_wrapper function calls are found
def find_fsync_lines(node):

    call_nodes = []

    # Iterate through its children
    for child in node.get_children():

        # Collect all child node calls
        nodes = find_fsync_lines(child)
        call_nodes += nodes

        # If the child is an fsync_wrapper
        if child.kind == clang.cindex.CursorKind.CALL_EXPR:
            if is_fsync_wrapper(child) or child.spelling == "fsync":
                call_nodes.append(child)

    # Remove empty nodes before returning
    return [x for x in call_nodes if x.spelling != ""]

# Returns a list of all the .c .cpp files in dir
def find_all_files(dir):

    # a recursively constructed list of [recursive_directory/file_name[.c or .cpp]]
    list_of_files = []

    # recurse through project folder
    for root, subdirs, files in os.walk(dir):
        # for every file in current directory,
        for filename in files:
            # if it ends with .cpp or .c
            if filename.endswith('.cpp') or filename.endswith('.c'):
                # construct a string with directory from the top root
                add_val = root + '/' + filename
                # and append it to the list of files
                list_of_files.append(add_val)

    return list_of_files


# Return a list of the file's source code lines
def get_file_lines(filepath):

    # Open the source file for reading
    with open(filepath, "r") as f:
        source = f.read()

    return source.split("\n")


# Returns the function name modified according to version ("osync, dsync")
def alt_name(func_name, version):

    # handle the base fsync case
    if "fsync" in func_name:
        return func_name.replace("fsync", version)
    else:
        return version + "_" + func_name


def backup_fwd_decl(node):
    
    node_data = node.location.__repr__().split(',')
    
    func_name = node.spelling
    filepath = node_data[0].split('\'')[1]
    line_number = int(node_data[1].replace('line', '').replace(' ', ''))

    source_code = get_file_lines(filepath)

    index = 0
    func_decl = source_code[line_number - 1]
    while ')' not in func_decl:
        index += 1
        func_decl += source_code[line_number - 1 + index]

    relevant = func_decl.split(')')
    relevant = relevant[0] + ');'

    return relevant

# Returns a modified version of the function's forward declaration
def convert_fwd_decl(node, version):

    func_def = node.referenced
    func_name = node.spelling
    fwd_decl = ""

    if func_name == "fsync":
        return

    for token in func_def.get_tokens():

        fwd_decl += token.spelling + " "
        if token.spelling == ")":
            fwd_decl += ";"
            break

    if fwd_decl == "":
        fwd_decl = backup_fwd_decl(func_def)


    fwd_decl = fwd_decl.replace(func_name, alt_name(func_name, version))

    return fwd_decl

# Runs convert on every fsync_wrapper
def convert_fsync_wrappers(file_functions):

    # Do not modify fsync
    fsync_wrappers.pop("fsync", None)

    # for every file,
    for filepath in set(file_functions.keys()):

        source_lines = get_file_lines(filepath)
        modified_funcs[filepath] = {}
        modified_fwd_decls[filepath] = []

        # for every fsync_wrapper,
        functions = file_functions[filepath]
        for func_name in set(functions):

            # get the right node
            key = filepath + '_' + func_name
            node = fsync_wrappers[key]

            if node is None:
                print "Empty node found in file " + filepath

            # create an osync and dsync copy of every function
            # only create a dsync version of main without prepending "dsync_"
            if func_name != "main":
                convert(filepath, node, source_lines, "osync")
            convert(filepath, node, source_lines, "dsync")

        # Print out the string that will be appended to the file
        # if filepath in modified_funcs.keys():
            # print filepath + ": "
            # print "\n".join(modified_funcs[filepath])


# Returns the line of the last fsync_wrapper function call
def last_fsync_line(func_name, filepath):

    # Compile the line numbers of func calls
    line_nums = []
    key = filepath + "_" + func_name
    for call_node in fsync_lines[key]:
        line_nums.append(call_node.location.line)

    # Determine the greatest line number
    if len(line_nums) == 0:
        print "Zero fsync_wrapper calls were found in the fsync_wrapper named " + filepath
        return -1

    return max(line_nums)


# Converts function implementation and adds it to modified_funcs
def convert(filepath, node, file_source, version):

    # Extract name, start and end line from FUNC_DECL node
    func_name = node.spelling

    start = node.extent.start.line - 1
    end = node.extent.end.line - 1

    # Extract function call nodes from FUNC_DECL node
    key = filepath + "_" + func_name
    call_nodes = fsync_lines[key]

    # Determine the last line for dsync case
    last_line = last_fsync_line(func_name, filepath)
    if last_line == -1:
        return

    # Make copy of source code lines for personal use
    buffer_lines = list(file_source)
    new_name = alt_name(func_name, version)

    # Modify function definition
    if func_name != "main":

        # Modify the function's name
        osync_decl = buffer_lines[start].replace(func_name, new_name)
        buffer_lines[start] = osync_decl

    # Modify function implementation
    updated_line_nums = []
    for call_node in call_nodes:

        # Determine the name of the function that is called
        func_call_name = call_node.spelling
        line_num = call_node.location.line

        # Only allow one modification per line
        # Note: we are not handling the case of more than one fsync_wrapper call per line
        if line_num not in updated_line_nums:

            # Get the line
            line = buffer_lines[line_num - 1]

            # Modify the function call according to the version
            FUNC_CALL_REGEX = re.escape(func_call_name) + r"(?=[\s,()])"

            call_version = "osync"
            if version == "dsync" and line_num == last_line:
                call_version = "dsync"

            new_name = alt_name(func_call_name, call_version)
            updated_line = re.sub(FUNC_CALL_REGEX, new_name, line)

            # Collecting stats
            global osyncs
            global osync_wrappers
            global dsyncs
            global dsync_wrappers
            if call_version == "osync":
                if func_call_name == "fsync":
                    osyncs += 1
                else:
                    osync_wrappers += 1
            elif call_version == "dsync":
                if func_call_name == "fsync":
                    dsyncs += 1
                else:
                    dsync_wrappers += 1

            # Generate a new osync/dsync forward declaration
            new_fwd_decl = convert_fwd_decl(call_node, call_version)
            if  new_fwd_decl is not None:
                modified_fwd_decls[filepath].append(new_fwd_decl)

            # Replace it in the source code
            buffer_lines[line_num - 1] = updated_line
            #call_expr_handler(filename, call_node, func_call_name, temp_funky_name)

            # Update our list of lines that have been updated
            updated_line_nums.append(line_num)

    # Add this modified function to a list of functions that will be appended to the file
    updated_lines = buffer_lines[start:(end+1)]
    updated_func = "\n".join(updated_lines)
    modified_funcs[filepath][updated_func] = node

# Write back all the changes
def modify_source():

    # Make fwd_decls unique
    for key in modified_fwd_decls.keys():
        modified_fwd_decls[key] = list(set(modified_fwd_decls[key]))

    # append all the new functions to the file
    for filepath in modified_funcs.keys():

        impl_hash = modified_funcs[filepath]
        osync_dsync = ["static int osync(int fd) {return syscall(349, fd);}\n",
                        "static int dsync(int fd) {return syscall(350, fd);}\n\n"]
        impls = sorted(impl_hash.keys(), key=lambda x: impl_hash[x].location.line)
        with open(filepath, "a") as wb:

            # Append osync/dsync definition and function implementations to the file
            wb.write("\n".join(osync_dsync))
            wb.write("\n".join(impls))

    # append the function declarations for osyncs and dsyncs right after includes
    for filepath in modified_fwd_decls.keys():

        source_code = get_file_lines(filepath)

        # Comment out original main function
        if filepath + "_main" in fsync_wrappers.keys():

            node = fsync_wrappers[filepath + "_main"]
            start = node.extent.start.line - 1
            end = node.extent.end.line - 1

            # Insert the comments
            source_code[start] = "/*" + source_code[start]
            source_code[end] = source_code[end] + "*/"

        need_prepending = "\n".join(modified_fwd_decls[filepath])

        # go immediately before the first function definition
        index = 0
        while 1:
            if (")" in source_code[index]  and "{" in source_code[index]) \
                    or (")" in source_code[index] and '{' in source_code[index + 1]):
                    break
            index += 1
            continue

        # trace back until we hit the beginning of the function declaration
        while (source_code[index].strip() != ""):
            index -= 1

        source_code.insert(index, "\n")
        source_code.insert(index + 1, need_prepending)

        # Insert the syscall include statement needed for osync/dsync
        source_code.insert(0, "#include <sys/syscall.h>")

        wb = open(filepath, "wb+")

        wb.write("\n".join(source_code))

# Tell clang.cindex where libclang.dylib is
clang.cindex.Config.set_library_path("/Users/tomgong/Desktop/build/lib")
index = clang.cindex.Index.create()

# root of the project want to run the tool on
proj_dir = sys.argv[1]

# Create a copy of the directory whose name has an underscore at the end
# This is the directory where modifications are made
try:
    shutil.copytree(proj_dir, proj_dir + "_")
except OSError:
    shutil.rmtree(proj_dir + "_")
    shutil.copytree(proj_dir, proj_dir + "_")

# find all files in the project
files = find_all_files(proj_dir + "_")

# compile the list of all fsync_wrappers across the project
Z(files)

# Find all the lines where fsync_wrappers are called
W()

# Run ABC routine
convert_fsync_wrappers(file_functions)

# put stuff in the source code
modify_source()

# Print out stats
print "Stats for " + proj_dir + ":"
print "fsync_wrappers found: " + str(len(fsync_wrappers.keys()))
print "osync calls: " + str(osyncs)
print "dsync calls: " + str(dsyncs)
print "osync_wrapper calls: " + str(osync_wrappers)
print "dsync_wrapper calls: " + str(dsync_wrappers)
