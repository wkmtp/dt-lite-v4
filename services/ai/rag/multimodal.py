"""Multimodal document processing using unstructured for PDF/Word/Excel/image/video subtitles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel


@dataclass
class ProcessedElement:
    """A single element extracted from a multimodal document."""
    text: str
    element_type: str  # "Title", "NarrativeText", "ListItem", "Image", "Table", etc.
    metadata: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class MultimodalConfig(BaseModel):
    """Configuration for multimodal document processing."""
    use_unstructured: bool = True
    api_url: str = "https://api.unstructured.io/general/v0/general"
    api_key: str = ""
    strategy: str = "auto"  # auto, hi_res, fast, ocr_only
    languages: list[str] = ["eng", "chi"]


class MultimodalProcessor:
    """
    Processes PDF, Word, Excel, images, and video subtitles using the
    `unstructured` library.
    """

    def __init__(self, config: Optional[MultimodalConfig] = None) -> None:
        self._config = config or MultimodalConfig()

    async def process(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> list[ProcessedElement]:
        """
        Parse a multimodal document and return extracted elements.
        """
        if self._config.use_unstructured:
            return await self._process_with_unstructured(content, filename, content_type)
        # Fallback to simple text extraction
        return [ProcessedElement(text=content.decode("utf-8", errors="replace"), element_type="Text")]

    async def _process_with_unstructured(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> list[ProcessedElement]:
        """
        Use unstructured's partition functions for different file types.
        """
        import io
        from unstructured.partition.auto import partition

        file_obj = io.BytesIO(content)
        try:
            elements = partition(file=file_obj, filename=filename, content_type=content_type)
        except Exception:
            # Fallback: try with strategy
            elements = partition(file=file_obj, filename=filename, strategy=self._config.strategy)

        result = []
        for elem in elements:
            result.append(ProcessedElement(
                text=elem.text if hasattr(elem, "text") else str(elem),
                element_type=elem.category if hasattr(elem, "category") else type(elem).__name__,
                metadata=getattr(elem, "metadata", {}) or {},
            ))
        return result

    def extract_text(self, elements: list[ProcessedElement]) -> str:
        """Join all element texts with newlines."""
        return "\n\n".join(e.text for e in elements if e.text.strip())
