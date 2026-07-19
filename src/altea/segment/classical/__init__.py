"""Classical, unsupervised segmentation backends."""
from .threshold import OtsuThreshold, WatershedSplit

__all__ = ["OtsuThreshold", "WatershedSplit"]
