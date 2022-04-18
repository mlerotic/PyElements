# -*- coding: utf-8 -*-


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