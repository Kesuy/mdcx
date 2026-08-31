from __future__ import annotations

import copy
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "mdcx" / "views"
SOURCE = VIEWS / "MDCx.ui"
POSTER_CUT_SOURCE = VIEWS / "posterCutTool.ui"


@dataclass(frozen=True)
class Component:
    object_name: str
    class_name: str
    ui_name: str
    py_name: str


COMPONENTS = (
    Component("page_main", "MainPage", "main_page.ui", "main_page.py"),
    Component("page_log", "LogPage", "log_page.ui", "log_page.py"),
    Component("page_net", "NetworkPage", "network_page.ui", "network_page.py"),
    Component("page_tool", "ToolPage", "tool_page.ui", "tool_page.py"),
    Component("page_setting", "SettingsPage", "settings_page.ui", "settings_page.py"),
    Component("page_about", "AboutPage", "about_page.ui", "about_page.py"),
    Component("widget_nfo", "NfoOverlay", "nfo_overlay.ui", "nfo_overlay.py"),
)


def _set_string_property(widget: ET.Element, name: str, value: str) -> None:
    if widget.find(f"./property[@name='{name}']") is not None:
        return
    prop = ET.SubElement(widget, "property", {"name": name, "stdset": "0"})
    ET.SubElement(prop, "string").text = value


def _migrate_semantic_role(widget: ET.Element, style: str, ui_name: str) -> None:
    """Preserve intent from Designer-era QSS as a theme-owned property."""
    if ui_name != "settings_page.ui":
        return
    widget_class = widget.get("class", "")
    compact = style.replace(" ", "").lower()
    role = None
    if widget_class == "QLabel":
        if "255,38,0" in compact:
            role = "danger"
        elif "10,52,255" in compact:
            role = "link"
        elif "8,128,128" in compact:
            role = "help"
    elif widget_class == "QPushButton" and "background-color:rgba(255,255,255,0)" in compact:
        role = "ghost"
    elif widget_class in {"QLineEdit", "QPlainTextEdit", "QTextEdit"}:
        role = "code" if "courier" in compact else "input"
    elif widget_class == "QGroupBox" and "courier" in compact:
        role = "codeGroup"
    elif widget.get("name") == "gridLayoutWidget_6":
        role = "mutedContainer"
    if role is not None:
        _set_string_property(widget, "semanticRole", role)
    if widget.get("name") == "label_300":
        _set_string_property(widget, "semanticEmphasis", "hero")


def strip_inline_qss() -> None:
    """Remove page-local QSS so all visual rules come from theme tokens."""
    paths = [SOURCE, POSTER_CUT_SOURCE, *(VIEWS / component.ui_name for component in COMPONENTS)]
    for path in paths:
        tree = ET.parse(path)
        root = tree.getroot()
        changed = False
        for widget in root.findall(".//widget"):
            for prop in list(widget.findall("./property[@name='styleSheet']")):
                style = "".join(prop.itertext()).strip()
                if style:
                    _migrate_semantic_role(widget, style, path.name)
                widget.remove(prop)
                changed = True
        if changed:
            _write_xml(tree, path)


def _int_property(widget: ET.Element, name: str, field: str) -> int:
    value = widget.findtext(f"./property[@name='{name}']/{field}")
    if value is None:
        raise RuntimeError(f"{widget.get('name')} 缺少 {name}/{field}")
    return int(value)


def _set_number_property(parent: ET.Element, name: str, value: int) -> None:
    prop = ET.SubElement(parent, "property", {"name": name})
    ET.SubElement(prop, "number").text = str(value)


def _set_group_minimum_height(group: ET.Element, height: int) -> None:
    existing = group.find("./property[@name='minimumSize']")
    if existing is None:
        existing = ET.Element("property", {"name": "minimumSize"})
        geometry = group.find("./property[@name='geometry']")
        insert_at = list(group).index(geometry) + 1 if geometry is not None else 0
        group.insert(insert_at, existing)
    size = existing.find("size")
    if size is None:
        size = ET.SubElement(existing, "size")
    width = size.find("width")
    if width is None:
        width = ET.SubElement(size, "width")
    width.text = "0"
    height_node = size.find("height")
    if height_node is None:
        height_node = ET.SubElement(size, "height")
    height_node.text = str(height)


def migrate_settings_group_layouts() -> None:
    """Persist legacy settings-group coordinates as native Designer grids.

    The old form stored every child directly under a QGroupBox with geometry.
    Convert those coordinates once into grid metadata so Qt owns layout from
    object construction onward; runtime controllers must never rebuild it.
    """
    path = VIEWS / "settings_page.ui"
    tree = ET.parse(path)
    root = tree.getroot()
    changed = False
    for group in root.findall(".//widget[@class='QGroupBox']"):
        if group.find("./layout") is not None:
            continue
        widgets = [child for child in list(group) if child.tag == "widget"]
        if not widgets:
            continue

        rects: dict[int, tuple[int, int, int, int]] = {}
        x_points: set[int] = set()
        y_points: set[int] = set()
        for widget in widgets:
            geometry = widget.find("./property[@name='geometry']")
            if geometry is None:
                raise RuntimeError(f"{group.get('name')}/{widget.get('name')} 缺少 geometry")
            x = _int_property(widget, "geometry", "rect/x")
            y = _int_property(widget, "geometry", "rect/y")
            width = _int_property(widget, "geometry", "rect/width")
            height = _int_property(widget, "geometry", "rect/height")
            rects[id(widget)] = (x, y, width, height)
            x_points.update((x, x + width))
            y_points.update((y, y + height))

        xs = sorted(x_points)
        ys = sorted(y_points)
        x_index = {point: index for index, point in enumerate(xs)}
        y_index = {point: index for index, point in enumerate(ys)}
        group_width = _int_property(group, "geometry", "rect/width")
        group_height = _int_property(group, "geometry", "rect/height")
        max_right = max(x + width for x, _y, width, _height in rects.values())
        max_bottom = max(y + height for _x, y, _width, height in rects.values())

        layout = ET.Element(
            "layout",
            {
                "class": "QGridLayout",
                "name": f"{group.get('name')}_responsive_layout",
                "columnminimumwidth": ",".join(
                    str(max(1, end - start)) for start, end in zip(xs, xs[1:], strict=False)
                ),
                "columnstretch": ",".join(str(max(1, end - start)) for start, end in zip(xs, xs[1:], strict=False)),
                "rowminimumheight": ",".join(str(max(1, end - start)) for start, end in zip(ys, ys[1:], strict=False)),
            },
        )
        _set_number_property(layout, "leftMargin", max(0, xs[0]))
        _set_number_property(layout, "topMargin", max(18, ys[0]))
        _set_number_property(layout, "rightMargin", max(0, group_width - max_right))
        _set_number_property(layout, "bottomMargin", max(10, group_height - max_bottom))
        _set_number_property(layout, "horizontalSpacing", 0)
        _set_number_property(layout, "verticalSpacing", 0)

        for widget in sorted(widgets, key=lambda item: (rects[id(item)][1], rects[id(item)][0])):
            x, y, width, height = rects[id(widget)]
            geometry = widget.find("./property[@name='geometry']")
            widget.remove(geometry)
            row = y_index[y]
            column = x_index[x]
            row_span = max(1, y_index[y + height] - row)
            column_span = max(1, x_index[x + width] - column)
            attrs = {"row": str(row), "column": str(column)}
            if row_span > 1:
                attrs["rowspan"] = str(row_span)
            if column_span > 1:
                attrs["colspan"] = str(column_span)
            item = ET.SubElement(layout, "item", attrs)
            group.remove(widget)
            item.append(widget)

        for zorder in list(group.findall("./zorder")):
            group.remove(zorder)
        _set_group_minimum_height(group, group_height)
        group.append(layout)
        changed = True

    if changed:
        _write_xml(tree, path)


def normalize_settings_special_layouts() -> None:
    """Use intentional nested layouts for groups whose rows are extended at runtime."""
    path = VIEWS / "settings_page.ui"
    tree = ET.parse(path)
    root = tree.getroot()
    group = root.find(".//widget[@name='groupBox_10']")
    if group is None:
        raise RuntimeError("UI 中找不到 groupBox_10")
    current = group.find("./layout")
    if current is None or current.get("class") == "QVBoxLayout":
        return

    widgets = {widget.get("name"): widget for widget in current.findall("./item/widget")}
    expected = {"gridLayoutWidget_10", "label_75", "label_7", "label_get_cookie_url"}
    if set(widgets) != expected:
        raise RuntimeError(f"groupBox_10 子控件不符合预期: {sorted(widgets)}")

    layout = ET.Element("layout", {"class": "QVBoxLayout", "name": "groupBox_10_layout"})
    _set_number_property(layout, "leftMargin", 20)
    _set_number_property(layout, "topMargin", 26)
    _set_number_property(layout, "rightMargin", 20)
    _set_number_property(layout, "bottomMargin", 16)
    _set_number_property(layout, "spacing", 10)
    for name in ("gridLayoutWidget_10", "label_75"):
        item = ET.SubElement(layout, "item")
        item.append(widgets[name])
    row_item = ET.SubElement(layout, "item")
    row = ET.SubElement(
        row_item,
        "layout",
        {"class": "QHBoxLayout", "name": "horizontalLayout_cookie_links", "stretch": "0,1"},
    )
    for name in ("label_7", "label_get_cookie_url"):
        item = ET.SubElement(row, "item")
        item.append(widgets[name])

    group.remove(current)
    group.append(layout)
    _write_xml(tree, path)


def _find_widget(root: ET.Element, object_name: str) -> ET.Element:
    widget = root.find(f".//widget[@name='{object_name}']")
    if widget is None:
        raise RuntimeError(f"UI 中找不到 {object_name}")
    return widget


def _empty_widget(widget: ET.Element) -> None:
    for child in list(widget):
        if child.tag in {"widget", "layout", "zorder"}:
            widget.remove(child)


def _component_document(source_root: ET.Element, component: Component, widget: ET.Element) -> ET.ElementTree:
    root = ET.Element("ui", {"version": source_root.get("version", "4.0")})
    ET.SubElement(root, "class").text = component.class_name
    root.append(copy.deepcopy(widget))
    custom_widgets = source_root.find("customwidgets")
    if custom_widgets is not None:
        root.append(copy.deepcopy(custom_widgets))
    resources = source_root.find("resources")
    root.append(copy.deepcopy(resources) if resources is not None else ET.Element("resources"))
    root.append(ET.Element("connections"))
    return ET.ElementTree(root)


def _write_xml(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True, short_empty_elements=True)


def split() -> None:
    source_tree = ET.parse(SOURCE)
    source_root = source_tree.getroot()
    if source_root.findtext("class") == "MDCxShell":
        return
    extracted: list[tuple[Component, ET.Element]] = []
    for component in COMPONENTS:
        widget = _find_widget(source_root, component.object_name)
        extracted.append((component, copy.deepcopy(widget)))
        _empty_widget(widget)

    for component, widget in extracted:
        _write_xml(_component_document(source_root, component, widget), VIEWS / component.ui_name)

    source_root.find("class").text = "MDCxShell"
    _write_xml(source_tree, SOURCE)


def generate() -> None:
    commands = [(SOURCE, VIEWS / "MDCx_shell.py"), (POSTER_CUT_SOURCE, VIEWS / "posterCutTool.py")]
    commands.extend((VIEWS / component.ui_name, VIEWS / component.py_name) for component in COMPONENTS)
    for ui_path, py_path in commands:
        subprocess.run(
            [sys.executable, "-m", "PyQt6.uic.pyuic", str(ui_path), "-o", str(py_path)],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    split()
    strip_inline_qss()
    migrate_settings_group_layouts()
    normalize_settings_special_layouts()
    generate()
