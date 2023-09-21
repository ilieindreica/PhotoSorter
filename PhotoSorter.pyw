from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import (QApplication, QGridLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
        QPushButton, QScrollArea, QWidget, QMenuBar, QMainWindow, QFileDialog, QStyle)
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget
import os
import shutil


class Slider(QtWidgets.QSlider):
    def __init__(self, parent=None):
        super(Slider, self).__init__(parent)  
        self.observers = []
        self.val = 0

    def notify_observers(self):
        for obs in self.observers:
            obs.update(self)

    def mousePressEvent(self, event):
        super(Slider, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.val = self.pixelPosToRangeValue(event.pos())
            self.setValue(self.val)
            self.notify_observers()

    def attach(self, observer):
        self.observers.append(observer)
        print(self.observers)

    def pixelPosToRangeValue(self, pos):
        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, opt, QtWidgets.QStyle.SC_SliderGroove, self)
        sr = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, opt, QtWidgets.QStyle.SC_SliderHandle, self)

        if self.orientation() == QtCore.Qt.Horizontal:
            sliderLength = sr.width()
            sliderMin = gr.x()
            sliderMax = gr.right() - sliderLength + 1
        else:
            sliderLength = sr.height()
            sliderMin = gr.y()
            sliderMax = gr.bottom() - sliderLength + 1;
        pr = pos - sr.center() + sr.topLeft()
        p = pr.x() if self.orientation() == QtCore.Qt.Horizontal else pr.y()
        return QtWidgets.QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), p - sliderMin,
                                               sliderMax - sliderMin, opt.upsideDown)

class PhotoSorter(QMainWindow):
    def __init__(self, parent=None):
        super(PhotoSorter, self).__init__(parent)

        self.initialiseData()
        self.initialiseGraphics()
        
    
    def initialiseData(self):
        self.imagesQueue = []
        self.outputFolder = ""
        self.imageName = ""
        self.movie = None
        self.mediaPlayer = None
        self.separator = "      ->"


    def initialiseGraphics(self):
        self.setWindowTitle("Categories")                          

        self.categoriesList = QListWidget()                      
        self.categoriesList.setSortingEnabled(1)
        self.categoriesList.itemSelectionChanged.connect(self.showSubcategories)
        self.categoriesList.itemDoubleClicked.connect(self.removeSubcategories)

        selectCategoryButton = QPushButton("Select")                           
        selectCategoryButton.clicked.connect(self.selectCategory)
        addCategoryButton = QPushButton("Add Category")
        addCategoryButton.clicked.connect(self.addNewCategory)              

        self.newCategoryName = QLineEdit()                                   
        self.newCategoryName.returnPressed.connect(self.addNewCategory)      

        self.newImageName = QLineEdit()                                     
        self.newImageName.returnPressed.connect(self.selectCategory)

        centralWidget = QWidget(self)                                       

        self.imageBox = QLabel(self)                                        
        self.imageBox.setText("No Image Selected")

        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setWidget(self.imageBox)
        self.scroll.setWidgetResizable(True)

        self.imageCountLabel = QLabel(self)                                  
        self.imageCountLabel.setText("0 images left")

        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = QVideoWidget()
        self.mediaPlayer.setNotifyInterval(200)                         

        self.playButton = QPushButton()
        self.playButton.clicked.connect(self.play)
        self.playButton.setVisible(False)

        self.positionSlider = Slider(QtCore.Qt.Horizontal)
        self.positionSlider.attach(self)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)
        self.positionSlider.setVisible(False)

        self.jumpOverButton = QPushButton("Leave where it is (name will not be changed)")
        self.jumpOverButton.clicked.connect(self.jumpOver)


        mainLayout = QGridLayout(centralWidget)                               
        mainLayout.addWidget(self.scroll, 0,0,7,5)
        mainLayout.addWidget(self.categoriesList,0,5,6,2)
        mainLayout.addWidget(selectCategoryButton,6,5,1,2)
        mainLayout.addWidget(self.jumpOverButton, 6, 7, 1, 2)
        mainLayout.addWidget(self.newCategoryName, 0,7,1,2)
        mainLayout.addWidget(addCategoryButton, 1,7,1,2)
        mainLayout.addWidget(self.imageCountLabel, 2,7,1,2)
        mainLayout.addWidget(self.videoWidget,0,0,7,5)
        mainLayout.addWidget(self.newImageName, 3, 7, 1,2)
        mainLayout.addWidget(self.positionSlider, 7,1,1,2)
        mainLayout.addWidget(self.playButton, 7, 0, 1,1)
        
        self.setCentralWidget(centralWidget)

        menuBar = QMenuBar(self)                                            
        addImagesAction = menuBar.addAction("&Add Images")
        addImagesAction.triggered.connect(self.openAddImagesDialog)
        selectFolderAction = menuBar.addAction("Select Folder")
        selectFolderAction.triggered.connect(self.selectOutputFolder)
        emptyQueueAction = menuBar.addAction("Empty Queue")
        emptyQueueAction.triggered.connect(self.emptyQueue)
        self.setMenuBar(menuBar)


    def openAddImagesDialog(self):                                                                                                                          
        dialog = QFileDialog()
        filenames,filter = dialog.getOpenFileNames(None, "Select your images", "", "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.mp4 *.webm)")
        for f in filenames:
            if f not in self.imagesQueue:                                                            
                self.imagesQueue.append(f)
        self.refreshImage()
        self.refreshName()

    def refreshImage(self):
        self.mediaPlayer.stop()
        self.mediaPlayer.setPlaylist(QMediaPlaylist())
        self.videoWidget.hide()

        if self.movie:                                                                                   
            self.movie.stop()
            self.movie = None
            self.imageBox.setMovie(None)
        
        if self.imagesQueue:
            self.playButton.setVisible(False)
            self.positionSlider.setVisible(False)
            if self.imagesQueue[0].endswith(".gif"):                                                        
                self.movie = QMovie(self.imagesQueue[0])
                self.imageBox.setMovie(self.movie)
                self.movie.start()
            elif self.imagesQueue[0].endswith(".mp4") or self.imagesQueue[0].endswith(".webm"):                                                                      
                self.videoWidget.show()
                self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.imagesQueue[0])))
                self.videoWidget.setMediaObject(self.mediaPlayer)
                
                self.playButton.setVisible(True)
                self.positionSlider.setVisible(True)
                self.playButton.setEnabled(True)
                self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

                self.mediaPlayer.setVideoOutput(self.videoWidget)
                self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
                self.mediaPlayer.positionChanged.connect(self.positionChanged)
                self.mediaPlayer.durationChanged.connect(self.durationChanged)
                

                self.mediaPlayer.play()
                
            else:
                pixmap = QPixmap(self.imagesQueue[0])                                                               
                pixmap.setDevicePixelRatio(7.0)
                pixmap = pixmap.scaled(3840, 2160, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.imageBox.setPixmap(pixmap)
                self.imageBox.setScaledContents(True)
        elif not self.imagesQueue:
            self.imageBox.setText("No Image Selected")
            # self.imageName = ""
        
        self.imageCountLabel.setText(f'{len(self.imagesQueue)} images left')


    def selectOutputFolder(self):
        dialog = QFileDialog()
        self.outputFolder = dialog.getExistingDirectory(self)
        self.categoriesList.clear()
        if os.path.exists(self.outputFolder):
            self.categoriesList.addItems([ name for name in os.listdir(self.outputFolder) if os.path.isdir(os.path.join(self.outputFolder, name)) ])
    
    def emptyQueue(self):
        if self.imagesQueue:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Are you sure you want to remove the images from the queue?")
            daButton = QPushButton("Yes") 
            nuButton = QPushButton("No")
            msg.addButton(nuButton, QMessageBox.RejectRole)
            msg.addButton(daButton, QMessageBox.AcceptRole)
            msg.setWindowTitle("Warning")
            msg.exec_()
            
            if msg.clickedButton() == daButton:
                self.imagesQueue.clear()
                self.refreshImage()
                self.newImageName.setText("")

    def refreshName(self):
        if self.imagesQueue:
            self.imageName = os.path.split(self.imagesQueue[0])[1].rsplit('.', 1)[0]
        else:
            self.imageName = ""
        self.newImageName.setText(self.imageName)

    def jumpOver(self):
        if self.imagesQueue:
            self.imagesQueue.pop(0)  
            self.refreshImage() 
            self.refreshName()

    def removeSubcategories(self):
        if not self.categoriesList.selectedItems()[0].text().startswith(self.separator):
            for i in range(self.categoriesList.count(), 0, -1):
                            if self.categoriesList.item(i):
                                if self.categoriesList.item(i).text().startswith(self.separator):
                                    self.categoriesList.takeItem(i)     

    def showSubcategories(self):
        categories = self.categoriesList.selectedItems()
        if categories:
            category = categories[0]
            # self.categoriesList.setAutoScroll(True)
            # self.categoriesList.scrollToItem(categories[0], self.categoriesList.PositionAtBottom)
            # sub_folders = [name for name in os.listdir(category.text()) if os.path.isdir(os.path.join(category.text(), name))]

            if category:
                if not category.text().startswith(self.separator):
                    self.removeSubcategories()                   

                    self.categoriesList.setSortingEnabled(0)
                    
                    if os.path.exists(self.outputFolder + '/' + category.text()):
                        auxList = []
                        for name in os.listdir(self.outputFolder + '/' + category.text()):
                            if os.path.isdir(os.path.join(self.outputFolder + '/' + category.text(), name)):
                                auxList.append(name)

                        # auxList.sort(reverse=True)  #fara reverse le afiseaza invers; daca tot nu merge, incearca sa pui un +i crescator in loc de +1 mai jos
                        auxList = sorted(auxList, key=str.casefold, reverse=True)
                        for name in auxList:
                            self.categoriesList.insertItem(self.categoriesList.currentRow() + 1, self.separator + name)

                    self.categoriesList.setSortingEnabled(1)

    def selectCategory(self):
        if not self.imagesQueue:
            return
        self.imageName = self.newImageName.text()
        specialCharacter = "\\/:*?\"<>|"
        if self.imageName: 
            if True in [c in self.imageName for c in specialCharacter]:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("You can not use \\/:*?\"<>| in the name")
                msg.setWindowTitle("Error")
                msg.exec_()
                return
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Image name can not be empty")
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        if not self.outputFolder:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please select the output folder")
            msg.setWindowTitle("Error")
            msg.exec_()
            return

        categories = self.categoriesList.selectedItems()     
        
        if categories:
            category = categories[0]
            aux = categories[0]
            folderParinte = ""
            if aux.text().startswith(self.separator):
                category = aux.text().removeprefix(self.separator)
                for i in range(self.categoriesList.currentRow(), 0, -1):
                    if not self.categoriesList.item(i).text().startswith(self.separator):
                        folderParinte = self.categoriesList.item(i).text()
                        break
            else:
                category = aux.text()

            if folderParinte:
                imageFolder = self.outputFolder + '/' + folderParinte + '/' + category + '/'
            else:
                imageFolder = self.outputFolder + '/' + category + '/'
            os.makedirs(imageFolder, exist_ok=True)
            imageExtension = os.path.split(self.imagesQueue[0])[1].rsplit('.', 1)[1]
            currentImage = self.imagesQueue[0]
            
            self.imagesQueue.pop(0)
            self.refreshImage()
            
            if os.path.exists(imageFolder + self.imageName + "." + imageExtension):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                i = 1
                while os.path.exists(imageFolder + self.imageName + " double(" + str(i) + ")."+ imageExtension):
                    i += 1
                msg.setText("The file already exists in that folder\nIt was moved in the selected folder with \"dublura(" + str(i) + ")\" at the end in its name")
                msg.setWindowTitle("Error")
                shutil.move(currentImage, imageFolder + self.imageName + " double(" + str(i) + ")."+ imageExtension)

                msg.exec_()
            else:
                shutil.move(currentImage, imageFolder + self.imageName + "." + imageExtension)

            self.refreshName()
            

    def addNewCategory(self):
        name = self.newCategoryName.text()
        specialCharacter = "\\/:*?\"<>|"
        if name: 
            if True in [c in name for c in specialCharacter]:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("You can not use \\/:*?\"<>| in the name")
                msg.setWindowTitle("Error")
                msg.exec_()
            else:
                if not self.categoriesList.findItems(name, Qt.MatchFlag.MatchFixedString):
                    self.categoriesList.addItem(name)
                self.newCategoryName.setText("")


    #shortcut for SelectCategory
    def keyPressEvent(self, e):                                   
        if e.key() == Qt.Key_Space:
            self.selectCategory()
    
    def positionChanged(self, position):
        self.positionSlider.setValue(position)

    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)        
    
    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)
        
    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
    
    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPlay))

    def update(self, slider):
        self.setPosition(slider.val)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    photoSorter = PhotoSorter()
    photoSorter.show()
    sys.exit(app.exec_()) 

