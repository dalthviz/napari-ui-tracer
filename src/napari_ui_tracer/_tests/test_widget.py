import sys

import pytest
from qtpy.QtCore import Qt

from napari_ui_tracer import QtNapariUITracer


def test_qt_event_filter(make_napari_viewer, qtbot):
    """
    Test the qt event filter based functionality.
    """
    # get widget
    viewer = make_napari_viewer()
    qt_viewer = viewer.window._qt_viewer

    with qtbot.waitExposed(qt_viewer):
        viewer.show()

    # create our widget, passing in the viewer
    widget = QtNapariUITracer()

    # enable eventFilter install
    widget.cb_event_filter.setChecked(True)
    assert widget.cb_object_doc.isEnabled()

    # interact with viewer to see if event is captured
    qtbot.mouseClick(qt_viewer, Qt.RightButton, Qt.ControlModifier)

    # read captured output and check that it's as we expected
    captured_plain = widget.output.toPlainText()
    assert "QtViewer" in captured_plain
    assert "QWidget" in captured_plain
    assert "_QtMainWindow" in captured_plain

    captured_html = widget.output.toHtml()
    assert "file://" in captured_html

    # call clear output and check that output is clear
    qtbot.mouseClick(widget.btn_clear, Qt.LeftButton)
    assert widget.output.toPlainText() == ""

    # disable eventFilter uninstall
    widget.cb_event_filter.setChecked(False)
    assert not widget.cb_object_doc.isEnabled()

    # interact with viewer to see if event is captured
    qtbot.mouseClick(qt_viewer, Qt.RightButton, Qt.ControlModifier)

    assert widget.output.toPlainText() == ""

    # interact with doc option enabled
    widget.cb_event_filter.setChecked(True)
    widget.cb_object_doc.setChecked(True)
    qtbot.mouseClick(qt_viewer, Qt.RightButton, Qt.ControlModifier)
    captured_doc = widget.output.toPlainText()
    assert "Qt view for the napari Viewer model." in captured_doc


@pytest.mark.skipif(
    sys.platform != "darwin", reason="Only works on macOS. See QTBUG-5232"
)
def test_application_events_logging(make_napari_viewer, qtbot):
    """
    Test logging events and logging config functionality.
    """
    # get widget
    viewer = make_napari_viewer()
    qt_viewer = viewer.window._qt_viewer

    with qtbot.waitExposed(qt_viewer):
        viewer.show()

    # create our widget, passing in the viewer
    widget = QtNapariUITracer()

    # enable event logging
    widget.cb_log_events.setChecked(True)
    assert widget.sb_stack_depth.isEnabled()
    assert widget.sb_nesting_allowance.isEnabled()

    # move mouse to viewer
    qtbot.mouseMove(qt_viewer)
    qtbot.waitUntil(lambda: "_enter_canvas" in widget.output.toPlainText())
    assert "enterEvent" in widget.output.toPlainText()
    widget._on_clear()

    # move mouse out of viewer
    qtbot.mouseMove(widget)
    qtbot.waitUntil(lambda: "_leave_canvas" in widget.output.toPlainText())
    assert "leaveEvent" in widget.output.toPlainText()
    widget._on_clear()

    # set stack_depth to 1 and move mouse to viewer again
    widget.sb_stack_depth.setValue(1)
    qtbot.mouseMove(qt_viewer)
    qtbot.waitUntil(lambda: "enterEvent" in widget.output.toPlainText())
    assert "_enter_canvas" not in widget.output.toPlainText()
    widget._on_clear()

    # disable event logging
    widget.cb_log_events.setChecked(False)
    assert not widget.sb_stack_depth.isEnabled()
    assert not widget.sb_nesting_allowance.isEnabled()

    # move mouse out of viewer again
    qtbot.mouseMove(widget)
    assert widget.output.toPlainText() == ""
