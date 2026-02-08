"""
動画マニュアル作成ユーティリティパッケージ

このパッケージは動画マニュアル作成ツールのためのユーティリティ機能を提供します。
"""

from .coord_utils import (
    pixel_to_relative,
    relative_to_pixel,
    rect_to_relative,
    rect_to_pixel,
    arrow_to_relative,
    arrow_to_pixel,
    validate_rel_coords,
    VALID_ANNOTATION_TYPES,
)

from .video_processor import VideoProcessor

from .temp_manager import TempFileManager

from .doc_generator import (
    DocGenerator,
    create_word_manual,
    create_word_manual_from_paths,
)

from .text_parser import (
    ValidationResult,
    parse_json,
    validate_gemini_json,
    validate_saved_json,
    validate_all_timestamps,
    parse_and_validate,
)

__all__ = [
    # coord_utils
    'pixel_to_relative',
    'relative_to_pixel',
    'rect_to_relative',
    'rect_to_pixel',
    'arrow_to_relative',
    'arrow_to_pixel',
    'validate_rel_coords',
    'VALID_ANNOTATION_TYPES',
    # video_processor
    'VideoProcessor',
    # temp_manager
    'TempFileManager',
    # doc_generator
    'DocGenerator',
    'create_word_manual',
    'create_word_manual_from_paths',
    # text_parser
    'ValidationResult',
    'parse_json',
    'validate_gemini_json',
    'validate_saved_json',
    'validate_all_timestamps',
    'parse_and_validate',
]
