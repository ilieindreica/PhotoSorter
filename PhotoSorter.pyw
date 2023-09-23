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
        self.spaceText = "      "
        self.arrow = "->"
        
        self.subfolder_level = 0
        self.separator = self.subfolder_level * self.spaceText + self.arrow

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

        self.addSubfolderButton = QPushButton("Add subcategory to selected")
        self.addSubfolderButton.clicked.connect(self.addSubfolder)

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

        self.newFolderName = QLineEdit()
        self.newFolderName.returnPressed.connect(self.renameFolder)
        
        self.renameFolderButton = QPushButton("Rename selected folder")
        self.renameFolderButton.clicked.connect(self.renameFolder)

        height = 10
        width = 8
        mainLayout = QGridLayout(centralWidget)                               
        mainLayout.addWidget(self.scroll,             0, 0, height, 5)
        mainLayout.addWidget(self.categoriesList,     0, 5, height, 2)
        mainLayout.addWidget(selectCategoryButton,    height, 5, 1, 2)
        mainLayout.addWidget(self.jumpOverButton,     height, 7, 1, 2)
        mainLayout.addWidget(self.newCategoryName,    0, 7, 1, 2)
        mainLayout.addWidget(addCategoryButton,       1, 7, 1, 1)
        mainLayout.addWidget(self.addSubfolderButton, 1, 8, 1, 1)
        mainLayout.addWidget(self.imageCountLabel,    2, 7, 1, 2)
        mainLayout.addWidget(self.videoWidget,        0, 0, height, 5)
        mainLayout.addWidget(self.newImageName,       3, 7, 1, 2)
        mainLayout.addWidget(self.newFolderName,      height-3, 7, 1, 2)
        mainLayout.addWidget(self.renameFolderButton, height-2, 7, 1, 2)
        mainLayout.addWidget(self.positionSlider,     height, 1, 1, 2)
        mainLayout.addWidget(self.playButton,         height, 0, 1, 1)
        
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

    def renameFolder(self):
        categories = self.categoriesList.selectedItems()
        if categories:
            category = categories[0]

            if category:
                old_path = self.getAbsPath(category)
                new_path = self.newFolderName.text()

                if self.specialCharacterError(new_path):
                    return
                
                name = category.text().replace(self.spaceText, '').replace(self.arrow, '')
                prefix = category.text().replace(name, '')
                new_path = old_path.replace(name, self.newFolderName.text())
                
                if not os.path.isdir(new_path):
                    try:                        
                        os.replace(old_path, new_path) 

                        if prefix != '':                                          
                            self.categoriesList.setSortingEnabled(0)
                        else:
                            self.removeSubcategories()

                        self.categoriesList.selectedItems()[0].setText(prefix + self.newFolderName.text())
                        self.newFolderName.setText('')
                        self.categoriesList.setSortingEnabled(1)
                        self.showSubcategories()
                    except:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Renaming Failed")
                        msg.setWindowTitle("Error")
                        msg.exec_()

    def getAbsPath(self, name):
        selected = name.text().replace(self.arrow, '')
        index = self.categoriesList.row(name) 
        level = selected.count(self.spaceText)

        path = '/' + selected.replace(self.spaceText, '')

        while level:
            for i in range(index, -1, -1):
                parent = self.categoriesList.item(i).text()
                if parent.count(self.spaceText) < level:
                    level -= 1
                    path = '/' + parent.replace(self.spaceText, '').replace(self.arrow, '', 1) + path
        return self.outputFolder + path

    def removeSubcategories(self):
        # calculate the level at which the selected is, and +1 so we remove only the subfolders below this level
        if self.categoriesList.selectedItems():
            level = self.categoriesList.selectedItems()[0].text().count(self.spaceText) + 1

        # remove the subfolders in the list of a given level, to keep visibility
        # we go bottom up so when one category will be removed, it won't skip the one below
        for i in range(self.categoriesList.count(), 0, -1):
            if self.categoriesList.item(i):
                if self.categoriesList.item(i).text().count(self.spaceText) >= level:
                    self.categoriesList.takeItem(i)  

    def showSubcategories(self): 
        categories = self.categoriesList.selectedItems()
        if categories:
            category = categories[0]
            
            if category:     
                # subfolders will be indented with one 'spaceText' from their parent           
                subfolder_level = category.text().count(self.spaceText) + 1
                self.separator = subfolder_level * self.spaceText + self.arrow
                
                self.removeSubcategories()                
                self.categoriesList.setSortingEnabled(0)

                absolute_path_of_parent = self.getAbsPath(category)
                # print(absolute_path_of_parent)
                
                if os.path.exists(absolute_path_of_parent):                    
                    auxList = []
                    
                    # searching for subfolders to add them in the list
                    for name in os.listdir(absolute_path_of_parent):
                        if os.path.isdir(os.path.join(absolute_path_of_parent, name)):
                            auxList.append(name)

                    # make subfolders to appear alphabetically under parent
                    auxList = sorted(auxList, key=str.casefold, reverse=True)
                    for name in auxList:
                        self.categoriesList.insertItem(self.categoriesList.currentRow() + 1, self.separator + name)

                # center the view around selected
                self.categoriesList.scrollToItem(category, QListWidget.PositionAtCenter)

                item_rect = self.categoriesList.visualItemRect(category)                
                center_horizontal = self.categoriesList.viewport().width() / 2
                horizontal_scroll_position = int(item_rect.right() + center_horizontal)
                self.categoriesList.horizontalScrollBar().setValue(horizontal_scroll_position)
                
                self.newFolderName.setText(category.text().replace(self.spaceText, '').replace(self.arrow, ''))
                self.categoriesList.setSortingEnabled(1)

    def specialCharacterError(self, name):
        specialCharacter = "\\/:*?\"<>|" 
        if True in [c in name for c in specialCharacter] or self.spaceText in name:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"You can not use \\/:*?\"<>| in the name\nAnd it cannot start with \"{self.spaceText}\"")
            msg.setWindowTitle("Error")
            msg.exec_()
            return True
        else:
            return False

    def selectCategory(self):
        if not self.imagesQueue:
            return
        self.imageName = self.newImageName.text()
        
        #Errors regarding name of the image
        if self.imageName: 
            if self.specialCharacterError(self.imageName):
                return
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Image name can not be empty")
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        
        #Errors regarding output folder
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

            if category:
                aux = categories[0]
                imageFolder = self.getAbsPath(category)

                os.makedirs(imageFolder, exist_ok=True)
                imageExtension = '.' + os.path.split(self.imagesQueue[0])[1].rsplit('.', 1)[1]
                currentImage = self.imagesQueue[0]
                
                self.imagesQueue.pop(0)
                self.refreshImage()

                imagePath = os.path.join(imageFolder, self.imageName)
                
                if os.path.exists(imagePath + imageExtension):
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    i = 1
                    while os.path.exists(imagePath + " double(" + str(i) + ")"+ imageExtension):
                        i += 1
                    msg.setText("The file already exists in that folder\nIt was moved in the selected folder with \"double(" + str(i) + ")\" at the end in its name")
                    msg.setWindowTitle("Error")
                    shutil.move(currentImage, imagePath + " double(" + str(i) + ")"+ imageExtension)

                    msg.exec_()
                else:
                    shutil.move(currentImage, imagePath + imageExtension)

                self.refreshName()
            
    def addNewCategory(self):
        name = self.newCategoryName.text()

        if name: 
            if self.specialCharacterError(name=name):
                return
            else:
                if not self.categoriesList.findItems(name, Qt.MatchFlag.MatchFixedString):
                    self.categoriesList.addItem(name)
                    path = self.outputFolder + '/' + name
                    if not os.path.isdir(path):
                        os.mkdir(path)
                self.newCategoryName.setText("")

    def addSubfolder(self):
        name = self.newCategoryName.text()
        
        if name:
            if self.specialCharacterError(name=name):
                return
            else:
                categories = self.categoriesList.selectedItems()
                if categories:
                    category = categories[0]

                    if category:
                        path = os.path.join(self.getAbsPath(category), name)
                        if not os.path.isdir(path):
                            os.mkdir(path)
                        self.newCategoryName.setText('')
                        self.showSubcategories()
 
    def keyPressEvent(self, e): 
        #shortcut for SelectCategory                                  
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

