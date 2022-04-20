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


#-----------------------------------------------------------------------
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
        print(file_plugins.supported_plugins)

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
class DataViewerWidget(QtWidgets.QDockWidget):
    def __init__(self, parent, data_store):
        super(DataViewerWidget, self).__init__()

        self.parent = parent
        self.data = data_store
        self.data_type = self.data.data_type

        self.initUI()


    #----------------------------------------------------------------------
    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.setFixedSize(150,220)
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
        action_info = QtWidgets.QAction('Info...', self)
        #action_info.setIcon(QtGui.QIcon(os.path.join('images','help.png')))
        #action_info.triggered.connect(self.OnInfo)
        action_setup = QtWidgets.QAction('Setup...', self)
        #action_setup.setIcon(QtGui.QIcon(os.path.join('images','settings.png')))
        #action_setup.triggered.connect(lambda: self.OnSetup(show_less=True))
        action_setupall = QtWidgets.QAction('Setup All...', self)
        #action_setupall.setIcon(QtGui.QIcon(os.path.join('images','settings.png')))
        #action_setupall.triggered.connect(lambda: self.OnSetup(show_less=False))
        self.popMenu = QtWidgets.QMenu(self)
        self.popMenu.addAction(action_info)
        self.popMenu.addAction(action_setup)
        self.popMenu.addAction(action_setupall)
        vbox1.addLayout(hbox1)


        # hbox1 = QtGui.QHBoxLayout()
        #
        # if not self.showdevice:
        #     self.position = PVFloatText()
        # else:
        #     self.position = PVFloatDeviceText()
        # font = self.position.font()
        # font.setPointSize(12)
        # self.position.setFont(font)
        # if have_epics:
        #     self.position.SetPV(self.emotor, 'RBV')
        # else:
        #     self.position.setText(rbv)
        # hbox1.addWidget(self.position, alignment=Qt.AlignCenter)
        #
        # if self.customdevice:
        #     if have_epics:
        #         if statuspv != '':
        #             self.l_status = PVStatus()
        #             self.l_status.SetPV(statuspv, status_update=self.CustomStatusUpdate)
        #
        #             value = statuspv.get()
        #             self.CustomStatusUpdate(value)
        #         else:
        #             self.l_status = QtGui.QLabel('')
        #     else:
        #         self.l_status = QtGui.QLabel('')
        #         self.l_status.setPixmap(QtGui.QPixmap(os.path.join('images','led_green.png')))
        #     self.l_status.setMaximumWidth(18)
        #     hbox1.addWidget(self.l_status)
        # vbox1.addLayout(hbox1)
        #
        # if not self.showdevice:
        #     self.ntc_new_position = PVFloatEdit()
        # else:
        #     self.ntc_new_position = PVFloatDeviceEdit()
        # # font = self.position.font()
        # # font.setPointSize(12)
        # # self.ntc_new_position.setFont(font)
        # if have_epics:
        #     self.ntc_new_position.SetPV(self.emotor, 'VAL')
        # else:
        #     self.ntc_new_position.setText(drive)
        #
        # vbox1.addWidget(self.ntc_new_position, alignment=Qt.AlignCenter)
        #
        # hbox2 = QtGui.QHBoxLayout()
        # self.button_reverse = QtGui.QPushButton()
        # self.button_reverse.setIcon(QtGui.QIcon(os.path.join('images','left.png')))
        # self.button_reverse.setMaximumWidth(30)
        # self.button_reverse.clicked.connect(self.OnReverse)
        # hbox2.addWidget(self.button_reverse)
        #
        # self.ntc_tweak = QtGui.QLineEdit(self)
        # self.ntc_tweak.setText(str(tweak_val))
        # self.ntc_tweak.setValidator(QtGui.QDoubleValidator(-99999999, 99999999, 5, self))
        # self.ntc_tweak.setAlignment(QtCore.Qt.AlignRight)
        # #self.ntc_tweak.returnPressed(self.OnTweakVal)
        # hbox2.addWidget(self.ntc_tweak, alignment=Qt.AlignCenter)
        #
        # self.button_forward = QtGui.QPushButton()
        # self.button_forward.setIcon(QtGui.QIcon(os.path.join('images','right.png')))
        # self.button_forward.setMaximumWidth(30)
        # self.button_forward.clicked.connect(self.OnForward)
        # hbox2.addWidget(self.button_forward)
        # vbox1.addLayout(hbox2)
        #
        # vbox1.addStretch(1)
        #
        # self.button_stop = QtGui.QPushButton('Stop')
        # self.button_stop.clicked.connect(self.OnStop)
        # if self.disable_stop:
        #     self.button_stop.setEnabled(False)
        # vbox1.addWidget(self.button_stop)

        self.imgLabel = QtWidgets.QLabel()
        vbox1.addWidget(self.imgLabel)

        vbox1.addStretch(1)
        frame.setLayout(vbox1)
        self.setWidget(frame)
        self.setFloating(True)

        self.GetImage()


    def on_context_menu(self, event):
        cursor = QtGui.QCursor()
        self.popMenu.exec_(cursor.pos())


    def GetImage(self):

        if self.data.data_type == 'XFM':
            channel = -2
        else:
            channel = 78
        self.image = median_filter(self.data.image_data[channel, :, :].T, size=3)

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



class ViewerFrame(QtWidgets.QWidget):

    def __init__(self, parent):
        super(ViewerFrame, self).__init__(parent)
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

        #
        # self.button1 = QtWidgets.QPushButton("Button 1")
        # self.layout.addWidget(self.button1)
        #
        # self.button2 = QtWidgets.QPushButton("Button 2")
        # self.layout.addWidget(self.button2)

        self.setLayout(vboxtop)


#-----------------------------------------------------------------------
    def ShowImage(self, image):

        # despeckle the image
        dimage = median_filter(image, size=3)

        fig = self.imgfig
        fig.clf()
        fig.add_axes(((0.0,0.0,1.0,1.0)))
        axes = fig.gca()
        fig.patch.set_alpha(1.0)

        im = axes.imshow(dimage.T, cmap=matplotlib.cm.get_cmap("gray"))

        axes.axis("off")
        self.ImagePanel.draw()



""" ------------------------------------------------------------------------------------------------"""
class MainFrame(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainFrame, self).__init__()

        self.initUI()


    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.resize(Winsizex, Winsizey)
        self.setWindowTitle('PyElements v.{0}'.format(version))

        #self.initToolbar()
        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks | QtWidgets.QMainWindow.AllowNestedDocks)

        self.viewer = ViewerFrame(self)
        self.setCentralWidget(self.viewer)

        self.initToolbar()


        self.show()

        if sys.platform == "darwin":
            self.raise_()


    def initToolbar(self):

        self.toolbar = self.addToolBar('MainToolbar')
        self.toolbar.setStyleSheet('QToolBar{spacing:3px;}')



        self.actionBrowser = QtWidgets.QAction(self)
        self.actionBrowser.setIcon(QtGui.QIcon(os.path.join('resources','openfolder.png')))
        self.actionBrowser.setToolTip('MDA Browser')
        self.toolbar.addAction(self.actionBrowser)
        self.actionBrowser.triggered.connect(self.OnLoadStack)

        self.actionSettings = QtWidgets.QAction(self)
        self.actionSettings.setIcon(QtGui.QIcon(os.path.join('resources','settings.png')))
        self.actionSettings.setToolTip('Settings')
        self.toolbar.addAction(self.actionSettings)
        #self.actionSettings.triggered.connect(self.SettingsTB)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.actionHelp = QtWidgets.QAction(self)
        self.actionHelp.setIcon(QtGui.QIcon(os.path.join('resources','help.png')))
        self.actionHelp.setToolTip('Help')
        self.toolbar.addAction(self.actionHelp)
        #self.actionHelp.triggered.connect(self.HelpTB)

        self.actionAbout = QtWidgets.QAction(self)
        self.actionAbout.setIcon(QtGui.QIcon(os.path.join('resources','info.png')))
        self.actionAbout.setToolTip('About')
        self.toolbar.addAction(self.actionAbout)
        #self.actionAbout.triggered.connect(self.AboutTB)


    def OnLoadStack(self):
        """
        Browse for a data file:
        """

        filepath, plugin = File_GUI.SelectFile()
        if filepath is not None:
            if plugin is None: # auto-assign appropriate plugin
                plugin = file_plugins.identify(filepath)

            if plugin is None:
                QtWidgets.QMessageBox.warning(self, 'Error!', "Unknown file type")

            QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))

            data = data_store.DataStore()

            file_plugins.load(filepath, datastore_object=data, plugin=plugin)

            directory = os.path.dirname(str(filepath))

            basename, extension = os.path.splitext(filepath)

            datawin = DataViewerWidget(self, data)
            self.addDockWidget(Qt.TopDockWidgetArea, datawin)

            if data.data_type == 'XFM':
                channel = -2
            else:
                channel = 78
            self.viewer.ShowImage(data.image_data[channel, :, :])

            QtWidgets.QApplication.restoreOverrideCursor()




""" ------------------------------------------------------------------------------------------------"""
def main():

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))
    frame = MainFrame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()