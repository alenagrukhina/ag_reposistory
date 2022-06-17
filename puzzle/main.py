import random
import sys

from PyQt5.QtCore import (pyqtSignal, QByteArray, QDataStream, QIODevice,
                          QMimeData, QPoint, QRect, QSize, Qt)
from PyQt5.QtGui import QDrag, QColor, QCursor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                             QListView, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QSizePolicy, QWidget)

puzzle_size = 300  # размер пазла (по умолчанию 400x400)
puzzle_rows = 3  # количество строк (по умолчанию 5)
puzzle_cols = 3  # количество столбцов (по умолчанию 5)
pieces_quantity = puzzle_rows * puzzle_cols  # количество кусочков пазла (по умолчанию 25)
piece_size = round(((puzzle_size ** 2) / pieces_quantity) ** 0.5)  # сторона кусочка пазла (по умолчанию 80x80)


class PuzzleWidget(QWidget):
    puzzleCompleted = pyqtSignal()

    def __init__(self, parent=None):
        super(PuzzleWidget, self).__init__(parent)
        self.piece_pixel_maps = []
        self.piece_rect_list = []
        self.piece_locations = []
        self.highlightedRect = QRect()
        self.inPlace = 0
        self.setAcceptDrops(True)
        self.setMinimumSize(puzzle_size, puzzle_size)
        self.setMaximumSize(puzzle_size, puzzle_size)

    def clear(self): # очистить поле
        self.piece_locations = []
        self.piece_pixel_maps = []
        self.piece_rect_list = []
        self.highlightedRect = QRect()
        self.inPlace = 0
        self.update()

    def dragEnterEvent(self, event): # кусочек в певрый раз перетаскивают на игровое поле
        if event.mimeData().hasFormat('image/x-puzzle-piece'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event): # кусочек убирают из игрового поля
        update_rect = self.highlightedRect
        self.highlightedRect = QRect()
        self.update(update_rect)
        event.accept()

    def dragMoveEvent(self, event): #кусочек перетаскивается на другое место в игровом поле
        update_rect = self.highlightedRect.united(self.target_square(event.pos()))
        if event.mimeData().hasFormat('image/x-puzzle-piece') and self.find_piece(
                self.target_square(event.pos())) == -1:
            self.highlightedRect = self.target_square(event.pos())
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            self.highlightedRect = QRect()
            event.ignore()
        self.update(update_rect)

    def dropEvent(self, event): #паззл после перетаскивания опускается на игровое поле
        if event.mimeData().hasFormat('image/x-puzzle-piece') and self.find_piece(
                self.target_square(event.pos())) == -1:
            piece_data = event.mimeData().data('image/x-puzzle-piece')
            data_stream = QDataStream(piece_data, QIODevice.ReadOnly)
            square = self.target_square(event.pos())
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
            if location == QPoint(round(square.x() / piece_size), round(square.y() / piece_size)):
                self.inPlace += 1
                if self.inPlace == pieces_quantity:
                    self.puzzleCompleted.emit()
        else:
            self.highlightedRect = QRect()
            event.ignore()

    def find_piece(self, piece_rect): # если на месте, куда игрок хочет поместить паззл, уже есть кусочек
        try:
            return self.piece_rect_list.index(piece_rect)
        except ValueError:
            return -1

    def mousePressEvent(self, event): #удерживание кнопки мыши на кусочке паззла
        square = self.target_square(event.pos())
        found = self.find_piece(square)
        if found == -1:
            return
        location = self.piece_locations[found]
        pixmap = self.piece_pixel_maps[found]
        del self.piece_locations[found]
        del self.piece_pixel_maps[found]
        del self.piece_rect_list[found]
        if location == QPoint(round(square.x() / piece_size), round(square.y() / piece_size)):
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
            self.update(self.target_square(event.pos()))
            if location == QPoint(square.x() / piece_size, square.y() / piece_size):
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

    def target_square(self, position): #игровое поле
        return QRect(position.x() // piece_size * piece_size, position.y() // piece_size * piece_size, piece_size, piece_size)


class PiecesList(QListWidget): #лист кусочков паззла
    def __init__(self, parent=None):
        super(PiecesList, self).__init__(parent)
        self.setDragEnabled(True)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(60, 60))
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

    def add_piece(self, pixmap, location): #кусочек паззла помещен в правильное окошко
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
    def __init__(self, parent=None): #окно игры
        super(MainWindow, self).__init__(parent)
        self.puzzleImage = QPixmap()
        self.setup_menus()
        self.setup_widgets()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.setWindowTitle('Игра "Собери паззл"')  # название игры

    def setup_menus(self): #меню
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

    def open_image(self, path=None): #открыть изображение
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", '',
                                                  "Файлы изображений (*.png *.jpg *.bmp)")
        if path:
            new_image = QPixmap()
            if not new_image.load(path):
                QMessageBox.warning(self, "Открыть изображение", "Изображение не может быть загружено.",
                                    QMessageBox.Cancel)
                return
            self.puzzleImage = new_image
            self.setup_puzzle()

    def setup_puzzle(self): #установка паззла
        size = min(self.puzzleImage.width(), self.puzzleImage.height())  # размер минимальной стороны картинки
        aaa = round((self.puzzleImage.width() - size) / 2)
        bbb = round((self.puzzleImage.height() - size) / 2)
        self.puzzleImage = self.puzzleImage.copy(aaa, bbb, size, size).scaled(puzzle_size, puzzle_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.piecesList.clear()
        for y in range(puzzle_rows):
            for x in range(puzzle_cols):
                piece_image = self.puzzleImage.copy(x * piece_size, y * piece_size, piece_size, piece_size)
                self.piecesList.add_piece(piece_image, QPoint(x, y))
        random.seed(QCursor.pos().x() ^ QCursor.pos().y())
        for i in range(self.piecesList.count()):
            if random.random() < 0.5:
                item = self.piecesList.takeItem(i)
                self.piecesList.insertItem(0, item)
        self.puzzleWidget.clear()

    def setup_widgets(self): #установка виджетов
        frame = QFrame()
        frame_layout = QHBoxLayout(frame)
        self.piecesList = PiecesList()
        self.puzzleWidget = PuzzleWidget()
        self.puzzleWidget.puzzleCompleted.connect(self.set_completed, Qt.QueuedConnection)
        frame_layout.addWidget(self.piecesList)
        frame_layout.addWidget(self.puzzleWidget)
        self.setCentralWidget(frame)

    def set_completed(self): #паззл собран
        QMessageBox.information(self, "Паззл собран.",
                                "Поздравляю! Вы собрали паззл!\nНажмите OK, чтобы начать заново.", QMessageBox.Ok)
        self.setup_puzzle()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:  # если нажимаем клавишу "Esc", программа закрывается
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.open_image('images/picture_300x300.jpg')
    window.show()
    sys.exit(app.exec_())
