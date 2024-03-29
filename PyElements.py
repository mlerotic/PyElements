# -*- coding: utf-8 -*-

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import (
        NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.widgets import LassoSelector
matplotlib.interactive( True )
matplotlib.rcParams['svg.fonttype'] = 'none'
from matplotlib import cm
import matplotlib.pyplot as plt
import cv2
import numpy as np
import scipy as sp
from scipy.ndimage import median_filter, uniform_filter, filters, interpolation
import file_plugins
import data_store
from QRangeSlider import QRangeSlider
import skimage as ski


Winsizex = 1000
Winsizey = 800

PlotH = 4.0
PlotW = PlotH*1.61803

version = '1.0.0'


# -----------------------------------------------------------------------------
# Despike image using Enhanced Lee Filter
def despike(image, leefilt_percent=50.0):
    fimg = lee_filter(image)

    leefilt_max = np.amax(fimg)
    threshold = (1. + 0.01 * leefilt_percent) * leefilt_max

    datadim = np.int32(image.shape)

    ncols = datadim[0].copy()
    nrows = datadim[1].copy()

    spikes = np.where(image > threshold)
    n_spikes = fimg[spikes].shape[0]

    result_img = image.copy()

    if n_spikes > 0:

        xsp = spikes[0]
        ysp = spikes[1]
        for i in range(n_spikes):
            ix = xsp[i]
            iy = ysp[i]
            if ix == 0:
                ix1 = 1
                ix2 = 2
            elif ix == (ncols - 1):
                ix1 = ncols - 2
                ix2 = ncols - 3
            else:
                ix1 = ix - 1
                ix2 = ix + 1

            if iy == 0:
                iy1 = 1
                iy2 = 2
            elif iy == (nrows - 1):
                iy1 = nrows - 2
                iy2 = nrows - 3
            else:
                iy1 = iy - 1
                iy2 = iy + 1

            result_img[ix, iy] = 0.25 * (image[ix1, iy] + image[ix2, iy] +
                                         image[ix, iy1] + image[ix, iy2])

    return result_img


# -----------------------------------------------------------------------------
# Lee filter
def lee_filter(image):
    nbox = 5  # The size of the filter box is 2N+1.  The default value is 5.
    sig = 5.0  # Estimate of the standard deviation.  The default is 5.

    delta = int((nbox - 1) / 2)  # width of window

    datadim = np.int32(image.shape)

    n_cols = datadim[0].copy()
    n_rows = datadim[1].copy()

    Imean = np.zeros((n_cols, n_rows))
    uniform_filter(image, size=nbox, output=Imean)

    Imean2 = Imean ** 2

    # variance
    z = np.empty((n_cols, n_rows))

    for l in range(delta, n_cols - delta):
        for s in range(delta, n_rows - delta):
            z[l, s] = np.sum((image[l - delta:l + delta, s - delta:s + delta] - Imean[l, s]) ** 2)

    z = z / float(nbox ** 2 - 1.0)

    z = (z + Imean2) / float(1.0 + sig ** 2) - Imean2

    ind = np.where(z < 0)
    n_ind = z[ind].shape[0]
    if n_ind > 0:
        z[ind] = 0

    lf_image = Imean + (image - Imean) * (z / (Imean2 * sig ** 2 + z))

    return lf_image

class ShowHistogram(QtWidgets.QDialog, QtWidgets.QGraphicsScene):
    def __init__(self, parent, image_data, data_channel):
        QtWidgets.QWidget.__init__(self, parent)

        self.parent = parent

        self.resize(1000, 550)
        self.setWindowTitle('Histogram')

        vboxtop = QtWidgets.QVBoxLayout()

        st = QtWidgets.QLabel('Channel: {0}'.format(data_channel))
        font = st.font()
        font.setBold(True)
        font.setPointSize(10)
        st.setFont(font)
        vboxtop.addWidget(st)
        self.instruction = st

        hboxtop = QtWidgets.QHBoxLayout()
        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        fbox = QtWidgets.QVBoxLayout()
        self.rimgfig = Figure()
        self.rImagePanel = FigureCanvas(self.rimgfig)
        self.rImagePanel.setParent(self)
        fbox.addWidget(self.rImagePanel)
        toolbar = NavigationToolbar(self.rImagePanel, self)
        fbox.addWidget(toolbar)
        frame.setLayout(fbox)
        hboxtop.addWidget(frame, 2)

        vboxtop.addLayout(hboxtop)

        hboxb = QtWidgets.QHBoxLayout()
        hboxb.addStretch(1)

        button_export = QtWidgets.QPushButton('Export to .csv')
        button_export.clicked.connect(self.OnExport)
        hboxb.addWidget(button_export)

        button_cancel = QtWidgets.QPushButton('Close')
        button_cancel.clicked.connect(self.close)
        hboxb.addWidget(button_cancel)

        vboxtop.addLayout(hboxb)
        self.setLayout(vboxtop)

        self.ShowHistogram(image_data, data_channel)


    def ShowHistogram(self, image_data, data_channel):
        fig = self.rimgfig
        fig.clf()
        fig.add_axes((0.15, 0.15, 0.75, 0.75))
        axes = fig.gca()

        histogram = image_data.flatten()

        self.counts, self.bins, patches = axes.hist(histogram, 100)
        self.counts = self.counts.astype(np.int64)

        # axes.set_ylim(bottom=0)
        axes.set_xlabel('Counts')
        axes.set_title(data_channel)
        axes.set_yscale('log')

        self.rImagePanel.draw()


    def OnExport(self):
        wildcard = "Csv files (*.csv);;"
        SaveFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Histogram data', '', wildcard)
        SaveFileName = str(SaveFileName)
        if SaveFileName == '':
            return
        f = open(str(SaveFileName), 'wt')
        print('Bin number, Counts, Bins', file=f)
        for i in range(len(self.counts)):
            print('{0}, {1}, {2}'.format(i+1, self.counts[i], self.bins[i]), file=f)
        f.close()



class ShowHistogramPerChannel(QtWidgets.QDialog, QtWidgets.QGraphicsScene):
    def __init__(self, parent, data):
        QtWidgets.QWidget.__init__(self, parent)

        self.parent = parent
        self.data = data

        self.resize(1000, 550)
        self.setWindowTitle('Histogram')

        vboxtop = QtWidgets.QVBoxLayout()

        # st = QtWidgets.QLabel('Channel: {0}'.format(data_channel))
        # font = st.font()
        # font.setBold(True)
        # font.setPointSize(10)
        # st.setFont(font)
        # vboxtop.addWidget(st)
        # self.instruction = st

        hboxtop = QtWidgets.QHBoxLayout()

        self.limgfig = Figure((4.0, 4.0))
        self.lImagePanel = FigureCanvas(self.limgfig)
        self.lImagePanel.setParent(self)
        # self.lImagePanel.mpl_connect('button_press_event', self.OnPointLeftimage)
        # self.lImagePanel.setCursor(Qt.CrossCursor)
        hboxtop.addWidget(self.lImagePanel, 1)

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        fbox = QtWidgets.QVBoxLayout()

        self.rimgfig = Figure()
        self.rImagePanel = FigureCanvas(self.rimgfig)
        self.rImagePanel.setParent(self)
        # self.rImagePanel.mpl_connect('button_press_event', self.OnPointRightimage)
        # self.rImagePanel.setCursor(Qt.CrossCursor)

        fbox.addWidget(self.rImagePanel)
        toolbar = NavigationToolbar(self.rImagePanel, self)
        fbox.addWidget(toolbar)
        frame.setLayout(fbox)
        hboxtop.addWidget(frame, 2)

        vboxtop.addLayout(hboxtop)

        hboxb = QtWidgets.QHBoxLayout()
        hboxb.addStretch(1)

        button_export = QtWidgets.QPushButton('Export to .csv')
        button_export.clicked.connect(self.OnExport)
        hboxb.addWidget(button_export)

        button_cancel = QtWidgets.QPushButton('Close')
        button_cancel.clicked.connect(self.close)
        hboxb.addWidget(button_cancel)

        vboxtop.addLayout(hboxb)
        self.setLayout(vboxtop)

        self.ShowImage()
        self.ShowHistogram()


    def ShowImage(self):
        if self.data.display_image is None:
            return

        fig = self.limgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        self.laxes = fig.gca()
        fig.patch.set_alpha(1.0)
        im = self.laxes.imshow(self.data.display_image.T, cmap=matplotlib.cm.get_cmap('gray'))
        self.laxes.axis("off")
        self.lImagePanel.draw()

    def ShowHistogram(self):
        n_channels = self.data.np
        self.histogram = np.sum(self.data.image_data, axis=(1,2))
        fig = self.rimgfig
        fig.clf()
        fig.add_axes((0.15, 0.15, 0.75, 0.75))
        axes = fig.gca()
        # axes.fill_between(range(n_channels), histogram, step="pre")
        # axes.step(range(n_channels), histogram)
        bar_plot = axes.bar(range(1, n_channels+1), self.histogram, width=1)
        # axes.set_ylim(bottom=0)
        axes.set_xlim(left=1, right=n_channels+1)
        axes.set_xlabel('Channel')
        axes.set_ylabel('Counts')
        axes.set_yscale('log')
        axes.format_coord = self.format_coord
        # axes.set_xticks(range(n_channels))
        # fig.autofmt_xdate()

        self.rImagePanel.draw()

    def format_coord(self, x, y):
        col = int(x+0.5)
        row = int(y+0.5)
        if col >= 1 and col < self.data.np+1:
            z = self.data.peaks[int(col-1)]
            return 'channel=%s [x=%1.0f, y=%1.4f]' % (z, x, y)
        else:
            return '[x=%1.0f, y=%1.4f]' % (x, y)

    def OnExport(self):
        wildcard = "Csv files (*.csv);;"
        SaveFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Histogram data', '', wildcard)
        SaveFileName = str(SaveFileName)
        if SaveFileName == '':
            return
        f = open(str(SaveFileName), 'wt')
        print('Channel number, Counts, Channel name', file=f)
        for i in range(self.data.np):
            print('{0}, {1}, {2}'.format(i+1, self.histogram[i], self.data.peaks[i]), file=f)
        f.close()


class ImageRegistrationDialog(QtWidgets.QDialog):

    def __init__(self, parent, image1, image2):
        super(ImageRegistrationDialog, self).__init__(parent)
        self.parent = parent

        self.parent = parent
        self.image1 = image1
        self.image2 = image2
        self.aligned_image = None
        self.lpoints = []
        self.rpoints = []
        self.transform = 'homography'
        self.n_segments = 36
        self.data_transformH = None
        self.data_transform_fine = None

        self.resize(1350, 750)
        self.setWindowTitle('Image Alignment')
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        vboxtop = QtWidgets.QVBoxLayout()
        hboxtop = QtWidgets.QHBoxLayout()
        sizer1 = QtWidgets.QGroupBox('Manual Point Selection')
        vbox1 = QtWidgets.QVBoxLayout()
        st = QtWidgets.QLabel('1 - Select points on the images\n2 - Improve point locations with cross-correlation\n3 - Calculate')
        # self.rb_affine = QtWidgets.QRadioButton('Affine', self)
        # self.rb_hom = QtWidgets.QRadioButton('Homography',self)
        # self.rb_affine.setChecked(True)
        # self.rb_affine.toggled.connect(self.OnMethod)
        vbox1.addWidget(st)
        # vbox1.addWidget(self.rb_affine)
        # vbox1.addWidget(self.rb_hom)
        self.b_ccr_alignment = QtWidgets.QPushButton('Improve point locations')
        self.b_ccr_alignment.setMaximumWidth(220)
        self.b_ccr_alignment.clicked.connect(self.OnSegmentAlignmentCC)
        # self.b_ccr_alignment.setEnabled(False)
        vbox1.addWidget(self.b_ccr_alignment)
        button_calc_homography = QtWidgets.QPushButton('Calculate')
        button_calc_homography.setMaximumWidth(220)
        button_calc_homography.clicked.connect(self.OnCalculateHomography)
        vbox1.addWidget(button_calc_homography)
        sizer1.setLayout(vbox1)
        hboxtop.addWidget(sizer1, 1)
        sizer2 = QtWidgets.QGroupBox('Automatic point location refinement')
        vbox2 = QtWidgets.QVBoxLayout()
        st = QtWidgets.QLabel('Improve point location using segments:')
        vbox2.addWidget(st)
        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(QtWidgets.QLabel('Segments size N:  '))
        self.le_nsegments = QtWidgets.QLineEdit()
        self.le_nsegments.setText('{0}'.format(self.n_segments))
        self.le_nsegments.setMaximumWidth(150)
        self.le_nsegments.setAlignment(QtCore.Qt.AlignRight)
        self.le_nsegments.setValidator(QtGui.QIntValidator(2, 10, self))
        hbox2.addWidget(self.le_nsegments)
        hbox2.addStretch(1)
        vbox2.addLayout(hbox2)
        self.b_show_segments = QtWidgets.QPushButton('Show Segments')
        self.b_show_segments.setMaximumWidth(220)
        self.b_show_segments.clicked.connect(self.OnShowSegments)
        # self.b_show_segments.setEnabled(False)
        vbox2.addWidget(self.b_show_segments)
        sizer2.setLayout(vbox2)
        hboxtop.addWidget(sizer2, 1)
        vboxtop.addLayout(hboxtop)
        vboxtop.addSpacing(20)

        st = QtWidgets.QLabel('Select at least 5 points on the left image and 5 corresponding points on the right.')
        font = st.font()
        font.setBold(True)
        font.setPointSize(10)
        st.setFont(font)
        vboxtop.addWidget(st)
        self.instruction = st

        gridsizertop = QtWidgets.QGridLayout()

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        fbox = QtWidgets.QHBoxLayout()

        self.limgfig = Figure()
        self.lImagePanel = FigureCanvas(self.limgfig)
        self.lImagePanel.setParent(self)
        self.lImagePanel.mpl_connect('button_press_event', self.OnPointLeftimage)
        self.lImagePanel.setCursor(Qt.CrossCursor)

        fbox.addWidget(self.lImagePanel)
        frame.setLayout(fbox)
        gridsizertop.addWidget(frame, 0, 0)

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        fbox = QtWidgets.QHBoxLayout()

        self.rimgfig = Figure()
        self.rImagePanel = FigureCanvas(self.rimgfig)
        self.rImagePanel.setParent(self)
        self.rImagePanel.mpl_connect('button_press_event', self.OnPointRightimage)
        self.rImagePanel.setCursor(Qt.CrossCursor)

        fbox.addWidget(self.rImagePanel)
        frame.setLayout(fbox)
        gridsizertop.addWidget(frame, 0, 1)
        vboxtop.addLayout(gridsizertop)

        self.t_status = QtWidgets.QTextEdit()
        vboxtop.addWidget(self.t_status)

        hboxb = QtWidgets.QHBoxLayout()
        hboxb.addStretch(1)
        # button_save = QtWidgets.QPushButton('Apply')
        # button_save.clicked.connect(self.OnApply)
        # hboxb.addWidget(button_save)

        button_clear = QtWidgets.QPushButton('Reset')
        button_clear.clicked.connect(self.OnClear)
        hboxb.addWidget(button_clear)

        button_cancel = QtWidgets.QPushButton('Cancel')
        button_cancel.clicked.connect(self.close)
        hboxb.addWidget(button_cancel)

        self.b_save = QtWidgets.QPushButton('Save')
        self.b_save.clicked.connect(self.OnSave)
        hboxb.addWidget(self.b_save)
        self.b_save.setEnabled(False)

        vboxtop.addLayout(hboxb)

        self.setLayout(vboxtop)

        self.ShowImage(self.image1, self.image2)


    def ShowImage(self, image1, image2):

        if image1 is None or image2 is None:
            return

        np.save('image1.bin', image1)
        np.save('image2.bin', image2)

        fig = self.limgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        self.laxes = fig.gca()
        fig.patch.set_alpha(1.0)
        # despeckle the image
        dimage1 = despike(image1)
        im = self.laxes.imshow(dimage1.T, cmap=matplotlib.cm.get_cmap('gray'))
        self.laxes.axis("off")
        self.lImagePanel.draw()

        if image2 is not None:
            fig = self.rimgfig
            fig.clf()
            fig.add_axes(((0.0,0.0,1.0,1.0)))
            self.raxes = fig.gca()
            fig.patch.set_alpha(1.0)
            # despeckle the image
            dimage2 = despike(image2)
            im = self.raxes.imshow(dimage2.T, cmap=matplotlib.cm.get_cmap('gray'))
            self.raxes.axis("off")
            self.rImagePanel.draw()


    def OnPointLeftimage(self, evt):
        x = evt.xdata
        y = evt.ydata

        if (x == None) or (y == None):
            return

        x1 = int(np.floor(x))
        y1 = int(np.floor(y))
        self.lpoints.append([y1, x1])
        self.t_status.append('Image L - [{0}, {1}]'.format(x1, y1))

        self.laxes.plot(x1, y1, '.')
        self.lImagePanel.draw()

    def OnPointRightimage(self, evt):
        x = evt.xdata
        y = evt.ydata

        if (x == None) or (y == None):
            return

        x2 = int(np.floor(x))
        y2 = int(np.floor(y))
        self.rpoints.append([y2, x2])
        self.t_status.append('Image R - [{0}, {1}]'.format(x2, y2))

        self.raxes.plot(x2, y2, '.')
        self.rImagePanel.draw()

    def OnClear(self):
        self.lpoints = []
        self.rpoints = []
        self.data_transformH = None
        self.data_transform_fine = None
        self.t_status.clear()
        self.ShowImage(self.image1, self.image2)
        self.b_ccr_alignment.setEnabled(False)
        self.b_save.setEnabled(False)

    def OnCalculateHomography(self):
        if self.transform == 'affine':
            npts = 3
            if len(self.lpoints) != npts or len(self.rpoints) != npts:
                QtWidgets.QMessageBox.warning(self, 'Warning', "Please select exactly {0} points on the left "
                                                               "and the right image.".format(npts))
                return
        else:
            npts = 5
            if len(self.lpoints) < npts or len(self.rpoints) < npts:
                QtWidgets.QMessageBox.warning(self, 'Warning', "Please select {0} points on the left "
                                                               "and the right image.".format(npts))
                return
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
        pts1 = np.float32(self.lpoints)
        pts2 = np.float32(self.rpoints)
        h1, w1 = self.image1.shape[:2]
        h2, w2 = self.image2.shape[:2]

        if self.transform == 'affine':
            H = cv2.getAffineTransform(pts2, pts1)
            al_image2 = cv2.warpAffine(self.image2, H, (w1, h1))
        else:
            H, status = cv2.findHomography(pts2, pts1)
            al_image2 = cv2.warpPerspective(self.image2, H, (w1, h1),
                                              flags=cv2.INTER_LINEAR)
        self.b_ccr_alignment.setEnabled(True)
        self.b_show_segments.setEnabled(True)
        self.b_save.setEnabled(True)

        self.data_transformH = H
        self.ShowImage(self.image1, al_image2)
        self.aligned_image = al_image2
        QtWidgets.QApplication.restoreOverrideCursor()

        rgb_img = np.zeros((w1, h1, 3), dtype='uint8')
        rgb_img[:, :, 0] = ((self.image1.T - self.image1.min()) * (1 / (self.image1.max() - self.image1.min()) * 255)).astype('uint8')
        rgb_img[:, :, 1] = (
                    (self.aligned_image.T - self.aligned_image.min()) * (1 / (self.aligned_image.max() - self.aligned_image.min()) * 255)).astype(
            'uint8')

        plt.figure()
        plt.imshow(rgb_img, interpolation='none')
        plt.show()

    def OnSave(self):
        if self.data_transform_fine is not None:
            self.parent.data_transform = self.data_transform_fine
        else:
            self.parent.data_transform = self.data_transformH
        self.parent.transform = self.transform
        self.parent.AlignData()
        self.parent.ShowImage()
        self.close()


    def OnMethod(self, enabled):
        state = enabled

        if state:
            self.transform = 'affine'
            self.instruction.setText('Select 3 points on the left image and 3 corresponding points on the right.')
        else:
            self.transform = 'homography'
            self.instruction.setText('Select at least 5 points on the left image and 5 corresponding points on the right.')

        self.OnClear()

    def ShowSegsImg(self, axis, ptsi):
        n_segments = int(self.le_nsegments.text())
        n2 = int(self.n_segments/2)
        pts1 = np.float32(ptsi)
        for i in range(len(pts1)):
            rect = matplotlib.patches.Rectangle((pts1[i][1] - n2, pts1[i][0] - n2), n_segments, n_segments,
                                                linewidth=1, edgecolor='r', facecolor='none')
            axis.add_patch(rect)
            axis.plot(pts1[i][1], pts1[i][0], '.')

    def OnShowSegments(self):
        npts = 5
        if len(self.lpoints) < npts or len(self.rpoints) < npts:
            QtWidgets.QMessageBox.warning(self, 'Warning', "Please select {0} points on the left "
                                                           "and the right image.".format(npts))
            return

        self.ShowImage(self.image1, self.image2)
        self.n_segments = int(self.le_nsegments.text())
        n2 = int(self.n_segments/2)
        pts1 = np.float32(self.lpoints)
        pts2 = np.float32(self.rpoints)
        self.ShowSegsImg(self.laxes, pts1)
        self.lImagePanel.draw()
        self.ShowSegsImg(self.raxes, pts2)
        self.rImagePanel.draw()

    def registration_phaseCrossCorrelation(self, ref_img, mov_img):
        tvec = ski.registration.phase_cross_correlation(ref_img, mov_img, upsample_factor=4)[0]
        M = np.array([
            [1, 0, tvec[0]],
            [0, 1, tvec[1]]]
        )
        w1, h1 = mov_img.shape
        reg_img = cv2.warpAffine(mov_img, M, (h1, w1))
        return reg_img, tvec

    def OnSegmentAlignmentCC(self):
        self.t_status.append('Improved point locations')
        self.n_segments = int(self.le_nsegments.text())
        n2 = int(self.n_segments/2)
        pts1 = self.lpoints
        pts2 = self.rpoints
        pts_pcc = []
        pts_aligned = []
        for i in range(len(pts1)):
            template1 = self.image1[pts1[i][1] - n2:pts1[i][1] + n2, pts1[i][0] - n2:pts1[i][0] + n2]
            template2 = self.image2[pts2[i][1] - n2:pts2[i][1] + n2, pts2[i][0] - n2:pts2[i][0] + n2]
            reg_im, tvec = self.registration_phaseCrossCorrelation(template1, template2)
            pts_pcc.append([tvec[0], tvec[1]])
            pts_aligned.append([pts2[i][0] - pts_pcc[i][1], pts2[i][1] - pts_pcc[i][0]])
            self.t_status.append('Point {0} shift {1}, {2} [{3}, {4}] -> [{5}, {6}]'.format(i, tvec[0], tvec[1],
                                                                                            pts2[i][0], pts2[i][1],
                                                                                            pts_aligned[i][0], pts_aligned[i][1]))
            # fig, axs = plt.subplots(1, 3, figsize=(12, 4))
            # ax = axs[0]
            # ax.imshow(template1.T, cmap='gray')
            # ax.set_title("Reference Image")
            # ax = axs[1]
            # ax.imshow(template1.T.astype(float) - reg_im.T, cmap='bwr')
            # ax.set_title("diff")
            # ax = axs[2]
            # ax.imshow(reg_im.T, cmap='gray')
            # ax.set_title("Registered Image")
            # plt.show()
        self.rpoints = pts_aligned[:]
        self.ShowSegsImg(self.raxes, pts_aligned)
        self.ShowSegsImg(self.laxes, pts_aligned)
        self.rImagePanel.draw()
        self.lImagePanel.draw()
        # self.OnShowSegments()

    def OnCalculateSIFT(self):
        npts = 5
        if len(self.lpoints) < npts or len(self.rpoints) < npts:
            QtWidgets.QMessageBox.warning(self, 'Warning', "Please select {0} points on the left "
                                                           "and the right image.".format(npts))
            return

        import pickle
        with open('points.pickle', 'wb') as handle:
            pickle.dump([self.lpoints, self.rpoints], handle, protocol=pickle.HIGHEST_PROTOCOL)

        self.n_segments = int(self.le_nsegments.text())
        n2 = int(self.n_segments/2)
        pts1 = self.lpoints
        pts2 = self.rpoints

        for i in range(0, self.n_segments):
            template1 = self.image1[pts1[i][0]-n2:pts1[i][0]+n2, pts1[i][1]-n2:pts1[i][1]+n2]
            template2 = self.image2[pts2[i][0] - n2:pts2[i][0] + n2, pts2[i][1] - n2:pts2[i][1] + n2]
            xshift, yshift, fr = self.registration_shift(template1, template2)

        # pts1 = np.float32(points1)
        # pts2 = np.float32(points2)
        # h1, w1 = self.image1.shape[:2]
        # h2, w2 = self.aligned_image.shape[:2]
        #
        # H, status = cv2.findHomography(pts1, pts2)
        # al_image2 = cv2.warpPerspective(self.aligned_image, H, (w1, h1), flags=cv2.INTER_LINEAR)
        #
        # self.data_transform_fine = np.matmul(H, self.data_transformH)
        # self.ShowImage(self.image1, al_image2)

        # test_im = cv2.warpPerspective(self.image2, combined_transform, (w1, h1), flags=cv2.INTER_LINEAR)
        # plt.figure()
        # plt.imshow(test_im.T, 'gray', interpolation='none')
        # plt.show()

    def registration_shift(self, ref_im, mov_im):
        mapper = cv2.reg.MapperGradShift()
        mapper_pyramid = cv2.reg.MapperPyramid(mapper)
        # Notice that you can adjust these parameters to fit your usecase
        mapper_pyramid.numLev_ = 5
        mapper_pyramid.numIterPerScale_ = 25
        M = mapper_pyramid.calculate(ref_im / np.max(ref_im),
                                     mov_im / np.max(mov_im))  # Notice that it fails if the images are not normalized to [0, 1)
        map_shift = cv2.reg.MapTypeCaster_toShift(M.inverseMap())
        tvec = map_shift.getShift()
        return tvec

    # ----------------------------------------------------------------------
    # Register images using Fourier Shift Theorem
    # EdgeEnhancement: 0 = no edge enhacement; 1 = sobel; 2 = prewitt
    def calc_fouriershifts(self, ref_image, image2, have_ref_img_fft=False, edge_enhancement=0):

        if have_ref_img_fft == False:
            if edge_enhancement == 1:
                self.ref_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(filters.sobel(ref_image))))
            elif edge_enhancement == 2:
                self.ref_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(filters.prewitt(ref_image))))
            else:
                self.ref_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(ref_image)))

        if edge_enhancement == 1:
            img2_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(filters.sobel(image2))))
        if edge_enhancement == 2:
            img2_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(filters.prewitt(image2))))
        else:
            img2_fft = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(image2)))

        fr = (self.ref_fft * img2_fft.conjugate()) / (np.abs(self.ref_fft) * np.abs(img2_fft))
        fr = np.fft.fftshift(np.fft.ifft2(np.fft.fftshift(fr)))
        fr = np.abs(fr)

        shape = ref_image.shape

        xc, yc = np.unravel_index(np.argmax(fr), shape)

        # Limit the search to 1 pixel border
        if xc == 0:
            xc = 1
        if xc == shape[0] - 1:
            xc = shape[0] - 2

        if yc == 0:
            yc = 1
        if yc == shape[1] - 1:
            yc = shape[1] - 2

        # Use peak fit to find the shifts
        xpts = [xc - 1, xc, xc + 1]
        ypts = fr[xpts, yc]
        xf, fit = self.peak_fit(xpts, ypts)

        xpts = [yc - 1, yc, yc + 1]
        ypts = fr[xc, xpts]
        yf, fit = self.peak_fit(xpts, ypts)

        xshift = xf - float(shape[0]) / 2.0
        yshift = yf - float(shape[1]) / 2.0

        return xshift, yshift, fr

    # ----------------------------------------------------------------------
    # Quadratic peak fit: Fits the 3 data pairs to y=a+bx+cx^2, returning fit=[a,b,c]'
    #  and xpeak at position of inflection'
    def peak_fit(self, x, y):

        y1y0 = y[1] - y[0]
        y2y0 = y[2] - y[0]
        x1x0 = float(x[1] - x[0])
        x2x0 = float(x[2] - x[0])
        x1x0sq = float(x[1] * x[1] - x[0] * x[0])
        x2x0sq = float(x[2] * x[2] - x[0] * x[0])

        c_num = y2y0 * x1x0 - y1y0 * x2x0
        c_denom = x2x0sq * x1x0 - x1x0sq * x2x0

        if c_denom == 0:
            print('Divide by zero error')
            return

        c = c_num / float(c_denom)
        if x1x0 == 0:
            print('Divide by zero error')
            return

        b = (y1y0 - c * x1x0sq) / float(x1x0)
        a = y[0] - b * x[0] - c * x[0] * x[0]

        fit = [a, b, c]
        if c == 0:
            xpeak = 0.
            print('Cannot find xpeak')
            return
        else:
            # Constrain the fit to be within these three points.
            xpeak = -b / (2.0 * c)
            if xpeak < x[0]:
                xpeak = float(x[0])
            if xpeak > x[2]:
                xpeak = float(x[2])

        return xpeak, fit


    # ----------------------------------------------------------------------
    # Apply image registration
    def apply_image_registration(self, image, xshift, yshift):

        shape = image.shape
        nx = shape[0]
        ny = shape[1]

        outofboundariesval = np.sum(image) / float(nx * ny)
        shifted_img = interpolation.shift(image, [xshift, yshift],
                                                        mode='constant',
                                                        cval=outofboundariesval)

        return shifted_img





class File_GUI():
    """
    Ask user to choose file and then use an appropriate plugin to read and return a data structure.
    """
    def __init__(self):
        #self.last_path = dict([a,dict([t,os.getcwd()] for t in file_plugins.data_types)] for a in file_plugins.actions)
        self.last_filter = 0 #dict([a,dict([t,0] for t in file_plugins.data_types)] for a in file_plugins.actions)
        self.supported_filters = file_plugins.supported_filters
        self.filter_list = file_plugins.filter_list
        self.option_write_json = False
        #print(self.filter_list)


    def SelectFile(self):

        dlg = QtWidgets.QFileDialog(None)
        dlg.setWindowTitle('Choose File')
        dlg.setViewMode(QtWidgets.QFileDialog.Detail)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)

        #dlg.setDirectory(self.last_path)
        dlg.setNameFilters(self.filter_list)
        dlg.selectNameFilter(self.filter_list[self.last_filter])
        if dlg.exec_(): #if not cancelled
            self.last_path = os.path.split(str(dlg.selectedFiles()[0]))[0]
            chosen_plugin = None

            checklist = self.filter_list[1:-1] #take into account the extra "Supported" and "All" filter entries

            for i,filt in enumerate(checklist):
                print(i, filt, dlg.selectedNameFilter())
                if filt == dlg.selectedNameFilter():
                    chosen_plugin = file_plugins.supported_plugins[i]
                    break
            if chosen_plugin is not None:
                self.last_filter = i
            return (str(dlg.selectedFiles()[0]),chosen_plugin)
        else:
            return (None,None)


#-----------------------------------------------------------------------
    class DataChoiceDialog(QtWidgets.QDialog):

        def __init__(self,filepath=None,filestruct=None,plugin=None):
            super(File_GUI.DataChoiceDialog, self).__init__()
            self.filepath = filepath
            self.selection = None
            self.setWindowTitle('Choose Dataset')

            # A vertical box layout containing rows
            self.MainSizer = QtWidgets.QVBoxLayout()
            hbox1 = QtWidgets.QHBoxLayout()
            hbox2 = QtWidgets.QHBoxLayout()
            hbox3 = QtWidgets.QHBoxLayout()
            hbox4 = QtWidgets.QHBoxLayout()

            # Add the widgets to the first row
            hbox1.addWidget(QtWidgets.QLabel("Path:"))
            self.Path_text = QtWidgets.QLabel("")
            hbox1.addWidget(self.Path_text,stretch=1)
            self.MainSizer.addLayout(hbox1)

            # Add the widgets to the second row
            hbox2.addWidget(QtWidgets.QLabel('File:'))
            self.File_text = QtWidgets.QLineEdit(self)
            hbox2.addWidget(self.File_text,stretch=1)
            browse_button = QtWidgets.QPushButton('Browse...')
            browse_button.clicked.connect(self.OnBrowse)
            hbox2.addWidget(browse_button)
            self.MainSizer.addLayout(hbox2)

            # Add the widgets to the third row - dynamic set of widgets to display file info
            self.Entry_info = File_GUI.EntryInfoBox()
            self.MainSizer.addWidget(self.Entry_info)

            # Add widgets for the fourth row - just OK, cancel buttons
            self.jsoncheck = QtWidgets.QCheckBox("Write Data Structure to JSON-file (for .HDR only!)")
            self.jsoncheck.clicked.connect(self.setChecked)
            hbox4.addWidget(self.jsoncheck)
            self.jsoncheck.setChecked(File_GUI.option_write_json)
            if plugin.title not in ['SDF']:
                self.jsoncheck.hide()
            hbox4.addStretch(1)
            self.button_ok = QtWidgets.QPushButton('Accept')
            self.button_ok.clicked.connect(self.OnAccept)
            self.button_ok.setEnabled(False)
            hbox4.addWidget(self.button_ok)
            button_cancel = QtWidgets.QPushButton('Cancel')
            button_cancel.clicked.connect(self.close)
            hbox4.addWidget(button_cancel)
            self.MainSizer.addLayout(hbox4)

            # Set self.MainSizer as the layout for the window
            self.setLayout(self.MainSizer)
            self.setModal(True)
            #self.show()

            if filepath is not None:
                path, filename = os.path.split(str(self.filepath))
                self.Path_text.setText(path)
                self.File_text.setText(filename)
                if filestruct is None:
                    self.contents = file_plugins.GetFileStructure(str(self.filepath))

                else:
                    self.contents = filestruct
                self.Entry_info.UpdateInfo(self.contents)

        def setChecked(self,value=True):
            File_GUI.option_write_json = value
            self.jsoncheck.setChecked(value)

        def OnAccept(self):
            self.selection = self.Entry_info.GetSelection()
            if len(self.selection) == 0:
                self.close() #accepting with no regions selected is the same as clicking 'cancel'
            else:
                self.accept()

        def OnBrowse(self):
            filepath, plugin = File_GUI.SelectFile()
            if filepath is None:
                return
            path, filename = os.path.split(str(filepath))
            self.filepath = str(filepath)
            self.Path_text.setText(path)
            self.File_text.setText(filename)
            self.contents = file_plugins.GetFileStructure(str(filepath),plugin=plugin)
            if self.contents is None:
                self.selection = [(0,0)]
                self.accept()
            else:
                self.Entry_info.UpdateInfo(self.contents)


    #-------------------------------------
    class InfoItem(QtWidgets.QHBoxLayout):
        '''Row of widgets describing the contents of a file entry that appear within the EntryInfoBox'''
        def __init__(self,name,contents,allowed_application_definitions,index):
            super(File_GUI.InfoItem, self).__init__()
            self.valid_flag = self.checkValidity(contents,allowed_application_definitions)
            self.index = index
            self.populate(name,contents)

        def populate(self,name,contents):
            self.checkbox = QtWidgets.QCheckBox(name+' ('+str(contents.definition)+':'+str(contents.scan_type)+')')
            self.checkbox.clicked.connect(self.setChecked)
            self.addWidget(self.checkbox)
            self.addStretch(1)
            self.addWidget(QtWidgets.QLabel('Channels:'))
            self.channel_combobox = QtWidgets.QComboBox()
            for c in contents:
                self.channel_combobox.addItem(c)
            self.addWidget(self.channel_combobox)
            self.addStretch(1)
            Data_Size_Label = QtWidgets.QLabel('Points: '+str(contents.data_shape))
            if contents.data_axes is not None:
                Data_Size_Label.setToolTip(' | '.join(contents.data_axes))
            self.addWidget(Data_Size_Label)
            if not self.valid_flag:
                self.checkbox.setEnabled(False)
                self.channel_combobox.setEnabled(False)

        def setChecked(self,value=True):
            self.checkbox.setChecked(value)

        def isEnabled(self):
            return self.checkbox.isEnabled()

        def isValid(self):
            return self.valid_flag

        def checkValidity(self,contents,allowed_application_definitions):
            '''Check if data file entry appears to have the correct structure.'''
            return True
            #if contents.definition in allowed_application_definitions and contents.scan_type is not None and contents.data_shape is not None and contents.data_axes is not None:
                #return True
            #else:
                #return False

        def GetStatus(self):
            return (self.checkbox.isChecked(),self.channel_combobox.currentIndex())

    #---------------------------------------
    class EntryInfoBox(QtWidgets.QGroupBox):
        '''Widgets giving a summary of the contents of a file via an InfoItem object per file entry.'''
        def __init__(self):
            super(File_GUI.EntryInfoBox, self).__init__('File Summary')
            self.vbox = QtWidgets.QVBoxLayout()
            self.setLayout(self.vbox)
            self.valid_entry_flag = False
            self.selection = (0,0)

        def ClearAll(self):
            # Cycle through children and mark for deletion
            while self.vbox.count():
                row = self.vbox.takeAt(0)
                while row.count():
                    item = row.takeAt(0)
                    if item.widget() is not None:
                        item.widget().deleteLater()
            self.valid_entry_flag = False

        def UpdateInfo(self, FileContents):
            self.ClearAll()
            # Now popoulate widgets representing file contents
            for i,entry in enumerate(FileContents):
                entryCheckBox = File_GUI.InfoItem(entry,FileContents[entry],['NXstxm'],i)
                self.vbox.addLayout(entryCheckBox)
                if self.valid_entry_flag is False and entryCheckBox.isValid() is True:
                    entryCheckBox.setChecked(True)
                    self.valid_entry_flag = True
                    self.parent().button_ok.setEnabled(True)

        def GetSelection(self):
            selection = []
            for i in range(self.vbox.count()):
                status = self.vbox.itemAt(i).GetStatus()
                if status[0]:
                    selection.append((i,status[1])) # (region,detector)
            return selection

File_GUI = File_GUI() #Create instance so that object can remember things (e.g. last path)


""" ------------------------------------------------------------------------------------------------"""
class ToolBarWidget(QtWidgets.QDockWidget):
    def __init__(self, parent):
        super(ToolBarWidget, self).__init__()

        self.parent = parent

        self.initUI()


    #----------------------------------------------------------------------
    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.setFixedSize(200, 430)
        self.setWindowTitle('Toolbar')

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        vbox1 = QtWidgets.QVBoxLayout()

        self.dataset_names = ['None']
        sizer1 = QtWidgets.QGroupBox('Dataset 1')
        vboxs1 = QtWidgets.QVBoxLayout()
        self.cb_data1 = QtWidgets.QComboBox(self)
        self.cb_data1.addItems(self.dataset_names)
        self.cb_data1.currentIndexChanged.connect(self.OnData1)
        vboxs1.addWidget(self.cb_data1)
        sizer1.setLayout(vboxs1)
        vbox1.addWidget(sizer1)


        sizer2 = QtWidgets.QGroupBox('Dataset 2')
        vboxs2 = QtWidgets.QVBoxLayout()
        self.cb_data2 = QtWidgets.QComboBox(self)
        self.cb_data2.addItems(self.dataset_names)
        self.cb_data2.currentIndexChanged.connect(self.OnData2)
        vboxs2.addWidget(self.cb_data2)
        sizer2.setLayout(vboxs2)
        vbox1.addWidget(sizer2)

        b_register = QtWidgets.QPushButton('Register Images')
        b_register.clicked.connect(self.OnRegisterImages)
        vbox1.addWidget(b_register)

        vbox1.addSpacing(15)
        self.cb_scalebar = QtWidgets.QCheckBox('Show Scalebar', self)
        self.cb_scalebar.setChecked(self.parent.show_scale_bar)
        self.cb_scalebar.stateChanged.connect(self.OnShowScalebar)
        vbox1.addWidget(self.cb_scalebar)
        self.cb_colorbar = QtWidgets.QCheckBox('Show Colorbar', self)
        self.cb_colorbar.setChecked(self.parent.show_color_bar)
        self.cb_colorbar.stateChanged.connect(self.OnShowColorbar)
        vbox1.addWidget(self.cb_colorbar)

        sizer3 = QtWidgets.QGroupBox('RGB Map')
        vboxs3 = QtWidgets.QVBoxLayout()
        self.cb_rgb = QtWidgets.QCheckBox('Show RBG', self)
        self.cb_rgb.stateChanged.connect(self.OnShowRBG)
        vboxs3.addWidget(self.cb_rgb)
        vboxs3.addWidget(QtWidgets.QLabel('Red:'))
        self.cb_red = QtWidgets.QComboBox(self)
        self.cb_red.currentIndexChanged.connect(self.OnRGBCChanged)
        vboxs3.addWidget(self.cb_red)
        vboxs3.addWidget(QtWidgets.QLabel('Green:'))
        self.cb_green = QtWidgets.QComboBox(self)
        self.cb_green.currentIndexChanged.connect(self.OnRGBCChanged)
        vboxs3.addWidget(self.cb_green)
        vboxs3.addWidget(QtWidgets.QLabel('Blue:'))
        self.cb_blue = QtWidgets.QComboBox(self)
        self.cb_blue.currentIndexChanged.connect(self.OnRGBCChanged)
        vboxs3.addWidget(self.cb_blue)

        sizer3.setLayout(vboxs3)
        vbox1.addWidget(sizer3)

        vbox1.addStretch(1)
        frame.setLayout(vbox1)
        self.setWidget(frame)
        self.setFloating(True)


    def AddData(self, data_store_type):

        self.dataset_names.append(data_store_type)
        self.cb_data1.addItem(data_store_type)

        self.cb_data2.addItem(data_store_type)
        if len(self.dataset_names) == 2:
            self.cb_data1.setCurrentIndex(1)
        else:
            self.cb_data2.setCurrentIndex(len(self.dataset_names)-1)


    def RemoveData(self, data_index):
        del self.dataset_names[data_index]

        self.cb_data1.removeItem(data_index+1)
        self.cb_data2.removeItem(data_index+1)

    def OnData1(self):
        self.parent.i_selected_dataset1 = self.cb_data1.currentIndex() - 1
        self.parent.ShowImage()


    def OnData2(self):
        self.parent.i_selected_dataset2 = self.cb_data2.currentIndex() - 1
        self.parent.ShowImage()


    def OnRegisterImages(self):
        self.parent.RegisterImages()

    def OnShowScalebar(self):
        if self.cb_scalebar.isChecked():
            self.parent.show_scale_bar = 1
        else:
            self.parent.show_scale_bar = 0
        self.parent.ShowImage()

    def OnShowColorbar(self):
        if self.cb_colorbar.isChecked():
            self.parent.show_color_bar = 1
        else:
            self.parent.show_color_bar = 0
        self.parent.ShowImage()

    def OnShowRBG(self):
        if self.cb_rgb.isChecked():
            self.parent.show_rgb = True
        else:
            self.parent.show_rgb = False
        self.parent.ShowImage()

    def AddRBGChannels(self, channel_list):
        self.cb_red.addItems(channel_list)
        self.cb_red.setCurrentIndex(self.parent.red_ch)
        self.cb_green.addItems(channel_list)
        self.cb_green.setCurrentIndex(self.parent.green_ch)
        self.cb_blue.addItems(channel_list)
        self.cb_blue.setCurrentIndex(self.parent.blue_ch)

    def OnRGBCChanged(self):
        self.parent.red_ch = self.cb_red.currentIndex()
        self.parent.green_ch = self.cb_green.currentIndex()
        self.parent.blue_ch = self.cb_blue.currentIndex()
        self.parent.ShowImage()

    def close(self):
        self.hide()


""" ------------------------------------------------------------------------------------------------"""
class DataViewerWidget(QtWidgets.QDockWidget):
    def __init__(self, parent, data_store, data_index):
        super(DataViewerWidget, self).__init__()

        self.parent = parent
        self.data = data_store
        self.data_type = self.data.data_type

        self.data_index = data_index

        self.initUI()


    #----------------------------------------------------------------------
    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.setFixedSize(200, 300)
        self.setWindowTitle(os.path.splitext(os.path.basename(self.data.filename))[0])

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        vbox1 = QtWidgets.QVBoxLayout()

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addStretch(1)
        self.l_data_type = QtWidgets.QLabel(self)
        self.l_data_type.setText(self.data_type)
        font = self.l_data_type.font()
        font.setBold(True)
        font.setPointSize(10)
        self.l_data_type.setFont(font)
        self.l_data_type.setToolTip('Data Type')
        hbox1.addWidget(self.l_data_type, alignment=Qt.AlignCenter)
        hbox1.addStretch(1)

        self.button_popup = QtWidgets.QPushButton()
        self.button_popup.setIcon(QtGui.QIcon(os.path.join('resources','popup-menu-sm.png')))
        self.button_popup.setFixedWidth(25)
        self.button_popup.setFixedHeight(25)
        #self.button_popup.setFlat(True)
        self.button_popup.clicked.connect(self.on_context_menu)
        self.button_popup.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        hbox1.addWidget(self.button_popup, alignment=Qt.AlignRight)

        # create context menu
        action_mirrorud = QtWidgets.QAction('Data mirror Up-Down', self)
        action_mirrorud.triggered.connect(self.OnMirrorUD)
        action_mirrorlf = QtWidgets.QAction('Data mirror Left-Right', self)
        action_mirrorlf.triggered.connect(self.OnMirrorLR)
        self.popMenu = QtWidgets.QMenu(self)
        self.popMenu.addAction(action_mirrorud)
        self.popMenu.addAction(action_mirrorlf)
        vbox1.addLayout(hbox1)

        self.imgLabel = QtWidgets.QLabel()
        vbox1.addWidget(self.imgLabel)

        self.cb_peaks = QtWidgets.QComboBox(self)
        self.cb_peaks.addItems(self.data.peaks)
        self.cb_peaks.setCurrentIndex(self.parent.data_channel[-1])
        self.cb_peaks.currentIndexChanged.connect(self.OnPeakChange)
        vbox1.addWidget(self.cb_peaks)

        self.cmaps = ["gray","jet","autumn","bone", "cool","copper", "flag","hot","hsv","pink", "prism","spring",
                      "summer","winter"]

        hbox1 = QtWidgets.QHBoxLayout()
        st = QtWidgets.QLabel('Colormap:')
        hbox1.addWidget(st)
        self.cb_cmap = QtWidgets.QComboBox(self)
        self.cb_cmap.addItems(self.cmaps)
        self.cb_cmap.setCurrentIndex(0)
        self.cb_cmap.currentIndexChanged.connect(self.OnCmapChange)
        hbox1.addWidget(self.cb_cmap)
        vbox1.addLayout(hbox1)

        self.cb_despike = QtWidgets.QCheckBox('Despike', self)
        if self.data.despike == 1:
            self.cb_despike.setChecked(False)
        self.cb_despike.stateChanged.connect(self.OnDespike)
        vbox1.addWidget(self.cb_despike)

        hbox2 = QtWidgets.QHBoxLayout()
        self.tc_thrmax = QtWidgets.QLabel(self)
        self.tc_thrmax.setText('Threshold:')
        hbox2.addWidget(self.tc_thrmax)
        self.sl_thresh = QRangeSlider()
        self.sl_thresh.setMaximumHeight(25)
        self.sl_thresh.endValueChanged[int].connect(self.SetThreshRangeEnd)
        self.sl_thresh.startValueChanged[int].connect(self.SetThreshRangeStart)

        # self.slider_thrmax = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        # self.slider_thrmax.setRange(1, 100)
        # self.slider_thrmax.setValue(100)
        # self.slider_thrmax.setFocusPolicy(QtCore.Qt.StrongFocus)
        # self.slider_thrmax.valueChanged[int].connect(self.OnThreshold)
        hbox2.addWidget(self.sl_thresh)
        vbox1.addLayout(hbox2)

        hbox3 = QtWidgets.QHBoxLayout()
        self.l_gamma = QtWidgets.QLabel(self)
        self.l_gamma.setText('Gamma: {0:5.2f}'.format(self.data.gamma))
        hbox3.addWidget(self.l_gamma)
        self.sl_gamma = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.sl_gamma.setRange(1, 20)
        self.sl_gamma.setValue(int(self.data.gamma*10))
        self.sl_gamma.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.sl_gamma.valueChanged[int].connect(self.OnScrollGamma)
        self.sl_gamma.setMinimumWidth(100)
        hbox3.addWidget(self.sl_gamma)
        vbox1.addLayout(hbox3)

        b_histogramchannel = QtWidgets.QPushButton('Show Counts/Channel')
        # b_histogramchannel.setMaximumWidth(220)
        b_histogramchannel.clicked.connect(self.OnShowHistogramPerChannel)
        vbox1.addWidget(b_histogramchannel)
        b_histogram = QtWidgets.QPushButton('Show Histogram')
        # b_histogram.setMaximumWidth(220)
        b_histogram.clicked.connect(self.OnShowHistogram)
        vbox1.addWidget(b_histogram)

        frame.setLayout(vbox1)
        self.setWidget(frame)
        self.setFloating(True)

        self.GetImage()


    def on_context_menu(self, event):
        cursor = QtGui.QCursor()
        self.popMenu.exec_(cursor.pos())

    def SetThreshRangeEnd(self, val):
        self.data.threshold[1] = float(val)
        self.parent.ShowImage()

    def SetThreshRangeStart(self, val):
        self.data.threshold[0] = float(val)
        self.parent.ShowImage()

    def OnScrollGamma(self, value):
        self.data.gamma = float(value) / 10.0
        self.l_gamma.setText('Gamma: {0:5.2f}'.format(self.data.gamma))
        self.parent.ShowImage()

    def GetImage(self):
        self.image = median_filter(self.data.image_data[
                                   self.parent.data_channel[self.data_index], :, :].T, size=5)
        self.image = (255*(self.image - np.min(self.image))/np.ptp(self.image)).astype(np.uint8)
        self.DisplayImage()


    def DisplayImage(self):

        qformat = QImage.Format_Grayscale8

        img = QImage(self.image,
                     self.image.shape[1],
                     self.image.shape[0],
                     self.image.strides[0],
                     qformat)
        #img = img.rgbSwapped()
        pixmap = QPixmap.fromImage(img)
        w = 100
        smaller_pixmap = pixmap.scaledToWidth(w, Qt.SmoothTransformation)


        self.imgLabel.setPixmap(smaller_pixmap)
        self.imgLabel.setAlignment(QtCore.Qt.AlignHCenter
                                 | QtCore.Qt.AlignVCenter)

    def OnPeakChange(self):

        old_data_channel = self.parent.data_channel[self.data_index]
        self.parent.data_channel[self.data_index] = self.cb_peaks.currentIndex()
        if old_data_channel != self.parent.data_channel[self.data_index]:
            self.parent.ShowImage()

    def OnCmapChange(self):

        old_cmap = self.parent.data_cmap[self.data_index]
        self.parent.data_cmap[self.data_index] = self.cb_cmap.currentText()
        if old_cmap != self.parent.data_cmap[self.data_index]:
            self.parent.ShowImage()


    def OnMirrorUD(self):
        self.data.MirrorUD()
        self.parent.ShowImage()

    def OnMirrorLR(self):
        self.data.MirrorLR()
        self.parent.ShowImage()

    def OnDespike(self):
        if self.cb_despike.isChecked():
            self.data.despike = 1
        else:
            self.data.despike = 0
        self.parent.ShowImage()

    def OnShowHistogramPerChannel(self):
        hist_dialog = ShowHistogramPerChannel(self, self.data)
        hist_dialog.show()

    def OnShowHistogram(self):
        data_channel = self.parent.data_channel[self.data_index]
        data_channel_name = self.data.peaks[data_channel]
        image_data = self.parent.GetImage(self.data, data_channel)
        hist_dialog = ShowHistogram(self, image_data, data_channel_name)
        hist_dialog.show()

    def closeEvent(self, event):

        returnValue = QtWidgets.QMessageBox.question(self, 'Close dataset', "Are you sure to close the dataset?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if returnValue == QtWidgets.QMessageBox.Yes:
            self.parent.CloseDataset(self.data_index)
        else:
            event.ignore()



class ViewerFrame(QtWidgets.QWidget):

    def __init__(self, parent):
        super(ViewerFrame, self).__init__(parent)
        self.parent = parent

        vboxtop = QtWidgets.QVBoxLayout(self)

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        fbox = QtWidgets.QHBoxLayout()

        self.imgfig = Figure((PlotH*0.9, PlotH*0.9))

        self.ImagePanel = FigureCanvas(self.imgfig)
        self.ImagePanel.setParent(self)

        fbox.addWidget(self.ImagePanel)
        frame.setLayout(fbox)
        vboxtop.addWidget(frame)
        toolbar = NavigationToolbar(self.ImagePanel, self)
        vboxtop.addWidget(toolbar)

        self.setLayout(vboxtop)


    #-----------------------------------------------------------------------
    def ShowImage(self, image1, image2, scale_bar_string, scale_bar_pixels_x, scale_bar_pixels_y,
                  cmap1='gray', cmap2='gray', cblabel1='', cblabel2='',
                  show_rgb=False):

        if image1 is None and image2 is None:
            fig = self.imgfig
            fig.clf()
            self.ImagePanel.draw()
            return

        fig = self.imgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        axes = fig.gca()
        fig.patch.set_alpha(1.0)

        if self.parent.show_color_bar:
            divider = make_axes_locatable(axes)
            axes.set_position([0.03,0.03,0.8,0.94])

        n_cols = 0
        alpha = 1
        if show_rgb:
            im = axes.imshow(image1)
            n_cols = image1.shape[0]
            if image2 is not None:
                im = axes.imshow(image2, alpha=0.5)
                if n_cols == 0:
                    n_cols = image2.shape[0]
        else:
            if image1 is not None:
                im1 = axes.imshow(image1.T, cmap=matplotlib.cm.get_cmap(cmap1))
                if self.parent.show_color_bar:
                    ax_cb1 = divider.append_axes("right", size="3%", pad="2%")
                    cbar1 = axes.figure.colorbar(im1, cax=ax_cb1)
                n_cols = image1.shape[1]
                alpha = 0.5
            if image2 is not None:
                im2 = axes.imshow(image2.T, cmap=matplotlib.cm.get_cmap(cmap2), alpha=alpha)
                if self.parent.show_color_bar:
                    ax_cb2 = divider.append_axes("right", size="3%", pad="12%")
                    cbar2 = axes.figure.colorbar(im2, cax=ax_cb2)
                    if image1 is not None:
                        cbar1.set_label(cblabel1)
                    cbar2.set_label(cblabel2)
                if n_cols == 0:
                    n_cols = image2.shape[1]

        if self.parent.show_scale_bar == 1:
            #um_string = ' $\mathrm{\mu m}$'
            mm_string = ' $\mathrm{mm}$'
            microns = '$'+scale_bar_string+' $'+mm_string
            axes.text(scale_bar_pixels_x+10, n_cols-9, microns, horizontalalignment='left',
                      verticalalignment='center', color ='white', fontsize=14)
            # Matplotlib has flipped scales so I'm using rows instead of cols!
            p = matplotlib.patches.Rectangle((5, n_cols-10), scale_bar_pixels_x, scale_bar_pixels_y,
                                   color='white', fill=True)
            axes.add_patch(p)


        axes.axis("off")
        self.ImagePanel.draw()


""" ------------------------------------------------------------------------------------------------"""
class MainFrame(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainFrame, self).__init__()

        self.data_objects = []
        self.data_widgets = []
        self.i_selected_dataset1 = -1
        self.i_selected_dataset2 = -1
        self.data_channel = []
        self.data_cmap = []
        self.data_names = []

        self.show_scale_bar = 1
        self.scale_bar_string = ''
        self.scale_bar_pixels_x = 0
        self.scale_bar_pixels_y = 0

        self.show_color_bar = 1

        self.show_rgb = False
        self.red_ch = 0
        self.green_ch = 0
        self.blue_ch = 0
        self.channel_list = []

        self.transform = None
        self.data_transform = None

        self.initUI()


    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.resize(Winsizex, Winsizey)
        self.setWindowTitle('PyElements v.{0}'.format(version))

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks | QtWidgets.QMainWindow.AllowNestedDocks)

        self.viewer = ViewerFrame(self)
        self.setCentralWidget(self.viewer)

        self.initMainTopToolbar()

        self.tb_widget = ToolBarWidget(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tb_widget)

        self.show()

        if sys.platform == "darwin":
            self.raise_()


    def initMainTopToolbar(self):

        self.maintoolbar = self.addToolBar('MainToolbar')
        self.maintoolbar.setStyleSheet('QToolBar{spacing:3px;}')

        self.actionBrowser = QtWidgets.QAction(self)
        self.actionBrowser.setIcon(QtGui.QIcon(os.path.join('resources','openfolder.png')))
        self.actionBrowser.setToolTip('Load Data')
        self.maintoolbar.addAction(self.actionBrowser)
        self.actionBrowser.triggered.connect(self.OnLoadStack)

        self.actionToolbar = QtWidgets.QAction(self)
        self.actionToolbar.setIcon(QtGui.QIcon(os.path.join('resources','settings.png')))
        self.actionToolbar.setToolTip('Toolbar')
        self.maintoolbar.addAction(self.actionToolbar)
        self.actionToolbar.triggered.connect(self.OnToolbarTB)

        # spacer = QtWidgets.QWidget()
        # spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # self.maintoolbar.addWidget(spacer)
        #
        # self.actionHelp = QtWidgets.QAction(self)
        # self.actionHelp.setIcon(QtGui.QIcon(os.path.join('resources','help.png')))
        # self.actionHelp.setToolTip('Help')
        # self.maintoolbar.addAction(self.actionHelp)
        # #self.actionHelp.triggered.connect(self.HelpTB)
        #
        # self.actionAbout = QtWidgets.QAction(self)
        # self.actionAbout.setIcon(QtGui.QIcon(os.path.join('resources','info.png')))
        # self.actionAbout.setToolTip('About')
        # self.maintoolbar.addAction(self.actionAbout)
        # #self.actionAbout.triggered.connect(self.AboutTB)


    def OnLoadStack(self):
        """
        Browse for a data file:
        """

        filepath, plugin = File_GUI.SelectFile()
        if filepath is not None:
            if plugin is None:  # auto-assign appropriate plugin
                plugin = file_plugins.identify(filepath)

            if plugin is None:
                QtWidgets.QMessageBox.warning(self, 'Error!', "Unknown file type")

            QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))

            data = data_store.DataStore()

            file_plugins.load(filepath, datastore_object=data, plugin=plugin)
            self.data_objects.append(data)

            if data.data_type == 'XFM':
                self.data_channel.append(len(data.peaks) - 2)
            else:
                self.data_channel.append(78)

            self.data_names.append(data.data_type)
            self.data_cmap.append('gray')

            datawin = DataViewerWidget(self, data, len(self.data_objects) - 1)
            self.addDockWidget(Qt.TopDockWidgetArea, datawin)

            self.tb_widget.AddData(data.data_type)
            self.UpdateChannelList(data.data_type, data)
            self.tb_widget.AddRBGChannels(self.channel_list)
            self.data_widgets.append(datawin)

            if len(self.data_objects) == 1:
                self.i_selected_dataset1 = 0
                self.CalcScaleBar()

            if len(self.data_objects) > 1:
                self.i_selected_dataset2 = len(self.data_objects) - 1

            self.ShowImage()

            QtWidgets.QApplication.restoreOverrideCursor()


    def UpdateChannelList(self, data_type, data):
        for i in range(len(data.peaks)):
            self.channel_list.append('{0}: {1}'.format(data_type, data.peaks[i]))

    def CloseDataset(self, dataindex):
        print('Closing dataset {0}'.format(self.data_objects[dataindex].filename))

        oldindex1 = self.i_selected_dataset1
        oldindex2 = self.i_selected_dataset2

        self.tb_widget.RemoveData(dataindex)

        if len(self.data_objects) == 1:
            self.data_objects = []
            self.data_widgets = []
            self.i_selected_dataset1 = -1
            self.i_selected_dataset2 = -1
            self.data_channel = []
        else:
            del self.data_objects[dataindex]
            del self.data_widgets[dataindex]
            del self.data_channel[dataindex]

        self.ShowImage()

    def GetImage(self, data, data_channel):
        img = None
        img = data.image_data[data_channel, :, :].copy()
        if data.despike == 1:
            img = despike(img)
        if data.threshold[1] != 100 or data.threshold[0] != 0:
            imgmax = np.amax(img)
            thrnum = imgmax*data.threshold[1]/100.
            img[img > thrnum] = thrnum
            thrnum = imgmax*data.threshold[0]/100.
            img[img < thrnum] = thrnum

        if (data.gamma != 1.0):
            img[img<0] = 0
            img = np.power(img, data.gamma)
        data.display_image = img
        return img

    def ShowImage(self):

        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
        image1 = None
        image2 = None
        cmap1 = ''
        cmap2 = ''
        cbl1 = ''
        cbl2 = ''
        if self.show_rgb is False:
            if self.i_selected_dataset1 >= 0:
                if len(self.data_objects) > 0:
                    data = self.data_objects[self.i_selected_dataset1]
                    image1 = self.GetImage(data, self.data_channel[self.i_selected_dataset1])
                    cmap1 = self.data_cmap[self.i_selected_dataset1]
                    cbl1 = self.data_objects[self.i_selected_dataset1].data_type

            if len(self.data_objects) > 0:
                if self.i_selected_dataset2 >= 0:
                    data = self.data_objects[self.i_selected_dataset2]
                    image2 = self.GetImage(data, self.data_channel[self.i_selected_dataset2])
                    cmap2 = self.data_cmap[self.i_selected_dataset2]
                    cbl2 = self.data_objects[self.i_selected_dataset2].data_type
                    # if self.data_transform is not None:
                    #     h1, w1 = image1.shape[:2]
                    #     if self.transform == 'affine':
                    #         image2 = cv2.warpAffine(image2, self.data_transform, (w1, h1))
                    #     else:
                    #         image2 = cv2.warpPerspective(image2, self.data_transform, (w1, h1),
                    #                                         flags=cv2.INTER_LINEAR)
        else:
            image1 = np.zeros((self.data_objects[0].ny, self.data_objects[0].nx, 3),
                              dtype=self.data_objects[0].image_data.dtype)
            im1scale = 255
            if self.data_objects[0].image_data.dtype in [np.float32, np.float64, float]:
                im1scale = 1
            if len(self.data_objects) > 1:
                image2 = np.zeros((self.data_objects[1].ny, self.data_objects[1].nx, 3),
                                  dtype=self.data_objects[1].image_data.dtype)
                im2scale = 255
                if self.data_objects[1].image_data.dtype in [np.float32, np.float64, float]:
                    im2scale = 1
            haveimg1 = False
            haveimg2 = False
            if self.red_ch < self.data_objects[0].np:
                r_ds = 0
                ir = self.red_ch
                r_image = self.GetImage(self.data_objects[r_ds], ir)
                image1[:,:,0] = r_image.T
                haveimg1 = True
            else:
                r_ds = 1
                ir = self.red_ch - self.data_objects[0].np
                r_image = self.GetImage(self.data_objects[r_ds], ir)
                image2[:, :, 0] = r_image.T
                haveimg2 = True

            if self.green_ch < self.data_objects[0].np:
                g_ds = 0
                ig = self.green_ch
                g_image = self.GetImage(self.data_objects[g_ds], ig)
                image1[:, :, 1] = g_image.T
                haveimg1 = True
            else:
                g_ds = 1
                ig = self.green_ch - self.data_objects[0].np
                g_image = self.GetImage(self.data_objects[g_ds], ig)
                image2[:, :, 1] = g_image.T
                haveimg2 = True

            if self.blue_ch < self.data_objects[0].np:
                b_ds = 0
                ib = self.blue_ch
                b_image = self.GetImage(self.data_objects[b_ds], ib)
                image1[:, :, 2] = b_image.T
                haveimg1 = True
            else:
                b_ds = 1
                ib = self.blue_ch - self.data_objects[0].np
                b_image = self.GetImage(self.data_objects[b_ds], ib)
                image2[:, :, 2] = b_image.T
                haveimg2 = True

            if not haveimg1 and haveimg2:
                image1 = image2
                image2 = None
                im1scale = im2scale
            if not haveimg2:
                image2 = None

            image1 -= image1.min()
            image1 *= (im1scale / image1.max())
            if image2 is not None:
                if self.data_transform is not None:
                    h1, w1 = image1.shape[:2]
                    if self.transform == 'affine':
                        image2 = cv2.warpAffine(image2, self.data_transform, (w1, h1))
                    else:
                        image2 = cv2.warpPerspective(image2, self.data_transform, (w1, h1),
                                                     flags=cv2.INTER_LINEAR)
                image2 -= image2.min()
                image2 *= (im2scale / image2.max())

        self.CalcScaleBar()
        self.viewer.ShowImage(image1, image2, self.scale_bar_string, self.scale_bar_pixels_x, self.scale_bar_pixels_y,
                              cmap1=cmap1, cmap2=cmap2, cblabel1=cbl1, cblabel2=cbl2,
                              show_rgb=self.show_rgb)
        QtWidgets.QApplication.restoreOverrideCursor()


    # ----------------------------------------------------------------------
    def CalcScaleBar(self):

        x_start = np.min(self.data_objects[self.i_selected_dataset1].x_coord)
        x_stop = np.max(self.data_objects[self.i_selected_dataset1].x_coord)

        if 'micro' in str(self.data_objects[self.i_selected_dataset1].motor_units):
            x_start = x_start/1000
            x_stop = x_stop/1000

        bar_mm = 0.2 * np.abs(x_stop - x_start)

        if bar_mm >= 10.:
            bar_mm = 10. * int(0.5 + 0.1 * int(0.5 + bar_mm))
            bar_string = str(int(0.01 + bar_mm)).strip()
        elif bar_mm >= 1.:
            bar_mm = float(int(0.5 + bar_mm))
            if bar_mm == 1.:
                bar_string = '1'
            else:
                bar_string = str(int(0.01 + bar_mm)).strip()
        else:
            bar_mm = np.maximum(0.1 * int(0.5 + 10 * bar_mm), 0.1)
            bar_string = str(bar_mm).strip()
        self.scale_bar_string = bar_string

        self.scale_bar_pixels_x = int(0.5 + float(self.data_objects[self.i_selected_dataset1].ny) *
                                      float(bar_mm) / float(abs(x_stop - x_start)))
        self.scale_bar_pixels_y = int(0.01 * self.data_objects[self.i_selected_dataset1].nx)
        if self.scale_bar_pixels_y < 2:
            self.scale_bar_pixels_y = 2



    def OnToolbarTB(self):

        self.tb_widget.show()

    def RegisterImages(self):
        image1 = None
        image2 = None
        if len(self.data_objects) > 0:
            if self.i_selected_dataset1 >= 0:
                data = self.data_objects[self.i_selected_dataset1]
                image1 = self.GetImage(data, self.data_channel[self.i_selected_dataset1])
            if self.i_selected_dataset2 >= 0:
                data = self.data_objects[self.i_selected_dataset2]
                image2 = self.GetImage(data, self.data_channel[self.i_selected_dataset2])
        imgregwin = ImageRegistrationDialog(self, image1, image2)
        imgregwin.show()

    def AlignData(self):
        if self.data_transform is not None:
            data1 = self.data_objects[0]
            data2 = self.data_objects[1]

            h1 = data1.nx
            w1 = data1.ny
            aligned_data = []
            for i in range(data2.np):
                image2 = data2.image_data[i, :, :]
                if self.transform == 'affine':
                    image2 = cv2.warpAffine(image2, self.data_transform, (w1, h1))
                else:
                    image2 = cv2.warpPerspective(image2, self.data_transform, (w1, h1),
                                                 flags=cv2.INTER_LINEAR)
                aligned_data.append(image2)
            self.data_objects[1].image_data = np.array(aligned_data)
            self.data_objects[1].nx = data1.nx
            self.data_objects[1].ny = data1.ny



    # def RegisterImagesCV(self):
    #     print('Registering images')
    #
    #     # Image to be aligned.
    #     data = self.data_objects[self.i_selected_dataset2]
    #     image2 = median_filter(data.image_data[self.data_channel[self.i_selected_dataset2], :, :], size=3)
    #     image2 = ((image2 - image2.min()) * (1/(image2.max() - image2.min()) * 255)).astype('uint8')
    #
    #     # Reference image.
    #     data = self.data_objects[self.i_selected_dataset1]
    #     image1 = median_filter(data.image_data[self.data_channel[self.i_selected_dataset1], :, :], size=3)
    #     image1 = ((image1 - image1.min()) * (1/(image1.max() - image1.min()) * 255)).astype('uint8')
    #
    #     # Create ORB detector with 5000 features.
    #     orb_detector = cv2.ORB_create(5000)
    #
    #     # Find keypoints and descriptors.
    #     # The first arg is the image, second arg is the mask
    #     #  (which is not required in this case).
    #     kp1, d1 = orb_detector.detectAndCompute(image2, None)
    #     kp2, d2 = orb_detector.detectAndCompute(image1, None)
    #
    #
    #
    #     # Match features between the two images.
    #     # We create a Brute Force matcher with
    #     # Hamming distance as measurement mode.
    #     matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck = True)
    #
    #     # Match the two sets of descriptors.
    #     matches = matcher.match(d1, d2)
    #     # Sort matches on the basis of their Hamming distance.
    #     matches = sorted(matches, key = lambda x:x.distance)
    #
    #     # Take the top 90 % matches forward.
    #     matches = matches[:int(len(matches)*0.9)]
    #     no_of_matches = len(matches)
    #
    #     print('no_of_matches', no_of_matches)
    #
    #     # Define empty matrices of shape no_of_matches * 2.
    #     p1 = np.zeros((no_of_matches, 2))
    #     p2 = np.zeros((no_of_matches, 2))
    #
    #     for i in range(len(matches)):
    #       p1[i, :] = kp1[matches[i].queryIdx].pt
    #       p2[i, :] = kp2[matches[i].trainIdx].pt
    #
    #     # Find the homography matrix.
    #     homography, mask = cv2.findHomography(p1, p2, cv2.RANSAC)
    #
    #     # Use this matrix to transform the
    #     # colored image wrt the reference image.
    #     transformed_img = cv2.warpPerspective(image2,
    #                         homography, (data.ny, data.nx))
    #
    #     self.viewer.ShowImage(image1, transformed_img, cmap1=self.data_cmap[self.i_selected_dataset1],
    #                           cmap2=self.data_cmap[self.i_selected_dataset2])

""" ------------------------------------------------------------------------------------------------"""
def main():

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = '1'
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    #app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))
    frame = MainFrame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()