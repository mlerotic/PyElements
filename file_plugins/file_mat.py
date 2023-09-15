# -*- coding: utf-8 -*-
import sys, os
import numpy as np
import scipy as sp
import scipy.io as spio
from collections import OrderedDict
#from PyQt5 import QtGui

title = 'XFM_mat'
extension = ['*.mat']
type = ['XFM']

def identify(filename):
    try:
        return os.path.isfile(filename)
    except:
        return False


def read(FileName, data_store, ds_object_list):
    print('Reading file {0} ...'.format(FileName), end=' ')
    ds_object = data_store.DataStore()
    ds_object.filename = FileName
    ds_object.data_type = type[0]

    data_dict = loadmat(FileName)

    fs = _todict(data_dict['handles']['fit_struct'][0])
    ds_object.peaks = fs['names']
    ds_object.np = len(fs['names'])
    ds_object.nx = data_dict['handles']['XRF']['num_x']
    ds_object.ny = data_dict['handles']['XRF']['num_y']

    #print('Data dims = ', ds_object.nx, ds_object.ny, ds_object.np)
    data = fs['calibrated']
    ds_object.image_data = np.reshape(data, [ds_object.np, ds_object.nx, ds_object.ny], order='F')

    ds_object.x_coord = np.reshape(data_dict['handles']['XRF']['X'], [ds_object.nx, ds_object.ny], order='F')
    ds_object.y_coord = np.reshape(data_dict['handles']['XRF']['Y'], [ds_object.nx, ds_object.ny], order='F')
    ds_object.motor_units = data_dict['handles']['XRF']['X_units']

    ds_object.dx = np.round(abs(ds_object.x_coord[-1][0]-ds_object.x_coord[0][0])/(ds_object.nx-1), 5)
    ds_object.dy = np.round(abs(ds_object.y_coord[1][-1]-ds_object.y_coord[1][0])/(ds_object.ny-1), 5)
    # print(ds_object.dx, ds_object.dy)
    # print(ds_object.motor_units)
    ds_object_list.append(ds_object)

    print('done')


def loadmat(filename):
    '''
    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)


def _check_keys(dict):
    '''
    checks if entries in dictionary are mat-objects. If yes
    todict is called to change them to nested dictionaries
    '''
    for key in dict:
        if isinstance(dict[key], spio.matlab.mio5_params.mat_struct):
            dict[key] = _todict(dict[key])
    return dict


def _todict(matobj):
    '''
    A recursive function which constructs from matobjects nested dictionaries
    '''
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if isinstance(elem, spio.matlab.mio5_params.mat_struct):
            dict[strg] = _todict(elem)
        else:
            dict[strg] = elem
    return dict

