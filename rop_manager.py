from PySide2.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget,
    QMessageBox, QDoubleSpinBox, QSpinBox,
    QSlider, QCheckBox, QLineEdit, QScrollArea, QColorDialog,
    QFrame, QGroupBox, QDialogButtonBox, QStyle, QDialog, QButtonGroup,
)
from PySide2.QtCore import Qt, Signal, QEvent, QSize, QLocale
from PySide2.QtGui import QFont, QColor, QIcon

import hou


class ROPManager(QWidget):
    WINDOW_NAME = "ROPManagerWindow"

    def __init__(self, parent=None):
        super(ROPManager, self).__init__(parent, Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("ROP Manager")
        
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # ROP Type Selection
        rop_type_layout = QHBoxLayout()
        rop_type_label = QLabel("ROP Type:")
        self.rop_type_combo = QComboBox()
        self.rop_type_combo.addItems(["Arnold", "Mantra", "Karma"])
        rop_type_layout.addWidget(rop_type_label)
        rop_type_layout.addWidget(self.rop_type_combo)
        main_layout.addLayout(rop_type_layout)

        # ROP List
        self.rop_list = QListWidget()
        main_layout.addWidget(self.rop_list)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add ROP")
        remove_button = QPushButton("Remove ROP")
        update_button = QPushButton("Update List")
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(update_button)
        main_layout.addLayout(button_layout)


        # Connect signals
        add_button.clicked.connect(self.add_rop)
        remove_button.clicked.connect(self.remove_rop)
        update_button.clicked.connect(self.update_rop_list)
        self.show_existing_rops(hou.node("/"))
        self.rop_list.itemClicked.connect(self.select_rop)

    def select_rop(self, item):
        rop_name = item.text()
        rop_node = hou.node(rop_name)
        if rop_node:
            hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).setCurrentNode(rop_node)
        else:
            QMessageBox.warning(self, "ROP Not Found", f"Could not find ROP node: {rop_name}")

    def show_existing_rops(self, context):
        root = context.children()
        
        for child in root:
            self.show_existing_rops(child)
            if child.type().name() in ["ifd", "karma", "arnold"]:
                self.rop_list.addItem(child.path())
        
    def update_rop_list(self):
        self.rop_list.clear()
        self.show_existing_rops(hou.node("/"))

    def _ask_name_and_suffix(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New ROP")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Enter a name for the new ROP:"))

        name_field = QLineEdit(dialog)
        layout.addWidget(name_field)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Suffix:"))
        bty_check = QCheckBox("bty")
        shd_check = QCheckBox("shd")
        tech_check = QCheckBox("tech")
        bty_check.setChecked(True)

        suffix_group = QButtonGroup(dialog)
        suffix_group.setExclusive(True)
        suffix_group.addButton(bty_check)
        suffix_group.addButton(shd_check)
        suffix_group.addButton(tech_check)

        suffix_row.addWidget(bty_check)
        suffix_row.addWidget(shd_check)
        suffix_row.addWidget(tech_check)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return None, None

        name = name_field.text().strip()
        if tech_check.isChecked():
            suffix = "tech"
        elif shd_check.isChecked():
            suffix = "shd"
        else:
            suffix = "bty"
        return name, suffix

    def add_rop(self):
        rop_type = self.rop_type_combo.currentText()
        text, suffix = self._ask_name_and_suffix()

        if text is None:
            return

        if text:
            rop_name = f"{text}_{suffix}"
        else:
            rop_name = f"{rop_type.lower()}"
        
        renderers = {
            "Arnold": "arnold",
            "Mantra": "ifd",
            "Karma": "karma"
        }
        
        rop_node = hou.node("/out").createNode(renderers[rop_type], rop_name)
        self.rop_list.addItem(rop_node.path())
        hou.node("/out").layoutChildren()

    def remove_rop(self):
        selected_items = self.rop_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a ROP to remove.")
            return
        for item in selected_items:
            self.rop_list.takeItem(self.rop_list.row(item))
            rop_node = hou.node(item.text())
            if rop_node:
                rop_node.destroy()
                hou.node("/out").layoutChildren()

_rop_manager_window = None


def create_rop_manager_window():
    global _rop_manager_window

    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            if widget.objectName() == ROPManager.WINDOW_NAME:
                try:
                    if widget.isVisible():
                        widget.raise_()
                        widget.activateWindow()
                        _rop_manager_window = widget
                        return widget
                    widget.close()
                except RuntimeError:
                    pass

    try:
        parent = hou.qt.mainWindow()
    except Exception:
        parent = None

    window = ROPManager(parent=parent)
    window.setObjectName(ROPManager.WINDOW_NAME)
    window.show()
    window.raise_()
    window.activateWindow()

    _rop_manager_window = window
    return window


create_rop_manager_window()