from mdcx.controllers.main_window.responsive_layout import setup_responsive_ui
from tests.layout_test_support import generated_ui_window


def test_primary_workflows_have_accessible_names_buddies_and_tab_order():
    window = generated_ui_window()

    setup_responsive_ui(window)

    assert window.Ui.pushButton_start_cap.accessibleName() == "开始或停止刮削"
    assert window.result_filter_edit.accessibleName() == "搜索刮削结果"
    assert window.Ui.lineEdit_single_file_path.accessibleName() == "单文件路径"
    assert window.Ui.label_3.buddy() is window.Ui.lineEdit_single_file_path
    assert window.Ui.label_10.buddy() is window.Ui.lineEdit_appoint_url
    assert window.Ui.pushButton_select_media_folder.nextInFocusChain() is window.Ui.pushButton_start_cap
    window.close()
