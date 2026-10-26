from app.web.api.base import BaseApi
from app.web.api.tool_archive import ArchiveApiMixin
from app.web.api.tool_collage import CollageApiMixin
from app.web.api.tool_converter import ConverterApiMixin
from app.web.api.tool_data import DataApiMixin
from app.web.api.tool_encoding import EncodingApiMixin
from app.web.api.tool_hash import HashApiMixin
from app.web.api.tool_images import ImagesApiMixin
from app.web.api.tool_markdown import MarkdownApiMixin
from app.web.api.tool_media import MediaApiMixin
from app.web.api.tool_metadata import MetadataApiMixin
from app.web.api.tool_model3d import Model3dApiMixin
from app.web.api.tool_network_monitor import NetworkMonitorApiMixin
from app.web.api.tool_ocr import OcrApiMixin
from app.web.api.tool_office import OfficeApiMixin
from app.web.api.tool_palette import PaletteApiMixin
from app.web.api.tool_pdf import PdfApiMixin
from app.web.api.tool_playlist import PlaylistApiMixin
from app.web.api.tool_qr import QrApiMixin
from app.web.api.tool_renamer import RenamerApiMixin
from app.web.api.tool_resume import ResumeApiMixin
from app.web.api.tool_screenshot import ScreenshotApiMixin
from app.web.api.tool_text_tools import TextToolsApiMixin
from app.web.api.tool_word_counter import WordCounterApiMixin


class WebApi(
    BaseApi,
    ArchiveApiMixin,
    CollageApiMixin,
    ConverterApiMixin,
    DataApiMixin,
    EncodingApiMixin,
    HashApiMixin,
    ImagesApiMixin,
    MarkdownApiMixin,
    MediaApiMixin,
    MetadataApiMixin,
    Model3dApiMixin,
    NetworkMonitorApiMixin,
    OcrApiMixin,
    OfficeApiMixin,
    PaletteApiMixin,
    PdfApiMixin,
    PlaylistApiMixin,
    QrApiMixin,
    RenamerApiMixin,
    ResumeApiMixin,
    ScreenshotApiMixin,
    TextToolsApiMixin,
    WordCounterApiMixin,
):
    pass


__all__ = ["WebApi"]
