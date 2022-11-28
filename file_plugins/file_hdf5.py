# -*- coding: utf-8 -*-
import sys, os, h5py
import numpy as np


title = 'LA_hdf5'
extension = ['*.h5', '*.hdf5']
type = ['LA-ICP-TOMFS']

def identify(filename):
    try:
        gotpeaks = False
        f = h5py.File(filename, 'r')
        if 'PeakData' in f.keys():
            gotpeaks = True
        f.close()
        return gotpeaks
    except:
        return False


def read(FileName, ds_object):

    print('Reading file {0} ...'.format(FileName), end=' ')

    ds_object.filename = FileName

    F = h5py.File(FileName, 'r')
    f_peakdata = F['PeakData']

    ds_object.data_type = type[0]

    ds_object.np = F.attrs['NbrPeaks'][0]
    npks = ds_object.np

    coord_data_info = F['ImageData']['SpotData']['Info'][...]

    coord_data = np.array(F['ImageData']['SpotData']['Data']).T

    #GET DATA DIMS!
    scandata = np.array(F['ImageData']['ScanData']['Data'])
    ny = scandata.shape[0]
    nx = int(scandata[0, 4])
    ds_object.nx = nx
    ds_object.ny = ny
    npix = nx*ny
    #print('NX, NY, NPix = ', nx, ny, npix)

    n_pts = scandata[:,4]

    ds_object.image_data = np.array(f_peakdata['PeakData']).T
    pddims = ds_object.image_data.shape

    temp = np.reshape(ds_object.image_data[0:npks, :, :, :], [npks, pddims[1]*pddims[2]*pddims[3]], order='F')

    ds_object.x_coord = coord_data[1]
    ds_object.y_coord = coord_data[2]
    ds_object.motor_units = F['ImageData'].attrs['CoordinateUnit']

    minx = F['ImageData'].attrs['MinX']
    miny = F['ImageData'].attrs['MinY']
    maxx = F['ImageData'].attrs['MaxX']
    maxy = F['ImageData'].attrs['MaxY']

    # Check for dead pixels
    i_keep = np.where((ds_object.x_coord > minx) & (ds_object.x_coord < maxx) &
                      (ds_object.y_coord > miny) & (ds_object.y_coord < maxy))

    n_i_notkeep = ds_object.x_coord[not i_keep].size

    if n_i_notkeep > 0:
        temp = temp[:, not i_keep]
        ds_object.x_coord = ds_object.x_coord[not i_keep]
        ds_object.y_coord = ds_object.y_coord[not i_keep]

    ds_object.dx = np.round(abs(ds_object.x_coord[-1]-ds_object.x_coord[0])/(nx-1), 5)
    ds_object.dy = np.round(abs(ds_object.y_coord[-1]-ds_object.y_coord[0])/(ny-1), 5)
    # print(ds_object.dx, ds_object.dy)
    # print(ds_object.motor_units)

    # check for incomplete rows
    I_empty = np.zeros([nx,ny])
    for i in range(ny):
        if n_pts[i] < nx:
            I_empty[n_pts[i]:, i] = 1

    I_empty = I_empty.flatten('F')
    n_pix_unempty = np.count_nonzero(I_empty == 0)

    temp = temp[:, 0:n_pix_unempty]
    ds_object.image_data = np.zeros([npks, npix])
    ds_object.image_data[:, np.where(I_empty == 0)[0]] = temp
    ds_object.image_data = np.reshape(ds_object.image_data[0:npks, 0:nx*ny], [npks, nx,ny], order='F')

    # PeakTable: label, mass, lower integration limit, upper integration limit
    ds_object.peaks = []
    temp_peaks = f_peakdata['PeakTable'][...]
    for item in temp_peaks:
        ds_object.peaks.append(item[0].decode('UTF-8'))

    F.close()

    print('done')




