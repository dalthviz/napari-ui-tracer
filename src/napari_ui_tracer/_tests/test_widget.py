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
    qtbot.mouseClick(qt_viewer, Qt.RightButton,
                     modifier=Qt.ControlModifier)

    # read captured output and check that it's as we expected
    captured = widget.output.toPlainText()
    assert "QtViewer" in captured
    assert "QWidget" in captured
    assert "_QtMainWindow" in captured

    # call clear output and check that output is clear
    widget._on_clear()
    assert widget.output.toPlainText() == ""

    # call eventFilter uninstall
    widget._on_uninstall()

    # interact with viewer to see if event is captured
    qtbot.mouseClick(qt_viewer, Qt.RightButton,
                     modifier=Qt.ControlModifier)

    assert widget.output.toPlainText() == ""
