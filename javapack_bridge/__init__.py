"""JavaPack Bridge: convert Minecraft Java Edition resource packs to Bedrock."""
from .convert import convert_pack, ConversionReport

__all__ = ["convert_pack", "ConversionReport"]
__version__ = "0.1.0"
