"""Shared QGraphicsView-based canvas for interactive annotations.

Annotations are real QGraphicsItem objects (ResizableRectItem /
ResizableTextItem / ResizablePathItem) so the user can click to select,
drag to move, drag a corner handle to resize, double-click text to edit it,
and recolor / resize-font via the toolbar. `get_annotations()` serializes
the live scene into plain dicts (the same schema the app has always used)
so callers can bake them into a PDF page or a raster image without caring
about Qt internals.
"""
import copy
import os
import re
from enum import Enum, auto
from typing import Callable, Optional, Dict, Tuple, Any, List

from PyQt6.QtCore import Qt, QRectF, QPointF, QEvent, pyqtSignal
from PyQt6.QtGui import (
    QImage, QPixmap, QPen, QColor, QBrush, QPainterPath, QFont, QPainter,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QGuiApplication, QKeySequence
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem, QColorDialog, QInputDialog, QMenu,
    QMessageBox, QWidget
)
from spellchecker import SpellChecker

_spell: Optional[SpellChecker] = None


def _get_spell() -> SpellChecker:
    """Lazily build the spellchecker's word-frequency dictionary on first use
    instead of at import time, since loading it costs ~0.1s and every
    annotation-capable tab imports this module just to open at all."""
    global _spell
    if _spell is None:
        _spell = SpellChecker()
    return _spell


class _SpellCheckHighlighter(QSyntaxHighlighter):
    """Underlines words not found in the offline dictionary, like a normal
    word processor's red squiggle. No-op if pyspellchecker isn't installed.
    """

    _WORD_RE = re.compile(r"[A-Za-z']+")

    def __init__(self, document: Any) -> None:
        super().__init__(document)
        self._format = QTextCharFormat()
        self._format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self._format.setUnderlineColor(QColor(220, 40, 40))

    def highlightBlock(self, text: str) -> None:  # noqa: 21 (Qt virtual override, invoked by the framework)
        spell = _get_spell()
        for match in self._WORD_RE.finditer(text):
            word = match.group()
            if word.lower() not in spell:
                self.setFormat(match.start(), len(word), self._format)


def _make_spell_highlighter(document: Any) -> _SpellCheckHighlighter:
    """Attach a spellcheck highlighter to a QTextDocument."""
    return _SpellCheckHighlighter(document)


class Tool(Enum):
    SELECT = auto()
    RECT = auto()
    HIGHLIGHT = auto()
    TEXT = auto()
    FREEHAND = auto()
    ARROW = auto()
    REDACT = auto()
    CROP = auto()


HANDLE_SIZE = 8

SHORTCUTS_HELP_TEXT = (
    "ZOOM\n"
    "  Mouse wheel          Scroll\n"
    "  Ctrl + wheel         Zoom to cursor position\n"
    "  Trackpad pinch       Zoom (Mac / Windows precision touchpad)\n"
    "  Ctrl + =             Zoom in\n"
    "  Ctrl + -             Zoom out\n"
    "  Ctrl + 0             Reset / fit to window\n"
    "\n"
    "PAN\n"
    "  Hold Space + drag    Pan\n"
    "  Middle-mouse drag    Pan\n"
    "  Drag empty canvas    Pan (Select tool; on a PDF page, selects text instead)\n"
    "\n"
    "TEXT (PDF only)\n"
    "  Drag over page text  Select real page text (like a browser)\n"
    "  Ctrl + C             Copy the selected text\n"
    "\n"
    "EDITING\n"
    "  Click an item        Select it (handles appear on its corners)\n"
    "  Drag a handle        Resize (text: scales font size)\n"
    "  Double-click text    Edit its contents\n"
    "  Delete / Backspace   Delete the selected item\n"
    "  Ctrl + Z             Undo\n"
    "  Ctrl + Y             Redo\n"
    "  Ctrl + C             Copy composite to clipboard (image tab)\n"
)


def show_shortcuts_dialog(parent: QWidget) -> None:
    QMessageBox.information(parent, "Keyboard Shortcuts", SHORTCUTS_HELP_TEXT)


class ResizableMixin:
    """Corner/edge-handle resize + move + select, shared by every annotation
    item type. Must be mixed in alongside a QGraphicsItem subclass that
    implements `_local_rect()` / `_apply_local_rect(rect)`.
    """

    def _init_resizable(self) -> None:
        self._active_handle = None
        self._resize_start_rect = None
        self._resize_start_pos = None
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def _local_rect(self) -> QRectF:
        raise NotImplementedError

    def _apply_local_rect(self, rect: QRectF) -> None:
        raise NotImplementedError

    def _handle_rects(self) -> Dict[str, QRectF]:
        r = self._local_rect()
        s = HANDLE_SIZE
        cx, cy = r.center().x(), r.center().y()
        return {
            "tl": QRectF(r.left() - s / 2, r.top() - s / 2, s, s),
            "tm": QRectF(cx - s / 2, r.top() - s / 2, s, s),
            "tr": QRectF(r.right() - s / 2, r.top() - s / 2, s, s),
            "ml": QRectF(r.left() - s / 2, cy - s / 2, s, s),
            "mr": QRectF(r.right() - s / 2, cy - s / 2, s, s),
            "bl": QRectF(r.left() - s / 2, r.bottom() - s / 2, s, s),
            "bm": QRectF(cx - s / 2, r.bottom() - s / 2, s, s),
            "br": QRectF(r.right() - s / 2, r.bottom() - s / 2, s, s),
        }

    def _handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def paint_handles(self, painter: Any) -> None:
        if not self.isSelected():
            return
        painter.setPen(QPen(QColor(30, 144, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for rect in self._handle_rects().values():
            painter.drawRect(rect)

    def resizable_mouse_press(self, event: Any) -> bool:
        handle = self._handle_at(event.pos())
        if handle:
            self._active_handle = handle
            self._resize_start_rect = QRectF(self._local_rect())
            self._resize_start_pos = event.pos()
            event.accept()
            return True
        return False

    def resizable_mouse_move(self, event: Any) -> bool:
        if not self._active_handle:
            return False
        delta = event.pos() - self._resize_start_pos
        rect = QRectF(self._resize_start_rect)
        if "l" in self._active_handle:
            rect.setLeft(rect.left() + delta.x())
        if "r" in self._active_handle:
            rect.setRight(rect.right() + delta.x())
        if "t" in self._active_handle:
            rect.setTop(rect.top() + delta.y())
        if "b" in self._active_handle:
            rect.setBottom(rect.bottom() + delta.y())
        rect = rect.normalized()
        if rect.width() < 6:
            rect.setWidth(6)
        if rect.height() < 6:
            rect.setHeight(6)
        self._apply_local_rect(rect)
        return True

    def resizable_mouse_release(self, event: Any) -> bool:
        was_resizing = self._active_handle is not None
        self._active_handle = None
        return was_resizing

    def _notify_canvas(self) -> None:
        """Tell the owning AnnotationCanvas a discrete edit just finished,
        so it can record an undo snapshot."""
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, "commit_change"):
                view.commit_change()

    def _extended_shape(self, base_shape: QPainterPath) -> QPainterPath:
        """Widen a base QPainterPath to also cover the resize handles, so
        clicking a handle actually registers as clicking this item instead
        of falling through to whatever's underneath."""
        if not self.isSelected():
            return base_shape
        combined = QPainterPath(base_shape)
        for rect in self._handle_rects().values():
            combined.addRect(rect)
        return combined


class ResizableRectItem(ResizableMixin, QGraphicsRectItem):
    """A movable/resizable rectangle: used for rect, highlight, redact, and
    crop markers. `kind` controls its default appearance and how it gets
    baked into the final PDF/image."""

    def __init__(self, rect: QRectF, kind: str = "rect", color: Optional[QColor] = None) -> None:
        QGraphicsRectItem.__init__(self, rect)
        self._init_resizable()
        self.kind = kind
        self.pen_width = 2
        self.qcolor = QColor(220, 40, 40)
        self.set_color(color or self._default_color())
        self.setZValue(1)

    def _default_color(self) -> QColor:
        return {
            "rect": QColor(220, 40, 40),
            "highlight": QColor(255, 235, 59, 120),
            "redact": QColor(0, 0, 0),
            "crop": QColor(30, 144, 255),
        }.get(self.kind, QColor(220, 40, 40))

    def set_color(self, qcolor: QColor) -> None:
        if self.kind == "redact":
            qcolor = QColor(0, 0, 0)  # redaction must stay opaque black
        self.qcolor = qcolor
        if self.kind == "highlight":
            self.setBrush(QBrush(qcolor))
            self.setPen(QPen(Qt.PenStyle.NoPen))
        elif self.kind == "redact":
            self.setBrush(QBrush(qcolor))
            self.setPen(QPen(Qt.PenStyle.NoPen))
        elif self.kind == "crop":
            self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.setPen(QPen(qcolor, self.pen_width, Qt.PenStyle.DashLine))
        else:
            self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.setPen(QPen(qcolor, self.pen_width))

    def _local_rect(self) -> QRectF:
        return self.rect()

    def _apply_local_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self.setRect(rect)

    def boundingRect(self) -> QRectF:
        # Handles are painted outside the rect; Qt only repaints boundingRect(),
        # so padding prevents stale handle pixels when dragging.
        pad = HANDLE_SIZE / 2 + 2 + self.pen_width
        return self.rect().adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        return self._extended_shape(QGraphicsRectItem.shape(self))

    def paint(self, painter: Any, option: Any, widget: Optional[Any] = None) -> None:
        super().paint(painter, option, widget)
        self.paint_handles(painter)

    def mousePressEvent(self, event: Any) -> None:
        if self.resizable_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self.resizable_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        was_resizing = self.resizable_mouse_release(event)
        super().mouseReleaseEvent(event)
        self._notify_canvas()
        if self.kind == "crop" and self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, "crop_frame_adjusted"):
                view.crop_frame_adjusted.emit(self)

    def to_dict(self) -> Dict[str, Any]:
        r = self.mapRectToScene(self.rect())
        c = self.qcolor
        return {
            "type": self.kind,
            "rect": (r.x(), r.y(), r.width(), r.height()),
            "qcolor": c.getRgb(),
            "width": self.pen_width,
            "color": (c.redF(), c.greenF(), c.blueF()),
        }


class ResizableTextItem(ResizableMixin, QGraphicsTextItem):
    """Movable/resizable text. Dragging a corner handle scales the font
    size; double-clicking edits the text in place. Misspelled words (per
    an offline dictionary) get a red squiggly underline while editing, and
    right-clicking a misspelled word offers replacement suggestions."""

    def __init__(self, text: str = "Text", pos: Optional[QPointF] = None, font_size: int = 14, color: Optional[QColor] = None,
                 font_family: str = "Helvetica", bold: bool = False, italic: bool = False, letter_spacing: int = 100) -> None:
        QGraphicsTextItem.__init__(self, text)
        self._init_resizable()
        self.kind = "text"
        self.font_family = font_family
        self.letter_spacing = letter_spacing
        font = QFont(font_family, max(8, int(font_size)))
        font.setBold(bold)
        font.setItalic(italic)
        self._apply_letter_spacing(font)
        self.setFont(font)
        self.qcolor = QColor(30, 30, 30)
        self.set_color(color or QColor(30, 30, 30))
        if pos is not None:
            self.setPos(pos)
        self.setZValue(2)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._highlighter = _make_spell_highlighter(self.document())  # noqa: 21 (must stay referenced or Qt garbage-collects it)

    def _apply_letter_spacing(self, font: QFont) -> None:
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, float(self.letter_spacing))

    def set_color(self, qcolor: QColor) -> None:
        self.qcolor = qcolor
        self.setDefaultTextColor(qcolor)

    def set_font_size(self, size: int) -> None:
        font = self.font()
        font.setPointSize(max(4, int(size)))
        self.setFont(font)

    def font_size(self) -> int:
        return self.font().pointSize()

    def set_font_family(self, family: str) -> None:
        self.font_family = family
        font = self.font()
        font.setFamily(family)
        self.setFont(font)

    def set_bold(self, bold: bool) -> None:
        font = self.font()
        font.setBold(bold)
        self.setFont(font)

    def set_italic(self, italic: bool) -> None:
        font = self.font()
        font.setItalic(italic)
        self.setFont(font)

    def set_letter_spacing(self, percent: int) -> None:
        self.letter_spacing = percent
        font = self.font()
        self._apply_letter_spacing(font)
        self.setFont(font)

    def _local_rect(self) -> QRectF:
        return QGraphicsTextItem.boundingRect(self)

    def _apply_local_rect(self, rect: QRectF) -> None:
        old = QGraphicsTextItem.boundingRect(self)
        if old.width() > 0:
            ratio = rect.width() / old.width()
            self.set_font_size(max(4, round(self.font_size() * ratio)))

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE / 2 + 2
        return QGraphicsTextItem.boundingRect(self).adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        return self._extended_shape(QGraphicsTextItem.shape(self))

    def paint(self, painter: Any, option: Any, widget: Optional[Any] = None) -> None:
        super().paint(painter, option, widget)
        self.paint_handles(painter)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event: Any) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().focusOutEvent(event)
        self._notify_canvas()

    def mousePressEvent(self, event: Any) -> None:
        if self.resizable_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self.resizable_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        was_resizing = self.resizable_mouse_release(event)
        super().mouseReleaseEvent(event)
        self._notify_canvas()

    def contextMenuEvent(self, event: Any) -> None:
        """While editing, right-clicking a misspelled word offers fixes."""
        if self.textInteractionFlags() == Qt.TextInteractionFlag.TextEditorInteraction:
            spell = _get_spell()
            cursor = self.document().documentLayout().hitTest(
                event.pos(), Qt.HitTestAccuracy.FuzzyHit
            )
            text_cursor = QTextCursor(self.document())
            text_cursor.setPosition(cursor)
            text_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = text_cursor.selectedText()
            if word and word.isalpha() and word.lower() not in spell:
                menu = QMenu()
                suggestions = list(spell.candidates(word.lower()) or [])[:6]
                if suggestions:
                    for suggestion in suggestions:
                        action = menu.addAction(suggestion)
                        action.triggered.connect(
                            lambda checked, s=suggestion, c=text_cursor: self._replace_word(c, s)
                        )
                else:
                    menu.addAction("No suggestions").setEnabled(False)
                menu.exec(event.screenPos())
                return
        super().contextMenuEvent(event)

    def _replace_word(self, cursor: QTextCursor, replacement: str) -> None:
        cursor.insertText(replacement)
        self._notify_canvas()

    def to_dict(self) -> Dict[str, Any]:
        p = self.mapToScene(0, 0)
        c = self.qcolor
        font = self.font()
        return {
            "type": "text",
            "pos": (p.x(), p.y()),
            "text": self.toPlainText(),
            "font_size": self.font_size(),
            "font_family": self.font_family,
            "bold": font.bold(),
            "italic": font.italic(),
            "letter_spacing": self.letter_spacing,
            "qcolor": c.getRgb(),
            "color": (c.redF(), c.greenF(), c.blueF()),
        }


class ResizablePathItem(ResizableMixin, QGraphicsPathItem):
    """Movable/resizable freehand pen stroke. Resizing scales all points to
    fit the new bounding box."""

    def __init__(self, path: QPainterPath, color: Optional[QColor] = None, width: int = 2) -> None:
        QGraphicsPathItem.__init__(self, path)
        self._init_resizable()
        self.kind = "freehand"
        self.pen_width = width
        self.qcolor = QColor(220, 40, 40)
        self.set_color(color or QColor(220, 40, 40))
        self.setZValue(1)

    def set_color(self, qcolor: QColor) -> None:
        self.qcolor = qcolor
        self.setPen(QPen(qcolor, self.pen_width))

    def _local_rect(self) -> QRectF:
        return self.path().boundingRect()

    def _apply_local_rect(self, rect: QRectF) -> None:
        old = self.path().boundingRect()
        if old.width() == 0 or old.height() == 0:
            return
        sx = rect.width() / old.width()
        sy = rect.height() / old.height()
        old_path = self.path()
        new_path = QPainterPath()
        for i in range(old_path.elementCount()):
            el = old_path.elementAt(i)
            nx = rect.left() + (el.x - old.left()) * sx
            ny = rect.top() + (el.y - old.top()) * sy
            if i == 0:
                new_path.moveTo(nx, ny)
            else:
                new_path.lineTo(nx, ny)
        self.prepareGeometryChange()
        self.setPath(new_path)

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE / 2 + 2 + self.pen_width
        return self.path().boundingRect().adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        return self._extended_shape(QGraphicsPathItem.shape(self))

    def paint(self, painter: Any, option: Any, widget: Optional[Any] = None) -> None:
        super().paint(painter, option, widget)
        self.paint_handles(painter)

    def mousePressEvent(self, event: Any) -> None:
        if self.resizable_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self.resizable_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        was_resizing = self.resizable_mouse_release(event)
        super().mouseReleaseEvent(event)
        self._notify_canvas()

    def to_dict(self) -> Dict[str, Any]:
        path = self.path()
        pts = []
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            scene_pt = self.mapToScene(el.x, el.y)
            pts.append((scene_pt.x(), scene_pt.y()))
        c = self.qcolor
        return {
            "type": "freehand",
            "points": pts,
            "width": self.pen_width,
            "qcolor": c.getRgb(),
            "color": (c.redF(), c.greenF(), c.blueF()),
        }


class ResizableArrowItem(ResizableMixin, QGraphicsPathItem):
    """Movable/resizable directional arrow markup."""

    def __init__(self, start_pos: QPointF, end_pos: QPointF, color: Optional[QColor] = None, width: int = 3) -> None:
        QGraphicsPathItem.__init__(self)
        self._init_resizable()
        self.kind = "arrow"
        self.pen_width = width
        self.qcolor = color or QColor(220, 40, 40)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.set_color(self.qcolor)
        self.setZValue(1)
        self._update_arrow_path()

    def _update_arrow_path(self) -> None:
        p1 = self.start_pos
        p2 = self.end_pos
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length > 4:
            head_len = min(22.0, max(8.0, length * 0.25))
            ux = dx / length
            uy = dy / length
            perp_x = -uy
            perp_y = ux
            wing_width = head_len * 0.45
            base_x = p2.x() - ux * head_len
            base_y = p2.y() - uy * head_len
            w1 = QPointF(base_x + perp_x * wing_width, base_y + perp_y * wing_width)
            w2 = QPointF(base_x - perp_x * wing_width, base_y - perp_y * wing_width)
            path.moveTo(w1)
            path.lineTo(p2)
            path.lineTo(w2)
        self.prepareGeometryChange()
        self.setPath(path)

    def set_color(self, qcolor: QColor) -> None:
        self.qcolor = qcolor
        self.setPen(QPen(qcolor, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def _local_rect(self) -> QRectF:
        return self.path().boundingRect()

    def _apply_local_rect(self, rect: QRectF) -> None:
        old = self.path().boundingRect()
        if old.width() == 0 or old.height() == 0:
            return
        sx = rect.width() / old.width()
        sy = rect.height() / old.height()
        p1 = self.start_pos
        p2 = self.end_pos
        self.start_pos = QPointF(rect.left() + (p1.x() - old.left()) * sx, rect.top() + (p1.y() - old.top()) * sy)
        self.end_pos = QPointF(rect.left() + (p2.x() - old.left()) * sx, rect.top() + (p2.y() - old.top()) * sy)
        self._update_arrow_path()

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE / 2 + 3 + self.pen_width
        return self.path().boundingRect().adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        return self._extended_shape(QGraphicsPathItem.shape(self))

    def paint(self, painter: Any, option: Any, widget: Optional[Any] = None) -> None:
        super().paint(painter, option, widget)
        self.paint_handles(painter)

    def mousePressEvent(self, event: Any) -> None:
        if self.resizable_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self.resizable_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        was_resizing = self.resizable_mouse_release(event)
        super().mouseReleaseEvent(event)
        self._notify_canvas()

    def to_dict(self) -> Dict[str, Any]:
        p1 = self.mapToScene(self.start_pos)
        p2 = self.mapToScene(self.end_pos)
        c = self.qcolor
        return {
            "type": "arrow",
            "start": (p1.x(), p1.y()),
            "end": (p2.x(), p2.y()),
            "width": self.pen_width,
            "qcolor": c.getRgb(),
            "color": (c.redF(), c.greenF(), c.blueF()),
        }


class ResizableImageLayerItem(QGraphicsPixmapItem):
    """A directly manipulable image layer with visible corner resize handles."""

    HANDLE_SIZE = 10

    def __init__(self, pixmap: QPixmap) -> None:
        super().__init__(pixmap)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._active_handle = None
        self._start_pixmap = None
        self._start_pos = None
        self._start_mouse = None
        self.setData(0, "image-layer")
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

    def _handles(self) -> Dict[str, QRectF]:
        rect = self.pixmap().rect()
        half = self.HANDLE_SIZE / 2
        return {
            "tl": QRectF(rect.left() - half, rect.top() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "tr": QRectF(rect.right() - half, rect.top() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bl": QRectF(rect.left() - half, rect.bottom() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "br": QRectF(rect.right() - half, rect.bottom() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
        }

    def boundingRect(self) -> QRectF:
        pad = self.HANDLE_SIZE / 2 + 2
        return super().boundingRect().adjusted(-pad, -pad, pad, pad)

    def paint(self, painter: Any, option: Any, widget: Optional[Any] = None) -> None:
        super().paint(painter, option, widget)
        if not self.isSelected():
            return
        painter.setPen(QPen(QColor(91, 156, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for handle in self._handles().values():
            painter.drawRect(handle)

    def mousePressEvent(self, event: Any) -> None:
        if self.isSelected():
            for name, rect in self._handles().items():
                if rect.contains(event.pos()):
                    self._active_handle = name
                    self._start_pixmap = self.pixmap()
                    self._start_pos = self.pos()
                    self._start_mouse = event.pos()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self._active_handle is None:
            return super().mouseMoveEvent(event)
        delta = event.pos() - self._start_mouse
        width, height = self._start_pixmap.width(), self._start_pixmap.height()
        new_width = max(8, width + (delta.x() if "r" in self._active_handle else -delta.x()))
        new_height = max(8, height + (delta.y() if "b" in self._active_handle else -delta.y()))
        self.setPixmap(self._start_pixmap.scaled(
            round(new_width), round(new_height), Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        x = self._start_pos.x() + (width - new_width if "l" in self._active_handle else 0)
        y = self._start_pos.y() + (height - new_height if "t" in self._active_handle else 0)
        self.setPos(x, y)
        event.accept()

    def mouseReleaseEvent(self, event: Any) -> None:
        resized = self._active_handle is not None
        self._active_handle = None
        if resized:
            self._notify_change()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._notify_change()

    def contextMenuEvent(self, event: Any) -> None:
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, "image_layer_context_requested"):
                self.setSelected(True)
                view.image_layer_context_requested.emit(self, event.screenPos())
                event.accept()
                return
        super().contextMenuEvent(event)

    def _notify_change(self) -> None:
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, "image_layer_changed"):
                view.image_layer_changed.emit()


class AnnotationCanvas(QGraphicsView):
    """Shows a base image/page and hosts interactive annotation items."""

    selection_changed = pyqtSignal(object)  # emits the selected item, or None
    image_layer_changed = pyqtSignal()
    image_layer_context_requested = pyqtSignal(object, object)
    content_changed = pyqtSignal()
    crop_drawn = pyqtSignal(object)
    crop_frame_adjusted = pyqtSignal(object)
    file_dropped = pyqtSignal(str)
    visible_page_changed = pyqtSignal(int)  # PDF continuous scroll: index of the topmost visible page

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

        # Make scale()-based zoom (wheel, buttons, pinch) center on the
        # cursor/gesture position instead of the viewport center.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.base_item = None
        self.fit_mode = "window"  # "window" fits the whole page/image; "width" fits width and lets height scroll
        # PDF continuous scroll (set via set_pages instead of set_image): every
        # page is its own pixmap item, stacked vertically in one scene.
        self.page_items: List[QGraphicsPixmapItem] = []
        self.page_boundaries: List[Tuple[float, float]] = []  # (top_y, height) per page, scene coords
        self._visible_page = 0
        # When set (PDF tab only), dragging empty canvas selects real page text
        # instead of panning: (start, end, box_mode) -> (text, word_rects).
        self.text_provider: Optional[Callable[[QPointF, QPointF, bool], Tuple[str, List[QRectF]]]] = None
        self.text_select_box_mode = False
        self._text_selecting = False
        self._text_select_start = QPointF()
        self._text_select_rect_item: Optional[QGraphicsRectItem] = None
        self._text_highlight_items: List[QGraphicsRectItem] = []
        self._selected_text = ""
        self.tool = Tool.SELECT
        self.pen_width = 2
        self.current_color = QColor(0, 0, 0)  # black by default
        self.current_font_size = 14
        self.current_font_family = "Helvetica"
        self.current_bold = False
        self.current_italic = False
        self.current_letter_spacing = 100  # percent; 100 = normal

        self._history = []
        self._future = []
        self._suspend_history = False

        self._drawing = False
        self._start_pos = QPointF()
        self._freehand_path = None
        self._temp_item = None

        self.crop_item = None  # the single active crop-guide rectangle, if any

        # Panning state: Space-held, middle-mouse-drag, or (with the Select
        # tool) dragging on empty canvas all pan the view.
        self._space_held = False
        self._panning = False
        self._pan_last_pos = QPointF()
        self._nudging = False  # tracks an in-progress arrow-key nudge, so history is pushed once on release

        self.scene_.selectionChanged.connect(self._on_selection_changed)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._update_visible_page())

    # ---------- image loading ----------

    def set_text_select_box_mode(self, enabled: bool) -> None:
        """Toggle the Select tool between word-processor-style line-flow text
        selection (default) and the literal rectangular-drag clip."""
        self.text_select_box_mode = enabled

    def clear_text_selection(self) -> None:
        if self._text_select_rect_item is not None:
            if self._text_select_rect_item.scene() is not None:
                self.scene_.removeItem(self._text_select_rect_item)
            self._text_select_rect_item = None
        for item in self._text_highlight_items:
            if item.scene() is not None:
                self.scene_.removeItem(item)
        self._text_highlight_items = []
        self._selected_text = ""

    def set_image(self, qimage: QImage) -> None:
        self.scene_.clear()
        self.base_item = None
        self.crop_item = None
        self.page_items = []
        self.page_boundaries = []
        self._text_select_rect_item = None
        self._text_highlight_items = []
        self._selected_text = ""
        self._history = []
        self._future = []
        pixmap = QPixmap.fromImage(qimage)
        self.base_item = QGraphicsPixmapItem(pixmap)
        self.base_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.base_item.setZValue(-1)
        self.scene_.addItem(self.base_item)
        self.scene_.setSceneRect(QRectF(pixmap.rect()))
        self._apply_fit()
        self._push_history()

    def set_pages(self, images: List[QImage], gap: float = 16.0) -> None:
        """PDF continuous scroll: stack every page as its own pixmap item in
        one scene (like a browser), instead of showing one page at a time."""
        self.scene_.clear()
        self.base_item = None
        self.crop_item = None
        self._text_select_rect_item = None
        self._text_highlight_items = []
        self._selected_text = ""
        self._history = []
        self._future = []
        self.page_items = []
        self.page_boundaries = []
        y = 0.0
        max_width = 0.0
        for qimage in images:
            pixmap = QPixmap.fromImage(qimage)
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setZValue(-1)
            item.setPos(0, y)
            self.scene_.addItem(item)
            self.page_items.append(item)
            self.page_boundaries.append((y, float(pixmap.height())))
            max_width = max(max_width, float(pixmap.width()))
            y += pixmap.height() + gap
        self.base_item = self.page_items[0] if self.page_items else None
        self.scene_.setSceneRect(QRectF(0, 0, max_width, max(0.0, y - gap)))
        self._visible_page = 0
        self._apply_fit()
        self._push_history()

    def append_pages(self, images: List[QImage], gap: float = 16.0) -> None:
        """Add more pages below the ones already shown by set_pages, so the
        rest of a document can be rendered in the background after the first
        page is already visible."""
        if not images:
            return
        if self.page_boundaries:
            last_top, last_height = self.page_boundaries[-1]
            y = last_top + last_height + gap
        else:
            y = 0.0
        max_width = self.scene_.sceneRect().width()
        for qimage in images:
            pixmap = QPixmap.fromImage(qimage)
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setZValue(-1)
            item.setPos(0, y)
            self.scene_.addItem(item)
            self.page_items.append(item)
            self.page_boundaries.append((y, float(pixmap.height())))
            max_width = max(max_width, float(pixmap.width()))
            y += pixmap.height() + gap
        if self.base_item is None and self.page_items:
            self.base_item = self.page_items[0]
        self.scene_.setSceneRect(QRectF(0, 0, max_width, max(0.0, y - gap)))

    def scroll_to_page(self, index: int) -> None:
        """Scroll the continuous-scroll scene so page `index` sits at the top
        of the viewport, like jumping to a page in a browser's PDF viewer."""
        if not (0 <= index < len(self.page_boundaries)):
            return
        top, _height = self.page_boundaries[index]
        scale_y = self.transform().m22() or 1.0
        half_viewport = (self.viewport().height() / 2) / scale_y
        scene_x = self.scene_.sceneRect().center().x()
        self.centerOn(scene_x, top + half_viewport)
        self._update_visible_page()

    def _update_visible_page(self) -> None:
        if not self.page_boundaries:
            return
        top_y = self.mapToScene(0, 0).y()
        index = 0
        for i, (top, _height) in enumerate(self.page_boundaries):
            if top <= top_y + 1:
                index = i
            else:
                break
        if index != self._visible_page:
            self._visible_page = index
            self.visible_page_changed.emit(index)

    def add_image_layer(self, qimage: QImage) -> ResizableImageLayerItem:
        """Place another image on the current canvas as a movable layer.

        Layers sit above the base image and below annotations. They are kept as
        real graphics items so their relative positions remain visible and
        editable until the user bakes/saves the composition.
        """
        if self.base_item is None:
            raise RuntimeError("Open a base image before adding image layers.")
        item = ResizableImageLayerItem(QPixmap.fromImage(qimage))
        item.setPos(
            (self.base_item.pixmap().width() - item.pixmap().width()) / 2,
            (self.base_item.pixmap().height() - item.pixmap().height()) / 2,
        )
        self.scene_.addItem(item)
        self._set_image_layer_order(self.image_layers())
        item.setSelected(True)
        return item

    def image_layers(self) -> List[QGraphicsPixmapItem]:
        """Return non-base image layers from back to front."""
        return sorted(
            [item for item in self.scene_.items() if item.data(0) == "image-layer"],
            key=lambda item: item.zValue(),
        )

    def selected_image_layer(self) -> Optional[QGraphicsPixmapItem]:
        return next((item for item in self.scene_.selectedItems() if item.data(0) == "image-layer"), None)

    def bring_selected_image_layer_to_front(self) -> bool:
        item = self.selected_image_layer()
        if item is None:
            return False
        layers = self.image_layers()
        layers.remove(item)
        self._set_image_layer_order([*layers, item])
        return True

    def send_selected_image_layer_to_back(self) -> bool:
        item = self.selected_image_layer()
        if item is None:
            return False
        layers = self.image_layers()
        layers.remove(item)
        self._set_image_layer_order([item, *layers])
        return True

    @staticmethod
    def _set_image_layer_order(layers: List[QGraphicsPixmapItem]) -> None:
        # Annotation items start at z=1.0; reserve the interval below that for
        # image layers while retaining deterministic front/back order.
        for index, item in enumerate(layers):
            item.setZValue(0.1 + index * 0.01)

    def clear_image_layers(self) -> None:
        for item in self.image_layers():
            self.scene_.removeItem(item)

    def load_annotations(self, dicts: List[Dict[str, Any]]) -> None:
        """Replace current annotations and treat this as the new undo
        baseline (so undo won't wipe out marks restored from a previous
        visit to this page/image)."""
        self._rebuild_from_dicts(dicts)
        self._history = [copy.deepcopy(dicts)]
        self._future = []

    def set_tool(self, tool: Tool) -> None:
        self.tool = tool
        select_mode = tool == Tool.SELECT
        for item in self._annotation_items():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, select_mode)

    def _annotation_items(self) -> List[QGraphicsItem]:
        return [
            item for item in self.scene_.items()
            if item is not self.base_item and item not in self.page_items and item.data(0) != "image-layer"
        ]

    def _on_selection_changed(self) -> None:
        items = self.scene_.selectedItems()
        self.selection_changed.emit(items[0] if items else None)

    # ---------- serialization / history ----------

    def get_annotations(self) -> List[Dict[str, Any]]:
        """Current annotation set as plain dicts (type/rect/pos/points/
        color/font_size/width) -- the schema pdf_ops.bake_annotations and
        the image-tab's Pillow baking both expect."""
        return [item.to_dict() for item in self._annotation_items()]

    def _push_history(self) -> None:
        if self._suspend_history:
            return
        self._history.append(copy.deepcopy(self.get_annotations()))
        self._history = self._history[-50:]
        self._future = []
        self.content_changed.emit()

    def commit_change(self) -> None:
        """Called by annotation items after a move/resize/edit finishes."""
        self._push_history()

    def _rebuild_from_dicts(self, dicts: List[Dict[str, Any]]) -> None:
        self._suspend_history = True
        for item in self._annotation_items():
            self.scene_.removeItem(item)
        self.crop_item = None
        for ann in dicts:
            item = self._item_from_dict(ann)
            if item is not None:
                self.scene_.addItem(item)
                if ann["type"] == "crop":
                    self.crop_item = item
        self._suspend_history = False

    def _item_from_dict(self, ann: Dict[str, Any]) -> Optional[QGraphicsItem]:
        atype = ann["type"]
        qcolor = QColor(*ann.get("qcolor", (220, 40, 40, 255)))
        if atype in ("rect", "highlight", "redact", "crop"):
            x, y, w, h = ann["rect"]
            item = ResizableRectItem(QRectF(0, 0, w, h), kind=atype, color=qcolor)
            item.setPos(x, y)
            item.pen_width = ann.get("width", 2)
            item.set_color(qcolor)
            return item
        if atype == "text":
            item = ResizableTextItem(
                ann.get("text", ""),
                font_size=ann.get("font_size", 14),
                color=qcolor,
                font_family=ann.get("font_family", "Helvetica"),
                bold=ann.get("bold", False),
                italic=ann.get("italic", False),
                letter_spacing=ann.get("letter_spacing", 100),
            )
            item.setPos(*ann["pos"])
            return item
        if atype == "freehand":
            pts = ann["points"]
            path = QPainterPath()
            if pts:
                path.moveTo(*pts[0])
                for p in pts[1:]:
                    path.lineTo(*p)
            return ResizablePathItem(path, color=qcolor, width=ann.get("width", 2))
        if atype == "arrow":
            start = QPointF(*ann.get("start", (0, 0)))
            end = QPointF(*ann.get("end", (0, 0)))
            return ResizableArrowItem(start, end, color=qcolor, width=ann.get("width", 3))
        return None

    def undo(self) -> None:
        if len(self._history) < 2:
            return
        current = self._history.pop()
        self._future.append(current)
        self._rebuild_from_dicts(self._history[-1])

    def redo(self) -> None:
        if not self._future:
            return
        dicts = self._future.pop()
        self._history.append(dicts)
        self._rebuild_from_dicts(dicts)

    def clear_annotations(self) -> None:
        for item in self._annotation_items():
            self.scene_.removeItem(item)
        self.crop_item = None
        self._push_history()

    def delete_selected(self) -> None:
        items = self.scene_.selectedItems()
        if not items:
            return
        for item in items:
            self.scene_.removeItem(item)
        self._push_history()

    # ---------- property application (selection, or future-draw default) ----------

    def prompt_and_apply_color(self, parent: Optional[QWidget] = None) -> None:
        """Shared by every tab's toolbar "Color..." button: prompt, then
        apply to the selection (or set the default draw color if none)."""
        color = QColorDialog.getColor(self.current_color, parent, "Choose Color")
        if color.isValid():
            self.apply_color(color)

    def apply_color(self, qcolor: QColor) -> None:
        items = [it for it in self.scene_.selectedItems() if getattr(it, "kind", "") != "redact"]
        if items:
            for item in items:
                item.set_color(qcolor)
            self._push_history()
        else:
            self.current_color = qcolor

    def apply_font_size(self, size: int) -> None:
        items = [it for it in self.scene_.selectedItems() if isinstance(it, ResizableTextItem)]
        if items:
            for item in items:
                item.set_font_size(size)
            self._push_history()
        else:
            self.current_font_size = size

    def apply_font_family(self, family: str) -> None:
        items = [it for it in self.scene_.selectedItems() if isinstance(it, ResizableTextItem)]
        if items:
            for item in items:
                item.set_font_family(family)
            self._push_history()
        else:
            self.current_font_family = family

    def apply_bold(self, bold: bool) -> None:
        items = [it for it in self.scene_.selectedItems() if isinstance(it, ResizableTextItem)]
        if items:
            for item in items:
                item.set_bold(bold)
            self._push_history()
        else:
            self.current_bold = bold

    def apply_italic(self, italic: bool) -> None:
        items = [it for it in self.scene_.selectedItems() if isinstance(it, ResizableTextItem)]
        if items:
            for item in items:
                item.set_italic(italic)
            self._push_history()
        else:
            self.current_italic = italic

    def apply_letter_spacing(self, percent: int) -> None:
        items = [it for it in self.scene_.selectedItems() if isinstance(it, ResizableTextItem)]
        if items:
            for item in items:
                item.set_letter_spacing(percent)
            self._push_history()
        else:
            self.current_letter_spacing = percent

    def current_crop_rect(self) -> Optional[Tuple[float, float, float, float]]:
        """(x, y, w, h) of the crop guide in scene/image coords, or None."""
        if self.crop_item is None or self.crop_item.scene() is None:
            return None
        r = self.crop_item.mapRectToScene(self.crop_item.rect())
        return (r.x(), r.y(), r.width(), r.height())

    # ---------- zoom / pan ----------

    def zoom_in(self) -> None:
        self.scale(1.25, 1.25)

    def zoom_out(self) -> None:
        self.scale(0.8, 0.8)

    def zoom_reset(self) -> None:
        self._apply_fit()

    def _apply_fit(self) -> None:
        if self.base_item is None:
            return
        rect = self.scene_.sceneRect()
        if self.fit_mode == "width" and rect.width() > 0:
            viewport_width = self.viewport().width()
            self.resetTransform()
            self.scale(viewport_width / rect.width(), viewport_width / rect.width())
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        else:
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _start_pan(self, event: Any) -> None:
        self._panning = True
        self._pan_last_pos = event.pos()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def _stop_pan(self) -> None:
        self._panning = False
        self.setCursor(Qt.CursorShape.OpenHandCursor if self._space_held else Qt.CursorShape.ArrowCursor)

    # ---------- mouse handling (creating new shapes only; SELECT tool lets
    # Qt's normal item click/drag/resize machinery run via super()) ----------

    def mousePressEvent(self, event: Any) -> None:
        self.clear_text_selection()

        if self.base_item is None:
            return super().mousePressEvent(event)

        if self._space_held or event.button() == Qt.MouseButton.MiddleButton:
            self._start_pan(event)
            return

        if self.tool == Tool.SELECT:
            # Empty canvas: pans, unless text_provider is set (PDF tab), in
            # which case dragging selects real embedded page text instead.
            clicked = self.itemAt(event.pos())
            if clicked is None or clicked is self.base_item or clicked in self.page_items:
                if self.text_provider is not None:
                    self._text_selecting = True
                    self._text_select_start = self.mapToScene(event.pos())
                    event.accept()
                    return
                self._start_pan(event)
                return
            return super().mousePressEvent(event)

        pos = self.mapToScene(event.pos())
        self._start_pos = pos
        self._drawing = True

        if self.tool == Tool.TEXT:
            text, ok = QInputDialog.getText(self, "Add Text", "Text:")
            if ok and text:
                item = ResizableTextItem(
                    text, pos=pos, font_size=self.current_font_size, color=self.current_color,
                    font_family=self.current_font_family, bold=self.current_bold,
                    italic=self.current_italic, letter_spacing=self.current_letter_spacing,
                )
                self.scene_.addItem(item)
                self._push_history()
            self._drawing = False
            return

        if self.tool == Tool.FREEHAND:
            self._freehand_path = QPainterPath(pos)
            self._temp_item = ResizablePathItem(
                QPainterPath(self._freehand_path), color=self.current_color, width=self.pen_width
            )
            self.scene_.addItem(self._temp_item)
            return

        if self.tool == Tool.ARROW:
            self._temp_item = ResizableArrowItem(
                pos, pos, color=self.current_color, width=max(2, self.pen_width)
            )
            self.scene_.addItem(self._temp_item)
            return

    def _apply_text_provider_result(self, text: str, word_rects: List[QRectF]) -> None:
        for item in self._text_highlight_items:
            if item.scene() is not None:
                self.scene_.removeItem(item)
        self._text_highlight_items = []
        self._selected_text = text
        for word_rect in word_rects:
            highlight = QGraphicsRectItem(word_rect)
            highlight.setBrush(QBrush(QColor(61, 133, 244, 90)))
            highlight.setPen(QPen(Qt.PenStyle.NoPen))
            highlight.setZValue(10)
            self.scene_.addItem(highlight)
            self._text_highlight_items.append(highlight)

    def _update_line_flow_selection(self, end_pos: QPointF) -> None:
        """Live word-processor-style selection: highlights flow through the
        text from the drag start to `end_pos` instead of clipping to a box."""
        if self.text_provider is None:
            return
        text, word_rects = self.text_provider(self._text_select_start, end_pos, False)
        self._apply_text_provider_result(text, word_rects)

    def mouseMoveEvent(self, event: Any) -> None:
        if self._text_selecting:
            pos = self.mapToScene(event.pos())
            if not self.text_select_box_mode:
                self._update_line_flow_selection(pos)
                return
            rect = QRectF(self._text_select_start, pos).normalized()
            if self._text_select_rect_item is None:
                self._text_select_rect_item = QGraphicsRectItem()
                self._text_select_rect_item.setBrush(QBrush(QColor(61, 133, 244, 60)))
                self._text_select_rect_item.setPen(QPen(Qt.PenStyle.NoPen))
                self._text_select_rect_item.setZValue(10)
                self.scene_.addItem(self._text_select_rect_item)
            self._text_select_rect_item.setRect(rect)
            return

        if self._panning:
            delta = event.pos() - self._pan_last_pos
            self._pan_last_pos = event.pos()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            return

        if self.base_item is None or self.tool == Tool.SELECT:
            return super().mouseMoveEvent(event)
        if not self._drawing:
            return

        pos = self.mapToScene(event.pos())

        if self.tool == Tool.FREEHAND and self._temp_item is not None:
            self._freehand_path.lineTo(pos)
            self._temp_item.setPath(QPainterPath(self._freehand_path))
            return

        if self.tool == Tool.ARROW and self._temp_item is not None:
            self._temp_item.end_pos = pos
            self._temp_item._update_arrow_path()
            return

        if self.tool in (Tool.RECT, Tool.HIGHLIGHT, Tool.REDACT, Tool.CROP):
            rect = QRectF(self._start_pos, pos).normalized()
            if self._temp_item is None:
                kind = {
                    Tool.RECT: "rect", Tool.HIGHLIGHT: "highlight",
                    Tool.REDACT: "redact", Tool.CROP: "crop",
                }[self.tool]
                color = self.current_color if kind == "rect" else None
                self._temp_item = ResizableRectItem(
                    QRectF(0, 0, rect.width(), rect.height()), kind=kind, color=color
                )
                self._temp_item.setPos(rect.topLeft())
                self._temp_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                self.scene_.addItem(self._temp_item)
            else:
                self._temp_item.setPos(rect.topLeft())
                self._temp_item.setRect(QRectF(0, 0, rect.width(), rect.height()))

    def mouseReleaseEvent(self, event: Any) -> None:
        if self._text_selecting:
            self._text_selecting = False
            pos = self.mapToScene(event.pos())
            if not self.text_select_box_mode:
                self._update_line_flow_selection(pos)
                return
            rect = self._text_select_rect_item.rect() if self._text_select_rect_item is not None else QRectF()
            if self._text_select_rect_item is not None:
                self.scene_.removeItem(self._text_select_rect_item)
                self._text_select_rect_item = None
            if self.text_provider is not None and rect.width() > 2 and rect.height() > 2:
                text, word_rects = self.text_provider(rect.topLeft(), rect.bottomRight(), True)
                self._apply_text_provider_result(text, word_rects)
            return

        if self._panning:
            self._stop_pan()
            return

        if self.base_item is None or self.tool == Tool.SELECT:
            return super().mouseReleaseEvent(event)
        if not self._drawing:
            return
        self._drawing = False

        if self.tool == Tool.FREEHAND:
            if self._temp_item is not None:
                self._temp_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                self._push_history()
            self._temp_item = None
            self._freehand_path = None
            return

        if self.tool == Tool.ARROW:
            if self._temp_item is not None:
                dx = self._temp_item.end_pos.x() - self._temp_item.start_pos.x()
                dy = self._temp_item.end_pos.y() - self._temp_item.start_pos.y()
                if dx * dx + dy * dy < 16:
                    self.scene_.removeItem(self._temp_item)
                else:
                    self._temp_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                    self._push_history()
            self._temp_item = None
            return

        if self._temp_item is not None:
            if self._temp_item.rect().width() < 4 or self._temp_item.rect().height() < 4:
                self.scene_.removeItem(self._temp_item)
            else:
                self._temp_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                if self.tool == Tool.CROP:
                    if self.crop_item is not None and self.crop_item.scene() is not None:
                        self.scene_.removeItem(self.crop_item)
                    self.crop_item = self._temp_item
                self._push_history()
                if self.tool == Tool.CROP:
                    self.crop_drawn.emit(self.current_crop_rect())
            self._temp_item = None

    def clear_crop_guide(self) -> None:
        if self.crop_item is not None and self.crop_item.scene() is not None:
            self.scene_.removeItem(self.crop_item)
        self.crop_item = None

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path and os.path.exists(path):
                    self.file_dropped.emit(path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        if event.matches(QKeySequence.StandardKey.Copy) and self._selected_text:
            QGuiApplication.clipboard().setText(self._selected_text)
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_Tab:
            self._cycle_selection(1 if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier else -1)
            return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
            dx = -step if event.key() == Qt.Key.Key_Left else step if event.key() == Qt.Key.Key_Right else 0.0
            dy = -step if event.key() == Qt.Key.Key_Up else step if event.key() == Qt.Key.Key_Down else 0.0
            if self._nudge_selected(dx, dy):
                return
        super().keyPressEvent(event)

    def _cycle_selection(self, direction: int) -> None:
        items = self._annotation_items()
        if not items:
            return
        selected = self.scene_.selectedItems()
        current_index = items.index(selected[0]) if selected and selected[0] in items else -1
        next_index = (current_index + direction) % len(items)
        self.scene_.clearSelection()
        items[next_index].setSelected(True)

    def _nudge_selected(self, dx: float, dy: float) -> bool:
        items = self.scene_.selectedItems()
        if not items:
            return False
        for item in items:
            item.moveBy(dx, dy)
        self._nudging = True
        return True

    def keyReleaseEvent(self, event: Any) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self.unsetCursor()
            return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and not event.isAutoRepeat() and self._nudging:
            self._nudging = False
            self._push_history()
            return
        super().keyReleaseEvent(event)

    def wheelEvent(self, event: Any) -> None:  # noqa: 21 (Qt virtual override, invoked by the framework)
        # Plain wheel scrolls like a normal document view; only Ctrl+wheel
        # zooms (AnchorUnderMouse in __init__ makes that zoom toward the cursor).
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def viewportEvent(self, event: Any) -> bool:
        # Trackpad pinch-to-zoom on macOS and Windows precision touchpads
        # arrives as a native gesture rather than a wheel event.
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                factor = 1.0 + event.value()
                if factor > 0:
                    self.scale(factor, factor)
                return True
        return super().viewportEvent(event)
