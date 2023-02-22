from qtpy.QtCore import Qt

from napari_ui_tracer import QtNapariUITracer


def test_qt_napari_ui_tracer(make_napari_viewer, qtbot):
    # make viewer
    viewer = make_napari_viewer()
    qt_viewer = viewer.window._qt_viewer

    with qtbot.waitExposed(qt_viewer):
        viewer.show()

    # create our widget, passing in the viewer
    widget = QtNapariUITracer()

    # call eventFilter install
    widget._on_install()
    assert not widget.btn_install.isEnabled()
    assert widget.btn_uninstall.isEnabled()

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
    widget._on_clear()
    assert widget.output.toPlainText() == ""

    # call eventFilter uninstall
    widget._on_uninstall()
    assert widget.btn_install.isEnabled()
    assert not widget.btn_uninstall.isEnabled()

    # interact with viewer to see if event is captured
    qtbot.mouseClick(qt_viewer, Qt.RightButton, Qt.ControlModifier)

    assert widget.output.toPlainText() == ""
