import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import cv2

Winsizex = 1700
Winsizey = 1000

version = '0.0.1'


""" ------------------------------------------------------------------------------------------------"""
class DataViewerWidget(QtWidgets.QDockWidget):
    def __init__(self, parent, filename):
        super(DataViewerWidget, self).__init__()

        self.parent = parent
        self.filename = filename

        self.data_type = 1

        self.initUI()




    #----------------------------------------------------------------------
    def initUI(self):

        self.setStyleSheet("""QToolTip { 
                                   background-color: black; 
                                   color: white; 
                                   border: black solid 1px
                                   }""")

        self.setFixedSize(150,220)
        self.setWindowTitle(os.path.splitext(os.path.basename(self.filename))[0])

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
        vbox1 = QtWidgets.QVBoxLayout()



        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addStretch(1)
        self.l_data_type = QtWidgets.QLabel(self)
        self.l_data_type.setText(self.parent.data_type_list[self.data_type])
        font = self.l_data_type.font()
        font.setBold(True)
        font.setPointSize(10)
        self.l_data_type.setFont(font)
        self.l_data_type.setToolTip('Data Type')
        hbox1.addWidget(self.l_data_type, alignment=Qt.AlignCenter)
        hbox1.addStretch(1)

        self.button_popup = QtWidgets.QPushButton()
        self.button_popup.setIcon(QtGui.QIcon(os.path.join('Resources','popup-menu-sm.png')))
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

        self.LoadImage(self.filename)


    def on_context_menu(self, event):
        cursor = QtGui.QCursor()
        self.popMenu.exec_(cursor.pos())


    def LoadImage(self, filename, ):
        self.image = cv2.imread(filename)
        self.DisplayImage()


    def DisplayImage(self):
        qformat = QImage.Format_Indexed8

        if len(self.image.shape) == 3:
            if (self.image.shape[2]) == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

                img = QImage(self.image,
                             self.image.shape[1],
                             self.image.shape[0],
                             self.image.strides[0],
                             qformat)
                img = img.rgbSwapped()
                pixmap = QPixmap.fromImage(img)
                w = 130
                smaller_pixmap = pixmap.scaledToWidth(w, Qt.SmoothTransformation)


                self.imgLabel.setPixmap(smaller_pixmap)
                self.imgLabel.setAlignment(QtCore.Qt.AlignHCenter
                                         | QtCore.Qt.AlignVCenter)



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

        self.data_type_list = ['XRF', 'Confocal', 'LA-ICP-MS']

        #self.initToolbar()
        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks | QtWidgets.QMainWindow.AllowNestedDocks)

        self.te = QtWidgets.QTextEdit()
        self.te.setReadOnly(True)
        self.setCentralWidget(self.te)

        self.initToolbar()


        self.show()

        if sys.platform == "darwin":
            self.raise_()


    def initToolbar(self):

        self.toolbar = self.addToolBar('MainToolbar')
        self.toolbar.setStyleSheet('QToolBar{spacing:3px;}')



        self.actionBrowser = QtWidgets.QAction(self)
        self.actionBrowser.setIcon(QtGui.QIcon(os.path.join('Resources','openfolder.png')))
        self.actionBrowser.setToolTip('MDA Browser')
        self.toolbar.addAction(self.actionBrowser)
        self.actionBrowser.triggered.connect(self.OnBrowserTB)

        self.actionSettings = QtWidgets.QAction(self)
        self.actionSettings.setIcon(QtGui.QIcon(os.path.join('Resources','settings.png')))
        self.actionSettings.setToolTip('Settings')
        self.toolbar.addAction(self.actionSettings)
        #self.actionSettings.triggered.connect(self.SettingsTB)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.actionHelp = QtWidgets.QAction(self)
        self.actionHelp.setIcon(QtGui.QIcon(os.path.join('Resources','help-50.png')))
        self.actionHelp.setToolTip('Help')
        self.toolbar.addAction(self.actionHelp)
        #self.actionHelp.triggered.connect(self.HelpTB)

        self.actionAbout = QtWidgets.QAction(self)
        self.actionAbout.setIcon(QtGui.QIcon(os.path.join('Resources','info-50.png')))
        self.actionAbout.setToolTip('About')
        self.toolbar.addAction(self.actionAbout)
        #self.actionAbout.triggered.connect(self.AboutTB)


    def OnBrowserTB(self):

        wildcard = "Supported Data formats (*.png *.jpg);;"


        OpenFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Dataset', '', wildcard,
                                                         None, QtWidgets.QFileDialog.DontUseNativeDialog)

        OpenFileName = str(OpenFileName)

        if OpenFileName == '':
            return

        basename, extension = os.path.splitext(OpenFileName)


        datawin = DataViewerWidget(self, OpenFileName)
        self.addDockWidget(Qt.TopDockWidgetArea, datawin)




""" ------------------------------------------------------------------------------------------------"""
def main():

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))
    frame = MainFrame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()