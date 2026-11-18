"""Intake: EXIF, orientation, segment, rectify, scale → intake.v2."""

from furniture_cad.intake.pipeline import intake_photo, segment_mask, try_rectify
from furniture_cad.intake.rectify import rectify_image
from furniture_cad.intake.segment import segment_subject

__all__ = ["intake_photo", "segment_mask", "segment_subject", "try_rectify", "rectify_image"]
