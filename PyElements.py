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
import cv2
import numpy as np
from scipy.ndimage import median_filter
import file_plugins
import data_store


Winsizex = 1000
Winsizey = 800

PlotH = 4.0
PlotW = PlotH*1.61803

version = '0.0.1'


class ImageRegistrationDialog(QtWidgets.QDialog):

    def __init__(self, parent, image1, image2):
        super(ImageRegistrationDialog, self).__init__(parent)
        self.parent = parent

        self.parent = parent
        self.image1 = image1
        self.image2 = image2
        self.lpoints = []
        self.rpoints = []

        self.resize(1050, 750)
        self.setWindowTitle('Image Alignment')

        vboxtop = QtWidgets.QVBoxLayout()
        st = QtWidgets.QLabel('Select 3 points on the left image and 3 corresponding points on the right.')
        font = st.font()
        font.setBold(True)
        font.setPointSize(10)
        st.setFont(font)
        vboxtop.addWidget(st)

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
        button_save = QtWidgets.QPushButton('Apply')
        button_save.clicked.connect(self.OnApply)
        hboxb.addWidget(button_save)

        button_clear = QtWidgets.QPushButton('Clear Points')
        button_clear.clicked.connect(self.OnClear)
        hboxb.addWidget(button_clear)

        button_cancel = QtWidgets.QPushButton('Cancel')
        button_cancel.clicked.connect(self.close)
        hboxb.addWidget(button_cancel)

        button_save = QtWidgets.QPushButton('Save')
        button_save.clicked.connect(self.OnSave)
        hboxb.addWidget(button_save)

        vboxtop.addLayout(hboxb)

        self.setLayout(vboxtop)

        self.ShowImage(self.image1, self.image2)


    def ShowImage(self, image1, image2):

        if image1 is None or image2 is None:
            return

        fig = self.limgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        self.laxes = fig.gca()
        fig.patch.set_alpha(1.0)
        # despeckle the image
        dimage1 = median_filter(image1, size=3)
        im = self.laxes.imshow(dimage1.T, cmap=matplotlib.cm.get_cmap('gray'))
        self.laxes.axis("off")
        self.lImagePanel.draw()

        fig = self.rimgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        self.raxes = fig.gca()
        fig.patch.set_alpha(1.0)
        # despeckle the image
        dimage2 = median_filter(image2, size=3)
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
        self.t_status.clear()
        self.ShowImage(self.image1, self.image2)

    def OnApply(self):
        if len(self.lpoints) != 3 or len(self.rpoints) != 3:
            QtWidgets.QMessageBox.warning(self, 'Warning', "Please select exactly 3 points on the left and the right image.")
            return
        transform = 'affine'
        pts1 = np.float32(self.lpoints)
        pts2 = np.float32(self.rpoints)
        h1, w1 = self.image1.shape[:2]
        h2, w2 = self.image2.shape[:2]

        if transform == 'affine':
            H = cv2.getAffineTransform(pts2, pts1)
            al_image2 = cv2.warpAffine(self.image2, H, (w1, h1))
        else:
            H, status = cv2.findHomography(pts2, pts1)
            al_image2 = cv2.warpPerspective(self.image2, H, (w1, h1),
                                              flags=cv2.INTER_LINEAR)

        self.data_transform = H
        self.ShowImage(self.image1, al_image2)

    def OnSave(self):
        self.parent.data_transform = self.data_transform
        self.close()


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
        #dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)

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

        self.setFixedSize(120,300)
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

        self.setFixedSize(150, 220)
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
                      "summer","winter", "spectral"]

        st = QtWidgets.QLabel('Colormap:')
        vbox1.addWidget(st)
        self.cb_cmap = QtWidgets.QComboBox(self)
        self.cb_cmap.addItems(self.cmaps)
        self.cb_cmap.setCurrentIndex(0)
        self.cb_cmap.currentIndexChanged.connect(self.OnCmapChange)
        vbox1.addWidget(self.cb_cmap)

        frame.setLayout(vbox1)
        self.setWidget(frame)
        self.setFloating(True)

        self.GetImage()


    def on_context_menu(self, event):
        cursor = QtGui.QCursor()
        self.popMenu.exec_(cursor.pos())


    def GetImage(self):
        self.image = median_filter(self.data.image_data[
                                   self.parent.data_channel[self.data_index], :, :].T, size=3)
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

        self.setLayout(vboxtop)


#-----------------------------------------------------------------------
    def ShowImage(self, image1, image2, cmap1='gray', cmap2='gray'):

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

        if image1 is not None:
            # despeckle the image
            dimage1 = median_filter(image1, size=3)
            im = axes.imshow(dimage1.T, cmap=matplotlib.cm.get_cmap(cmap1))
        if image2 is not None:
            dimage2 = median_filter(image2, size=3)
            im = axes.imshow(dimage2.T, cmap=matplotlib.cm.get_cmap(cmap2), alpha=0.5)

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

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.maintoolbar.addWidget(spacer)

        self.actionHelp = QtWidgets.QAction(self)
        self.actionHelp.setIcon(QtGui.QIcon(os.path.join('resources','help.png')))
        self.actionHelp.setToolTip('Help')
        self.maintoolbar.addAction(self.actionHelp)
        #self.actionHelp.triggered.connect(self.HelpTB)

        self.actionAbout = QtWidgets.QAction(self)
        self.actionAbout.setIcon(QtGui.QIcon(os.path.join('resources','info.png')))
        self.actionAbout.setToolTip('About')
        self.maintoolbar.addAction(self.actionAbout)
        #self.actionAbout.triggered.connect(self.AboutTB)


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

            self.data_cmap.append('gray')

            datawin = DataViewerWidget(self, data, len(self.data_objects) - 1)
            self.addDockWidget(Qt.TopDockWidgetArea, datawin)

            self.tb_widget.AddData(data.data_type)
            self.data_widgets.append(datawin)

            if len(self.data_objects) == 1:
                self.i_selected_dataset1 = 0

            if len(self.data_objects) > 1:
                self.i_selected_dataset2 = len(self.data_objects) - 1

            self.ShowImage()

            QtWidgets.QApplication.restoreOverrideCursor()



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


    def ShowImage(self):

        image1 = None
        image2 = None
        cmap1 = ''
        cmap2 = ''
        if self.i_selected_dataset1 >= 0:
            if len(self.data_objects) > 0:
                data = self.data_objects[self.i_selected_dataset1]
                image1 = data.image_data[self.data_channel[self.i_selected_dataset1], :, :]
                cmap1 = self.data_cmap[self.i_selected_dataset1]
        if len(self.data_objects) > 0:
            if self.i_selected_dataset2 >= 0:
                data = self.data_objects[self.i_selected_dataset2]
                image2 = data.image_data[self.data_channel[self.i_selected_dataset2], :, :]
                cmap2 = self.data_cmap[self.i_selected_dataset2]
                if self.data_transform is not None:
                    h1, w1 = image1.shape[:2]
                    image2 = cv2.warpAffine(image2, self.data_transform, (w1, h1))

        self.viewer.ShowImage(image1, image2, cmap1=cmap1, cmap2=cmap2)



    def OnToolbarTB(self):

        self.tb_widget.show()

    def RegisterImages(self):
        image1 = None
        image2 = None
        cmap1 = ''
        cmap2 = ''
        if self.i_selected_dataset1 >= 0:
            if len(self.data_objects) > 0:
                data = self.data_objects[self.i_selected_dataset1]
                image1 = data.image_data[self.data_channel[self.i_selected_dataset1], :, :]
        if len(self.data_objects) > 0:
            if self.i_selected_dataset2 >= 0:
                data = self.data_objects[self.i_selected_dataset2]
                image2 = data.image_data[self.data_channel[self.i_selected_dataset2], :, :]

        imgregwin = ImageRegistrationDialog(self, image1, image2)
        imgregwin.show()



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

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))
    frame = MainFrame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()