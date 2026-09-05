from __future__ import annotations

import re
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from mdcx.config.enums import NfoInclude, Website
from mdcx.config.manager import manager
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData
from mdcx.signals import signal_qt

from .ui_text import set_elided_label_text


class PreviewControllerMixin:
    @staticmethod
    def _provenance_tooltip(data: CrawlersResult, field: CrawlerResultFields | str, base: str = "") -> str:
        provenance = data.get_provenance(field)
        if provenance is None:
            return base
        return "\n".join(part for part in (base, provenance.describe()) if part)

    def _restore_layout_managed_provenance_tooltips(self) -> None:
        show_data = getattr(self, "show_data", None)
        if show_data is None:
            return
        data = show_data.data
        for label, field in (
            (self.Ui.label_outline, CrawlerResultFields.OUTLINE),
            (self.Ui.label_tag, CrawlerResultFields.TAGS),
            (self.Ui.label_director, CrawlerResultFields.DIRECTORS),
            (self.Ui.label_studio, CrawlerResultFields.STUDIO),
            (self.Ui.label_publish, CrawlerResultFields.PUBLISHER),
        ):
            base = str(label.property("mdcxFullText") or "")
            label.setToolTip(self._provenance_tooltip(data, field, base))

    def set_main_info(self, show_data: ShowData | None):
        if show_data is not None:
            self.show_data = show_data
            file_info = show_data.file_info
            data = show_data.data
            other = show_data.other
            self.show_name = show_data.show_name
        else:
            file_info = FileInfo.empty()
            data = CrawlersResult.empty()
            other = OtherInfo.empty()
            self.show_name = None
        try:
            number = data.number
            set_elided_label_text(self.Ui.label_number, number)
            self._set_main_source_url(data)
            actor = str(data.actor)
            if data.all_actor and NfoInclude.ACTOR_ALL in manager.config.nfo_include_new:
                actor = str(data.all_actor)
            self.Ui.label_actor.setToolTip(self._provenance_tooltip(data, CrawlerResultFields.ACTORS, actor))
            if number and not actor:
                actor = manager.config.actor_no_name
            if len(actor) > 10:
                actor = actor[:9] + "……"
            self.Ui.label_actor.setText(actor)
            self.file_main_open_path = file_info.file_path  # 文件路径

            title = data.title.split("\n")[0].strip(" :")
            self.Ui.label_title.setToolTip(self._provenance_tooltip(data, CrawlerResultFields.TITLE, title))
            if len(title) > 27:
                title = title[:25] + "……"
            self.Ui.label_title.setText(title)
            outline = str(data.outline)
            set_elided_label_text(self.Ui.label_outline, outline, mode=Qt.TextElideMode.ElideRight)
            self.Ui.label_outline.setToolTip(
                self._provenance_tooltip(data, CrawlerResultFields.OUTLINE, self.Ui.label_outline.toolTip())
            )
            tag = str(data.tag).strip(" [',']").replace("'", "")
            set_elided_label_text(self.Ui.label_tag, tag, mode=Qt.TextElideMode.ElideRight)
            self.Ui.label_tag.setToolTip(
                self._provenance_tooltip(data, CrawlerResultFields.TAGS, self.Ui.label_tag.toolTip())
            )
            set_elided_label_text(self.Ui.label_release, str(data.release), mode=Qt.TextElideMode.ElideRight)
            if data.runtime:
                set_elided_label_text(
                    self.Ui.label_runtime,
                    str(data.runtime) + " 分钟",
                    mode=Qt.TextElideMode.ElideRight,
                )
            else:
                set_elided_label_text(self.Ui.label_runtime, "", mode=Qt.TextElideMode.ElideRight)
            set_elided_label_text(self.Ui.label_director, str(data.director), mode=Qt.TextElideMode.ElideRight)
            set_elided_label_text(self.Ui.label_series, str(data.series), mode=Qt.TextElideMode.ElideRight)
            set_elided_label_text(self.Ui.label_studio, data.studio, mode=Qt.TextElideMode.ElideRight)
            set_elided_label_text(self.Ui.label_publish, data.publisher, mode=Qt.TextElideMode.ElideRight)
            for label, field in (
                (self.Ui.label_director, CrawlerResultFields.DIRECTORS),
                (self.Ui.label_studio, CrawlerResultFields.STUDIO),
                (self.Ui.label_publish, CrawlerResultFields.PUBLISHER),
            ):
                label.setToolTip(self._provenance_tooltip(data, field, label.toolTip()))
            self._restore_layout_managed_provenance_tooltips()
            self.Ui.label_poster.setToolTip(self._provenance_tooltip(data, CrawlerResultFields.POSTER, "点击裁剪图片"))
            self.Ui.label_thumb.setToolTip(self._provenance_tooltip(data, "fanart", "点击裁剪图片"))
            provenance_lines = []
            for field in (
                CrawlerResultFields.TITLE,
                CrawlerResultFields.ORIGINALTITLE,
                CrawlerResultFields.ACTORS,
                CrawlerResultFields.STUDIO,
                CrawlerResultFields.DIRECTORS,
                CrawlerResultFields.TAGS,
                CrawlerResultFields.OUTLINE,
                CrawlerResultFields.POSTER,
                "fanart",
            ):
                provenance = data.get_provenance(field)
                if provenance is not None:
                    field_name = field.value if isinstance(field, CrawlerResultFields) else field
                    translated = "（已翻译/映射）" if provenance.translated else ""
                    provenance_lines.append(f"{field_name} ← {provenance.source or '未知'}{translated}")
            self.Ui.label_source.setToolTip("\n".join(provenance_lines))
            # 生成img_path，用来裁剪使用
            img_path = other.fanart_path if other.fanart_path and other.fanart_path.is_file() else other.thumb_path
            self.img_path = img_path
            if self.Ui.checkBox_cover.isChecked():  # 主界面显示封面和缩略图
                poster_path = other.poster_path
                thumb_path = other.thumb_path
                fanart_path = other.fanart_path
                if not (thumb_path and thumb_path.is_file()) and fanart_path and fanart_path.is_file():
                    thumb_path = fanart_path
                poster_from = data.poster_from
                cover_from = data.thumb_from
                self._request_preview_images(poster_path, thumb_path, poster_from, cover_from)
        except Exception:
            if not signal_qt.stop:
                signal_qt.show_traceback_log(traceback.format_exc())

    @staticmethod
    def _source_page_url(data: CrawlersResult) -> str:
        """返回与当前番号最相关、且可安全交给浏览器打开的来源详情页。"""

        external_ids = data.external_ids or {}

        def site_value(site) -> str:
            return site.value if isinstance(site, Website) else str(site)

        def valid_url(value) -> str:
            text = str(value or "").strip()
            return text if re.fullmatch(r"https?://[^\s]+", text, flags=re.IGNORECASE) else ""

        preferred_sources = (
            data.field_sources.get(CrawlerResultFields.NUMBER, ""),
            data.field_sources.get(CrawlerResultFields.TITLE, ""),
        )
        for source in preferred_sources:
            source_name = site_value(source)
            for site, external_id in external_ids.items():
                if site_value(site) == source_name and (url := valid_url(external_id)):
                    return url
        for external_id in external_ids.values():
            if url := valid_url(external_id):
                return url
        return ""

    def _set_main_source_url(self, data: CrawlersResult) -> None:
        self._main_source_url = self._source_page_url(data)
        self.Ui.label_number.setCursor(
            Qt.CursorShape.PointingHandCursor if self._main_source_url else Qt.CursorShape.ArrowCursor
        )
        self._restore_number_source_tooltip()

    def _restore_number_source_tooltip(self) -> None:
        number = str(self.Ui.label_number.property("mdcxFullText") or "")
        if self._main_source_url:
            self.Ui.label_number.setToolTip(f"点击打开来源网页\n{self._main_source_url}")
        else:
            self.Ui.label_number.setToolTip(number)

    def _request_preview_images(
        self,
        poster_path: Path | None,
        thumb_path: Path | None,
        poster_from="",
        cover_from="",
        force_reload: bool = False,
    ) -> None:
        self.preview_request_id += 1
        if not poster_path or not poster_path.is_file():
            self.resize_label_and_setpixmap([False, "", "暂无封面图", 156, 220], None)
        if not thumb_path or not thumb_path.is_file():
            self.resize_label_and_setpixmap(None, [False, "", "暂无缩略图", 328, 220])
        self.preview_image_loader.load(
            self.preview_request_id,
            poster_path,
            thumb_path,
            poster_from,
            cover_from,
            force_reload=force_reload,
        )

    def _apply_preview_images(self, request_id: int, poster_pix: list, thumb_pix: list) -> None:
        if request_id != self.preview_request_id:
            return
        poster_text = poster_pix[2] if poster_pix[2] != "暂无封面图" else ""
        thumb_text = thumb_pix[2] if thumb_pix[2] != "暂无缩略图" else ""
        self.Ui.label_poster_size.setText((poster_text + " " + thumb_text).strip())
        self.resize_label_and_setpixmap(poster_pix, thumb_pix)

    def resize_label_and_setpixmap(self, poster_pix, thumb_pix):
        if poster_pix is not None:
            if poster_pix[0]:
                poster_pixmap = (
                    poster_pix[1] if isinstance(poster_pix[1], QPixmap) else QPixmap.fromImage(poster_pix[1])
                )
                self._poster_source_pixmap = QPixmap(poster_pixmap)
                self._render_preview_pixmap(self.Ui.label_poster, self._poster_source_pixmap)
            else:
                self._poster_source_pixmap = None
                self.Ui.label_poster.clear()
                self.Ui.label_poster.setText(poster_pix[2])

        if thumb_pix is not None:
            if thumb_pix[0]:
                thumb_pixmap = thumb_pix[1] if isinstance(thumb_pix[1], QPixmap) else QPixmap.fromImage(thumb_pix[1])
                self._thumb_source_pixmap = QPixmap(thumb_pixmap)
                self._render_preview_pixmap(self.Ui.label_thumb, self._thumb_source_pixmap)
            else:
                self._thumb_source_pixmap = None
                self.Ui.label_thumb.clear()
                self.Ui.label_thumb.setText(thumb_pix[2])

    @staticmethod
    def _render_preview_pixmap(label: QLabel, source_pixmap: QPixmap | None) -> None:
        if source_pixmap is None or source_pixmap.isNull():
            return
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(
            source_pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def refresh_preview_pixmaps(self) -> None:
        self._render_preview_pixmap(self.Ui.label_poster, getattr(self, "_poster_source_pixmap", None))
        self._render_preview_pixmap(self.Ui.label_thumb, getattr(self, "_thumb_source_pixmap", None))
