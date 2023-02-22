"""
Widget to show information of the Napari widgets classes and lcode location.

Uses `Ctrl + Mouse right button press`/`Cmd + Mouse right button press`
to trigger the tracing when the event filter is installed.
"""
# Standard library imports
import inspect
from pathlib import Path

# Third-party imports
from qtpy.QtCore import Qt, QEvent, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QTextBrowser,
    QWidget,
)


class QtNapariUITracer(QWidget):
    TEXT_DIVIDER = "--------\n"

    def __init__(self):
        super().__init__()

        # Checkbox
        self.cb_object_doc = QCheckBox("Show object documentation")

        # Buttons
        self.btn_install = QPushButton("Install event filter")
        self.btn_install.clicked.connect(self._on_install)
        self.btn_uninstall = QPushButton("Uninstall event filter")
        self.btn_uninstall.clicked.connect(self._on_uninstall)
        self.btn_uninstall.setEnabled(False)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._on_clear)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_install)
        btn_layout.addWidget(self.btn_uninstall)
        btn_layout.addWidget(self.btn_clear)

        # TextBrowser
        self.output = QTextBrowser(self)
        self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self._handle_file_link)

        # Layout
        self.setLayout(QVBoxLayout())
        self.layout().addLayout(btn_layout)
        self.layout().addWidget(self.cb_object_doc)
        self.layout().addWidget(self.output)

    def _on_install(self):
        qapp = QApplication.instance()
        if qapp:
            qapp.installEventFilter(self)
            self.btn_install.setEnabled(False)
            self.btn_uninstall.setEnabled(True)

    def _on_uninstall(self):
        qapp = QApplication.instance()
        if qapp:
            qapp.removeEventFilter(self)
            self.btn_install.setEnabled(True)
            self.btn_uninstall.setEnabled(False)

    def _on_clear(self):
        self.output.clear()

    def _append_output(self, text, alignment=Qt.AlignLeft, is_html=False):
        if is_html:
            self.output.setAlignment(alignment)
            self.output.insertHtml("<div>{0}</div><br>".format(text))
        else:
            self.output.setAlignment(alignment)
            self.output.insertPlainText(text)

    def _handle_file_link(self, url):
        if not url.scheme():
            url = QUrl.fromLocalFile(url.toString())
        QDesktopServices.openUrl(url)

    def eventFilter(self, qobject, qevent):
        if Qt.ControlModifier == QApplication.keyboardModifiers():
            if qevent.type() == QEvent.Type.MouseButtonPress:
                if qevent.buttons() == Qt.RightButton:
                    qobject_class = str(qobject.__class__)
                    start_qobject_paths = ["QtGui.QWindow"]
                    end_qobject_paths = [
                        "napari._qt.qt_main_window",
                        "napari._qt.dialogs",
                        "app_model.backends.qt._qmenu.QModelMenu",
                        "napari._qt.menus",
                    ]
                    qobject_module = inspect.getmodule(qobject)
                    if qobject_module:
                        is_html = False
                        qobject_module_link = f"Module: {qobject_module}\n\n"
                        try:
                            qobject_module_string = (
                                str(qobject_module)
                                .replace("<", "&#60;")
                                .replace(">", "&#62;")
                            )
                            qobject_module_file = inspect.getsourcefile(
                                qobject_module
                            )
                            if qobject_module_file:
                                qobject_module_file = Path(
                                    qobject_module_file
                                ).as_uri()
                                qobject_module_link = f'Module: <a href="{qobject_module_file}">{qobject_module_string}</a>'
                                is_html = True
                        except TypeError:
                            pass
                        qobject_info = (
                            f"Object: {qobject}\nClass: {qobject.__class__}\n"
                        )
                        qobject_doc = inspect.getdoc(qobject)
                        if qobject_doc and self.cb_object_doc.isChecked():
                            qobject_info = f"Object: {qobject}\nClass: {qobject.__class__}\nDoc: {qobject_doc}\n"
                        if any(
                            match in qobject_class
                            for match in start_qobject_paths
                        ):
                            self._append_output(
                                self.TEXT_DIVIDER, alignment=Qt.AlignCenter
                            )
                        elif any(
                            match in qobject_class
                            for match in end_qobject_paths
                        ):
                            self._append_output(qobject_info)
                            self._append_output(
                                qobject_module_link, is_html=is_html
                            )
                            self._append_output(
                                self.TEXT_DIVIDER, alignment=Qt.AlignCenter
                            )
                        else:
                            self._append_output(qobject_info)
                            self._append_output(
                                qobject_module_link, is_html=is_html
                            )

                    qevent.ignore()
        return super().eventFilter(qobject, qevent)
