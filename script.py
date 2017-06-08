#!/usr/bin/env python
""" Usage: call with <filename>
"""

import os
import sys
import string
import clang.cindex
from subprocess import call

foi = ["printf"]                    # List of functions that affect osync/dsync modification

fsync_wrappers = {"fsync" : None}   # (str) function name : pointer to AST node
fsync_lines = {}                    # (str) function name : [ function call nodes ]
file_functions = {}                 # (str) file name : [ (str) file_functions ]
alt_funcs = {}                      # (str) function name : [ source lines ]

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
        
        fsync_wrappers[node.spelling] = node
        file_functions[filename].append(node.spelling)

    # If this node is an function call and the
    # function being called is an fsync_wrapper, set fsync_found to True.
    if node.kind.is_expression():
        if ((node.kind == clang.cindex.CursorKind.CALL_EXPR)
            & (node.spelling in fsync_wrappers.keys())):

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


# Compile a list of line numbers where fsync_wrapper function calls are found
def find_fsync_lines(node):

    call_nodes = []

    # Iterate through its children
    for child in node.get_children():

        # Collect all child node calls
        nodes = find_fsync_lines(child)
        call_nodes += nodes

        # If the child is an fsync_wrapper
        if (child.spelling in fsync_wrappers.keys()) or child.spelling == "fsync":
            call_nodes.append(node)

    return call_nodes


# Find all lines in fsync_wrappers where fsync_wrappers are called
def W():

    # Remove fsync from fsync_wrappers
    fsync_wrappers.pop("fsync", None)

    # Iterate through all fsync_wrapper nodes
    for node in fsync_wrappers.values():
        fsync_lines[node.spelling] = find_fsync_lines(node)

# Retuns a list of all the .c .cpp files in dir
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


# Return a list of source code lines
def get_source_lines(filepath):

    # Open the source file for reading
    with open(filepath, "r") as f:
        source = f.read()

    return source.split("\n")


def modify_source(file_functions):

    # for every file,
    for filepath in set(file_functions.keys()):

        file_source = get_source_lines(filepath)

        # for every wrapper function,
        functions = file_functions[filepath]
        for func_name in set(functions):

            node = fsync_wrappers[func_name]
            start = node.extent.start.line
            end = node.extent.end.line

            # create an osync and dsync copy of function
            to_osync(node, file_source, "osync")
            to_osync(node, file_source, "dsync")

# Returns the function name modified according to version ("osync, dsync")
def alt_name(func_name, version):
    # handle the base fsync case
    if "fsync" in func_name:
        return func_name.replace("fsync", version)
    else:
        return version + "_" + func_name

def to_osync(node, file_source, version):

    func_name = node.spelling
    start = node.extent.start.line
    end = node.extent.end.line

    # Make copy of source code lines for personal user
    osync_lines = list(file_source)

    # Modify function definition
    osync_definition = osync_lines[start - 1].replace(func_name, alt_name(func_name, version))
    osync_lines[start - 1] = osync_definition

    # Determine the last fsync_wrapper function call
    line_nums = []
    for call_node in fsync_lines[func_name]:
        line_nums.append(call_node.location.line)

    # Determine the last line number of such a call
    last_line = max(line_nums)

    # Modify function implementation
    updated_line_nums = []
    for call_node in fsync_lines[func_name]:

        func_call_name = call_node.spelling
        line_num = call_node.location.line

        if line_num not in updated_line_nums:

            # Get the line
            line = osync_lines[line_num - 1]

            # Modify the function call
            if version == "dsync" and line_num == last_line:
                updated_line = line.replace(func_call_name, alt_name(func_call_name, "dsync"))
            else:
                updated_line = line.replace(func_call_name, alt_name(func_call_name, "osync"))

            # Replace it in the source code
            osync_lines[line_num - 1] = updated_line

            # Update our list of lines that have been updated
            updated_line_nums.append(line_num)

    updated_func = osync_lines[(start-1):end]
    print "\n".join(updated_func)


def insert_alt_funcs(source_lines):

    starts_and_ends = []
    for func_name in alt_defs.keys():
        node = fsync_wrappers[func_name]
        starts_and_ends.append(node.extent.start.line)
        starts_and_ends.append(node.extent.end.line)

    # Add last line of file
    starts_and_ends.append(len(source_lines))

    # sort starts and ends
    starts_and_ends.sort()

    partitions = []
    start = 0
    for line_num in starts_and_ends:
        partitions.append(source_lines[start:line_num])
        start = line_num



# Tell clang.cindex where libclang.dylib is
clang.cindex.Config.set_library_path("/Users/tomgong/Desktop/build/lib")
index = clang.cindex.Index.create()

# root of the project want to run the tool on
proj_dir = sys.argv[1]

# find all files in the project
files = find_all_files(proj_dir)

# compile the list of all fsync_wrappers across the project
Z(files)

# populate fsync_lines
W();

# Run ABC routine
modify_source(file_functions)

#insert_alt_funcs()



