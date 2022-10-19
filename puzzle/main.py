import random
import sys

from PyQt5.QtCore import (pyqtSignal, QByteArray, QDataStream, QIODevice,
                          QMimeData, QPoint, QRect, QSize, Qt)
from PyQt5.QtGui import QDrag, QColor, QCursor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                             QListView, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QSizePolicy, QWidget)

puzzle_image_width = 0
puzzle_image_height = 0
pieces_quantity = 0
piece_image_width = 0
piece_image_height = 0


def target_square(position):
    return QRect(position.x() // piece_image_width * piece_image_width,
                 position.y() // piece_image_height * piece_image_height, piece_image_width,
                 piece_image_height)


class PuzzleWidget(QWidget):
    puzzleCompleted = pyqtSignal()

    # def __init__(self, parent=None, aaa=400, bbb=400):
    def __init__(self, parent, aaa, bbb):
        super(PuzzleWidget, self).__init__(parent)
        self.hightlightedRect = None
        self.piece_pixel_maps = []
        self.piece_rect_list = []
        self.piece_locations = []
        self.highlightedRect = QRect()
        self.inPlace = 0
        self.setAcceptDrops(True)
        self.setMinimumSize(aaa, bbb)
        self.setMaximumSize(aaa, bbb)

    def clear(self):
        self.piece_locations = []
        self.piece_pixel_maps = []
        self.piece_rect_list = []
        self.highlightedRect = QRect()
        self.inPlace = 0
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('image/x-puzzle-piece'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        update_rect = self.highlightedRect
        self.highlightedRect = QRect()
        self.update(update_rect)
        event.accept()

    def dragMoveEvent(self, event):
        update_rect = self.highlightedRect.united(target_square(event.pos()))
        if event.mimeData().hasFormat('image/x-puzzle-piece') and self.find_piece(
                target_square(event.pos())) == -1:
            self.highlightedRect = target_square(event.pos())
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            self.highlightedRect = QRect()
            event.ignore()
        self.update(update_rect)

    def dropEvent(self, event):
        if event.mimeData().hasFormat('image/x-puzzle-piece') and self.find_piece(
                target_square(event.pos())) == -1:
            piece_data = event.mimeData().data('image/x-puzzle-piece')
            data_stream = QDataStream(piece_data, QIODevice.ReadOnly)
            square = target_square(event.pos())
            pixmap = QPixmap()
            location = QPoint()
            data_stream >> pixmap >> location
            self.piece_locations.append(location)
            self.piece_pixel_maps.append(pixmap)
            self.piece_rect_list.append(square)
            self.hightlightedRect = QRect()
            self.update(square)
            event.setDropAction(Qt.MoveAction)
            event.accept()
            if location == QPoint(round(square.x() / piece_image_width), round(square.y() / piece_image_height)):
                self.inPlace += 1
                if self.inPlace == pieces_quantity:
                    self.puzzleCompleted.emit()
        else:
            self.highlightedRect = QRect()
            event.ignore()

    def find_piece(self, piece_rect):
        try:
            return self.piece_rect_list.index(piece_rect)
        except ValueError:
            return -1

    def mousePressEvent(self, event):
        square = target_square(event.pos())
        found = self.find_piece(square)
        if found == -1:
            return
        location = self.piece_locations[found]
        pixmap = self.piece_pixel_maps[found]
        del self.piece_locations[found]
        del self.piece_pixel_maps[found]
        del self.piece_rect_list[found]
        if location == QPoint(round(square.x() / piece_image_width), round(square.y() / piece_image_height)):
            self.inPlace -= 1
        self.update(square)
        item_data = QByteArray()
        data_stream = QDataStream(item_data, QIODevice.WriteOnly)
        data_stream << pixmap << location
        mime_data = QMimeData()
        mime_data.setData('image/x-puzzle-piece', item_data)
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setHotSpot(event.pos() - square.topLeft())
        drag.setPixmap(pixmap)
        if drag.exec_(Qt.MoveAction) != Qt.MoveAction:
            self.piece_locations.insert(found, location)
            self.piece_pixel_maps.insert(found, pixmap)
            self.piece_rect_list.insert(found, square)
            self.update(target_square(event.pos()))
            if location == QPoint(square.x() / piece_image_width, square.y() / piece_image_height):
                self.inPlace += 1

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.fillRect(event.rect(), Qt.white)
        if self.highlightedRect.isValid():
            painter.setBrush(QColor("#ffcccc"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.highlightedRect.adjusted(0, 0, -1, -1))
        for rect, pixmap in zip(self.piece_rect_list, self.piece_pixel_maps):
            painter.drawPixmap(rect, pixmap)
        painter.end()


class PiecesList(QListWidget):
    def __init__(self, parent=None):
        super(PiecesList, self).__init__(parent)
        self.setDragEnabled(True)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(97, 97))
        self.setSpacing(10)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('image/x-puzzle-piece'):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('image/x-puzzle-piece'):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('image/x-puzzle-piece'):
            piece_data = event.mimeData().data('image/x-puzzle-piece')
            data_stream = QDataStream(piece_data, QIODevice.ReadOnly)
            pixmap = QPixmap()
            location = QPoint()
            data_stream >> pixmap >> location
            self.add_piece(pixmap, location)
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def add_piece(self, pixmap, location):
        piece_item = QListWidgetItem(self)
        piece_item.setIcon(QIcon(pixmap))
        piece_item.setData(Qt.UserRole, pixmap)
        piece_item.setData(Qt.UserRole + 1, location)
        piece_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        item_data = QByteArray()
        data_stream = QDataStream(item_data, QIODevice.WriteOnly)
        pixmap = QPixmap(item.data(Qt.UserRole))
        location = item.data(Qt.UserRole + 1)
        data_stream << pixmap << location
        mime_data = QMimeData()
        mime_data.setData('image/x-puzzle-piece', item_data)
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setHotSpot(QPoint(round(pixmap.width() / 2), round(pixmap.height() / 2)))
        drag.setPixmap(pixmap)
        if drag.exec_(Qt.MoveAction) == Qt.MoveAction:
            if self.currentItem() is not None:
                self.takeItem(self.row(item))


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.puzzleWidget = None
        self.piecesList = None
        self.puzzleImage = QPixmap()
        self.setup_menu()
        # self.setup_widgets()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.setWindowTitle('Игра "Собери паззл"')  # название игры

    def setup_menu(self):
        file_menu = self.menuBar().addMenu("&Файл")
        open_action = file_menu.addAction("&Открыть...")
        open_action.setShortcut("Ctrl+O")
        exit_action = file_menu.addAction("&Выход")
        exit_action.setShortcut("Ctrl+Q")
        game_menu = self.menuBar().addMenu("&Игра")
        restart_action = game_menu.addAction("&Начать заново")
        restart_action.setShortcut("Ctrl+R")
        open_action.triggered.connect(self.open_image)
        exit_action.triggered.connect(QApplication.instance().quit)
        restart_action.triggered.connect(self.setup_puzzle)

    def open_image(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", '',
                                                  "Файлы изображений (*.png *.jpg *.jpeg *.bmp)")
        if path:
            new_image = QPixmap()
            if not new_image.load(path):
                QMessageBox.warning(self, "Открыть изображение", "Изображение не может быть загружено.",
                                    QMessageBox.Cancel)
                return

            self.puzzleImage = new_image
            self.setup_puzzle()

    def setup_puzzle(self):
        global puzzle_image_width
        global puzzle_image_height
        global pieces_quantity
        global piece_image_width
        global piece_image_height

        if self.puzzleImage.width() > 600 or self.puzzleImage.height() > 600:
            if self.puzzleImage.height() > self.puzzleImage.width():
                puzzle_image_width = round(self.puzzleImage.width() * 600 / self.puzzleImage.height())  # ширина пазла
                puzzle_image_height = round(self.puzzleImage.height() * puzzle_image_width / self.puzzleImage.width())

            if self.puzzleImage.width() > self.puzzleImage.height():
                puzzle_image_height = round(self.puzzleImage.height() * 600 / self.puzzleImage.width())  # длина пазла
                puzzle_image_width = round(self.puzzleImage.width() * puzzle_image_height / self.puzzleImage.height())
        else:
            puzzle_image_width = self.puzzleImage.width()
            puzzle_image_height = self.puzzleImage.height()

        puzzle_image_rows = 3  # количество строк
        puzzle_image_cols = 3  # количество столбцов

        pieces_quantity = puzzle_image_rows * puzzle_image_cols  # количество кусочков пазла

        piece_image_width = round(puzzle_image_width / puzzle_image_cols)
        piece_image_height = round(puzzle_image_height / puzzle_image_rows)

        self.puzzleImage = self.puzzleImage.copy(self.puzzleImage.width(), self.puzzleImage.height(),
                                                 self.puzzleImage.width(),
                                                 self.puzzleImage.height()).scaled(puzzle_image_width,
                                                                                   puzzle_image_height,
                                                                                   Qt.IgnoreAspectRatio,
                                                                                   Qt.SmoothTransformation)
        self.setup_widgets()
        self.piecesList.clear()
        for y in range(puzzle_image_rows):
            for x in range(puzzle_image_cols):
                piece_image = self.puzzleImage.copy(x * piece_image_width, y * piece_image_height,
                                                    piece_image_width, piece_image_height)
                self.piecesList.add_piece(piece_image, QPoint(x, y))
        random.seed(QCursor.pos().x() ^ QCursor.pos().y())
        for i in range(self.piecesList.count()):
            if random.random() < 0.5:
                item = self.piecesList.takeItem(i)
                self.piecesList.insertItem(0, item)
        self.puzzleWidget.clear()

    def setup_widgets(self):
        print(self.puzzleImage.width(), self.puzzleImage.height())
        print(puzzle_image_width, puzzle_image_height)
        print(piece_image_width, piece_image_height)

        frame = QFrame()
        frame_layout = QHBoxLayout(frame)
        self.piecesList = PiecesList()
        self.puzzleWidget = PuzzleWidget(parent=None, aaa=puzzle_image_width, bbb=puzzle_image_height)
        self.puzzleWidget.puzzleCompleted.connect(self.set_completed, Qt.QueuedConnection)
        frame_layout.addWidget(self.piecesList)
        frame_layout.addWidget(self.puzzleWidget)
        self.setCentralWidget(frame)

    def set_completed(self):
        QMessageBox.information(self, "Паззл собран.",
                                "Поздравляю! Вы собрали паззл!\nНажмите OK, чтобы начать заново.", QMessageBox.Ok)
        self.setup_puzzle()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:  # если нажимаем клавишу "Esc", программа закрывается
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    # window.open_image('images/picture_300x300.jpg')
    # window.open_image('images/picture_400x400.jpg')
    # window.open_image('images/picture_2145x2560.jpg')
    window.open_image('images/picture_4390x2922.jpeg')
    # window.open_image('images/picture_4546x3026.jpeg')
    window.show()
    sys.exit(app.exec_())
