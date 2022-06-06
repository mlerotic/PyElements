# -*- coding: utf-8 -*-
import numpy as np


class DataStore:
    def __init__(self):
        self.data_type = ''
        self.image_data = None  # 3D datastack
        self.nx = 0
        self.ny = 0
        self.np = 0  # number of slices (elements)
        self.peaks = []  # slice names
        self.x_coord = None
        self.y_coord = None
        self.motor_units = None
        self.filename = ''
        self.despike = 0
        self.threshold = 100


    def MirrorUD(self):
        self.image_data = np.flip(self.image_data, 2)


    def MirrorLR(self):
        self.image_data = np.flip(self.image_data, 1)