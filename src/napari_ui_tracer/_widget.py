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
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
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

        # Settings
        self._debug_event_settings = _SETTINGS

        # Checkboxes
        self.cb_event_filter = QGroupBox("Enable Qt event filter")
        self.cb_event_filter.setCheckable(True)
        self.cb_event_filter.setChecked(False)
        self.cb_event_filter.setToolTip(
            "Use Ctrl/Cmd + Mouse Right click to check UI object instance and related modules when active"
        )
        self.cb_event_filter.toggled.connect(self._on_event_filter)
        self.cb_object_doc = QCheckBox("Show object documentation")
        self.cb_object_doc.setToolTip(
            "Define if documentation (if available) for clicked objects should be shown"
        )
        group_box_layout = QHBoxLayout()
        # Show docs
        group_box_layout.addWidget(self.cb_object_doc)
        self.cb_event_filter.setLayout(group_box_layout)

        self.cb_debug_events = QGroupBox("Enable application events logging")
        self.cb_debug_events.setCheckable(True)
        self.cb_debug_events.setChecked(False)
        self.cb_debug_events.setToolTip(
            "Show application events logging when active"
        )
        self.cb_debug_events.toggled.connect(self._on_log_debug_events)
        # Stack depth
        self.label_stack_depth = QLabel("Stack depth:")
        self.sb_stack_depth = QSpinBox()
        self.sb_stack_depth.setRange(1, 50)
        self.sb_stack_depth.setValue(self._debug_event_settings.stack_depth)
        self.sb_stack_depth.setToolTip("Stack depth to show")
        self.sb_stack_depth.valueChanged.connect(self._on_stack_depth_changed)
        # Nesting allowance
        self.label_nesting_allowance = QLabel("Allowed nested events:")
        self.sb_nesting_allowance = QSpinBox()
        self.sb_nesting_allowance.setRange(0, 5)
        self.sb_nesting_allowance.setValue(
            self._debug_event_settings.nesting_allowance
        )
        self.sb_nesting_allowance.setToolTip(
            "How many sub-emit nesting levels to show (i.e. events that get triggered by other events)"
        )
        self.sb_nesting_allowance.valueChanged.connect(
            self._on_nesting_allowance_changed
        )
        group_box_debug_events_layout = QGridLayout()
        group_box_debug_events_layout.addWidget(self.label_stack_depth, 0, 0)
        group_box_debug_events_layout.addWidget(self.sb_stack_depth, 0, 1)
        group_box_debug_events_layout.addWidget(
            self.label_nesting_allowance, 1, 0
        )
        group_box_debug_events_layout.addWidget(
            self.sb_nesting_allowance, 1, 1
        )
        self.cb_debug_events.setLayout(group_box_debug_events_layout)

        # Buttons
        self.btn_clear = QPushButton("Clear output")
        self.btn_clear.setToolTip("Clear output area")
        self.btn_clear.clicked.connect(self._on_clear)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_clear)

        # TextBrowser
        self.output = QTextBrowser(self)
        self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self._handle_file_link)

        # Layout
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.cb_event_filter)
        self.layout().addWidget(self.cb_debug_events)
        self.layout().addLayout(btn_layout)
        self.layout().addWidget(self.output)

    def _on_event_filter(self, enabled):
        qapp = QApplication.instance()
        if qapp:
            if enabled:
                qapp.installEventFilter(self)
            else:
                qapp.removeEventFilter(self)

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

    def _handle_file_link(self, url):
        if not url.scheme():
            url = QUrl.fromLocalFile(url.toString())
        QDesktopServices.openUrl(url)

    def _on_log_debug_events(self, enabled):
        def _handle_debug_event_output(event, cfg=self._debug_event_settings):
            """Print info about what caused this event to be emitted."""
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
                if obj:
                    ln = f'  <a href="{frame.filename}">"{fname}", line {frame.lineno}, in {obj}{frame.function}</a>'
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

            # separate groups of events
            if cfg._cur_depth <= 0:
                cfg._cur_depth = 0
                self._append_output(
                    self.TEXT_DIVIDER, alignment=Qt.AlignCenter
                )
            elif not cfg.nesting_allowance:
                return

            # log it
            output = indent("<br>".join(lines), "  " * cfg._cur_depth)
            self._append_output(
                f"<pre>{output}</pre>", alignment=Qt.AlignLeft, is_html=True
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

    def _on_stack_depth_changed(self, depth):
        self._debug_event_settings.stack_depth = depth

    def _on_nesting_allowance_changed(self, nesting_allowance):
        self._debug_event_settings.nesting_allowance = nesting_allowance

    def eventFilter(self, qobject, qevent):
        if Qt.ControlModifier == QApplication.keyboardModifiers():
            if qevent.type() == QEvent.Type.MouseButtonPress:
                if qevent.buttons() == Qt.RightButton:
                    qobject_string = (
                        str(qobject)
                        .replace("<", "&#60;")
                        .replace(">", "&#62;")
                    )
                    qobject_class = (
                        str(qobject.__class__)
                        .replace("<", "&#60;")
                        .replace(">", "&#62;")
                    )
                    start_qobject_paths = ["QtGui.QWindow"]
                    qobject_module = inspect.getmodule(qobject)
                    if qobject_module:
                        qobject_module_link = f"{qobject_module}".replace(
                            "<", "&#60;"
                        ).replace(">", "&#62;")
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
                                qobject_module_link = f'<a href="{qobject_module_file}">{qobject_module_string}</a>'
                        except TypeError:
                            pass
                        qobject_info = f"Object: {qobject_string}<br>  Class: {qobject_class}<br>  Module: {qobject_module_link}"
                        qobject_doc = inspect.getdoc(qobject)
                        if qobject_doc and self.cb_object_doc.isChecked():
                            qobject_doc = qobject_doc.replace(
                                "<", "&#60;"
                            ).replace(">", "&#62;")
                            qobject_info = f"Object: {qobject_string}<br>  Class: {qobject_class}<br>  Doc: {qobject_doc}<br>  Module: {qobject_module_link}"
                        if any(
                            match in qobject_class
                            for match in start_qobject_paths
                        ):
                            self._append_output(
                                self.TEXT_DIVIDER, alignment=Qt.AlignCenter
                            )
                        else:
                            self._append_output(
                                indent(f"<pre>{qobject_info}</pre>", "  "),
                                is_html=True,
                            )

                    qevent.ignore()
        return super().eventFilter(qobject, qevent)
