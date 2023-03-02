"""
Widget to show information of the Napari widgets classes and module location.

Uses `Ctrl + Mouse right button press`/`Cmd + Mouse right button press`
to trigger the tracing when the event filter is installed.
"""
# Standard library imports
import inspect
from pathlib import Path
from textwrap import indent

# Third-party imports
from qtpy.QtCore import Qt, QEvent, QUrl
from qtpy.QtGui import QDesktopServices, QTextCursor
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QTextBrowser,
    QWidget,
)

# napari imports
import napari.utils.events.event as events
from napari.utils.events.event import _noop
from napari.utils.events.debugging import _shorten_fname, _SETTINGS


class QtNapariUITracer(QWidget):
    TEXT_DIVIDER = "--------\n"

    def __init__(self):
        super().__init__()

        # Checkbox
        self.cb_object_doc = QCheckBox("Show object documentation")
        self.cb_debug_events = QCheckBox("Debug application events")
        self.cb_debug_events.toggled.connect(self._on_log_debug_events)

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
        self.layout().addWidget(self.cb_debug_events)
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
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
        if is_html:
            self.output.setAlignment(alignment)
            self.output.insertHtml("<div>{0}</div><br>".format(text))
        else:
            self.output.setAlignment(alignment)
            self.output.insertPlainText(text)

    def _append_event_output(
        self, text, alignment=Qt.AlignLeft, is_html=False
    ):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
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

    def _on_log_debug_events(self, enabled):
        def _handle_debug_event_output(event, cfg=_SETTINGS):
            """Print info about what caused this event to be emitted.s"""
            print(event)
            if cfg.include_events:
                if event.type not in cfg.include_events:
                    return
            elif event.type in cfg.exclude_events:
                return

            source = type(event.source).__name__
            if cfg.include_emitters:
                if source not in cfg.include_emitters:
                    return
            elif source in cfg.exclude_emitters:
                return

            # get values being emitted
            vals = ",".join(f"{k}={v}" for k, v in event._kwargs.items())
            # show event type and source
            lines = [f"{source}.events.{event.type}({vals})"]
            # climb stack and show what caused it.
            # note, we start 2 frames back in the stack, one frame for *this* function
            # and the second frame for the EventEmitter.__call__ function (where this
            # function was likely called).
            call_stack = inspect.stack(0)
            for frame in call_stack[2 : 2 + cfg.stack_depth]:
                fname = _shorten_fname(frame.filename)
                obj = ""
                if "self" in frame.frame.f_locals:
                    obj = type(frame.frame.f_locals["self"]).__name__ + "."
                ln = f'  "{fname}", line {frame.lineno}, in {obj}{frame.function}'
                lines.append(ln)
            lines.append("")

            # find the first caller in the call stack
            for f in reversed(call_stack):
                if "self" in f.frame.f_locals:
                    obj_type = type(f.frame.f_locals["self"])
                    module = obj_type.__module__ or ""
                    if module.startswith("napari"):
                        trigger = f"{obj_type.__name__}.{f.function}()"
                        lines.insert(1, f"  was triggered by {trigger}, via:")
                        break

            # seperate groups of events
            if not cfg._cur_depth:
                lines = ["─" * 79, ""] + lines
            elif not cfg.nesting_allowance:
                return

            # log it
            self._append_event_output(
                indent("\n".join(lines), "  " * cfg._cur_depth)
            )

            # spy on nested events...
            # (i.e. events that were emitted while another was being emitted)
            def _pop_source():
                cfg._cur_depth -= 1
                return event._sources.pop()

            event._pop_source = _pop_source
            cfg._cur_depth += 1

        if enabled:
            events._log_event_stack = _handle_debug_event_output
        else:
            events._log_event_stack = _noop

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
