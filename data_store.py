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
        self.dx = 0
        self.dy = 0
        self.motor_units = None
        self.filename = ''
        self.despike = 0
        self.threshold = [0, 100]
        self.gamma = 1.0
        self.display_image = None


    def MirrorUD(self):
        self.image_data = np.flip(self.image_data, 2)


    def MirrorLR(self):
        self.image_data = np.flip(self.image_data, 1)