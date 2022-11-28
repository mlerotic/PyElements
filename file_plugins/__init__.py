# -*- coding: utf-8 -*-


"""
The file_plugins system is exposed to general code through the functions defined here in __init__.py:

identify(filename)                  : Returns an instance of the plugin that claims to deal with the file at the URL 'filename'.
load(filename,data_store_object,..)      : Loads data from the URL 'filename' into the object (data_store type). The plugin used can be stated or determined automatically, using 'identify'.

Further functions for writing files via the plugins need to be written yet. To access the system, you should import the module ('import file_plugins') and then access the above functions as attributes of the module (e.g. 'file_plugins.load('data.hdf5',data_stk)' ).

Each file plugin should be included here in the 'file_plugins' directory. Each plugin should define the following:

title                           : A short string naming the plugin.
extension                       : A list of strings indicating the file extensions that the plugin handles (e.g. ['*.txt']).
types                           : A string indicating the data type that the plugin will read.
identify(filename)              : Returns boolean indicating if the plugin can read the file at URL 'filename'.
read(filename,datastore_object,..)  : Loads data from the URL 'filename' into the object (data_stack type) 'datastore_object'.

"""
from __future__ import print_function

import pkgutil, importlib, os, sys
import numpy
sys.path.append(".")
import data_store

verbose = True

# These variables declare the options that each plugin can claim the ability to handle
actions = ['read','write']
#data_types = ['spectrum','image','stack','results'] # Please refer to the individual file plugins for the supported data types.
data_types = []
# Go through the directory and try to load each plugin
plugins = []

for m in pkgutil.iter_modules(path=__path__):
    if verbose: print("Loading file plugin:", m[1], ".", end=' ')
    spec = importlib.machinery.PathFinder().find_spec(m[1],__path__)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        # check if there is a read() function in plugin
        if hasattr(mod, 'read'):
            plugins.append(mod)
            data_types.extend(plugins[-1].type) # pull data types from each file plugin
            print(plugins[-1].type)
            if verbose: print("("+plugins[-1].title+") Success!")
        else:
            if verbose: print('Not a valid plugin - skipping.')
    except ImportError as e:
        if verbose: print("prerequisites not satisfied:", e)


# Go through set of plugins and assemble lists of supported file types for each action and data type
supported_plugins = []
supported_filters = []
filter_list =  []
for P in plugins:
    filter_list.append(P.title+' ('+' '.join(P.extension)+')') # Fill filter_list with file extensions
    supported_plugins.append(P) # Fill supported_plugins with plugin for each scan/data type
    for ext in P.extension:
        if ext not in supported_filters:
            supported_filters.append(ext) # Fill supported_filters with file extensions
filter_list = ['Supported Formats ('+' '.join(supported_filters)+')']+filter_list
filter_list.append('All files (*.*)')


def load(filename, datastore_object=None, plugin=None):
    """
    Pass the load command over to the appropriate plugin so that it can import data from the named file.
    selection defines a list of tuples as [(region, channel),(region+1,channel),...]
    """
    if plugin is None:
        plugin = identify(filename)
    if plugin is None:
        return None
    else:
        print("load", filename, "with the", plugin.title, "plugin.")
        plugin.read(filename, datastore_object)


def identify(filename):
    """
    Cycle through plugins until finding one that claims to understand the file format.
    First it tries those claiming corresponding file extensions, followed by all other plugins until an appropriate plugin is found.
    """
    if verbose: print("Identifying file:", filename, "...", end=' ')
    ext = os.path.splitext(filename)[1]
    flag = [True]*len(plugins)
    for i,P in enumerate(plugins):
        if '*'+ext in P.extension:
            if P.identify(filename):
                print('success')
                return P
            elif flag[i] == True: #if plugin returns False, e.g. dataexch_hdf5 does not match, try the next plugin and find the same extension
                flag[i] = False
                continue
            else:
                break
    print("Error! unknown file type.")
    return None

