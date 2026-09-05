from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import (
    FORM_SECTION_HORIZONTAL_MARGIN,
    apply_responsive_layout,
    setup_responsive_ui,
)
from mdcx.controllers.main_window.style import set_dark_style, set_style
from tests.layout_test_support import APP, generated_ui_window


def test_tool_page_groups_use_page_owned_layouts_instead_of_fixed_geometry():
    window = generated_ui_window()

    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1200, 850)
    window.show()
    APP.processEvents()

    for group in (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    ):
        assert group.layout() is not None
        assert group.maximumWidth() == 16777215
        assert group.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding

    assert window.Ui.groupBox_7.layout().indexOf(window.Ui.lineEdit_single_file_path) >= 0
    assert window.Ui.groupBox_19.layout().indexOf(window.Ui.lineEdit_local_library_path) >= 0
    assert window.Ui.groupBox_6.layout().indexOf(window.Ui.lineEdit_escape_dir_move) >= 0
    assert window.Ui.groupBox_13.layout().indexOf(window.Ui.pushButton_select_thumb) >= 0
    assert window.Ui.groupBox_21.layout().indexOf(window.Ui.lineEdit_netdisk_path) >= 0

    for button in (
        window.Ui.pushButton_select_file,
        window.Ui.pushButton_select_file_clear_info,
        window.Ui.pushButton_select_local_library,
        window.Ui.pushButton_select_netdisk_path,
        window.Ui.pushButton_select_localdisk_path,
    ):
        assert button.size().width() == 92
        assert button.size().height() == 34
        assert button.property("toolRole") == "secondary"
    for button in (
        window.Ui.pushButton_start_single_file,
        window.Ui.pushButton_find_missing_number,
        window.Ui.pushButton_move_mp4,
        window.Ui.pushButton_creat_symlink,
    ):
        assert button.size().width() == 220
        assert button.size().height() == 38
        assert button.property("toolRole") == "primary"
    window.close()


def test_tool_page_expands_layout_managed_forms_and_keeps_scrollbar_at_right():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1600, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    scroll_area = window.Ui.scrollArea_10
    content = scroll_area.widget()
    assert content.width() == scroll_area.viewport().width()
    assert isinstance(content.layout(), QVBoxLayout)
    assert content.layout().spacing() == 18
    groups = (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    )
    for group in groups:
        assert group.width() == scroll_area.viewport().width() - 2 * FORM_SECTION_HORIZONTAL_MARGIN
        assert group.layout() is not None
        assert abs(group.geometry().center().x() - content.rect().center().x()) <= 1
        visible_children = [child for child in group.children() if isinstance(child, QWidget) and child.isVisible()]
        assert visible_children
        assert all(group.rect().contains(child.geometry()) for child in visible_children)
    scrollbar_x = scroll_area.verticalScrollBar().mapTo(window.Ui.page_tool, QPoint()).x()
    assert scrollbar_x >= window.Ui.page_tool.width() - 30
    page_margins = window.Ui.page_tool.layout().contentsMargins()
    assert (page_margins.left(), page_margins.top(), page_margins.right(), page_margins.bottom()) == (18, 8, 10, 8)
    content_margins = content.layout().contentsMargins()
    assert (content_margins.left(), content_margins.right()) == (
        FORM_SECTION_HORIZONTAL_MARGIN,
        FORM_SECTION_HORIZONTAL_MARGIN,
    )
    window.close()


def test_tool_page_resyncs_width_when_opened_after_startup_without_window_resize():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(1100, 700)
    window.show()
    APP.processEvents()

    groups = (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    )
    for group in groups:
        group.setMinimumWidth(400)

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    APP.processEvents()

    viewport_width = window.Ui.scrollArea_10.viewport().width()
    expected_width = viewport_width - 2 * FORM_SECTION_HORIZONTAL_MARGIN
    assert expected_width > 400
    assert window.Ui.scrollArea_10.widget().width() == viewport_width
    assert all(group.width() == expected_width for group in groups)
    window.close()


def test_tool_page_reopens_at_top_and_form_controls_share_one_radius():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0
    set_style(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1200, 720)
    window.show()
    APP.processEvents()

    scroll_bar = window.Ui.scrollArea_10.verticalScrollBar()
    scroll_bar.setValue(scroll_bar.maximum())
    assert scroll_bar.value() > scroll_bar.minimum()
    MyMAinWindow._reset_tool_scroll_position(window)
    assert scroll_bar.value() == scroll_bar.minimum()

    for control in (
        window.Ui.lineEdit_single_file_path,
        window.result_sort_combo,
        window.Ui.plainTextEdit_cookie_javdb,
    ):
        assert control.property("mdcxControlRadius") == 8
        assert control.styleSheet() == ""
        assert "border-radius: 15px" not in control.styleSheet()
    assert "border-radius:8px" in window.Ui.centralwidget.styleSheet().replace(" ", "")

    tool_style = window.Ui.page_tool.styleSheet()
    assert "background: #FFFFFF" in tool_style
    assert "background: #F5F5F6" in tool_style
    assert "margin-top: 10px" not in tool_style
    assert "margin-top: 0" in tool_style
    assert "subcontrol-origin: border" in tool_style
    assert 'QPushButton[toolRole="primary"]' in tool_style
    sidebar_style = window.Ui.widget_setting.styleSheet()
    assert "border-top-right-radius: 0" in sidebar_style
    assert "border-bottom-right-radius: 0" in sidebar_style

    window.dark_mode = True
    set_dark_style(window)
    assert "background: #18222D" in window.Ui.page_tool.styleSheet()
    assert "background: rgba(180, 180, 180, 20)" in window.Ui.page_tool.styleSheet()
    assert "margin-top: 10px" not in window.Ui.page_tool.styleSheet()
    assert "background: #2F3A46" in window._shell_splitter.styleSheet()

    window.dark_mode = False
    set_style(window)
    window.close()
