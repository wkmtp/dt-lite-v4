"""Document chunker with token, sentence, and semantic strategies."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from pydantic import BaseModel


@dataclass
class Chunk:
    """A single text chunk with its position metadata."""
    text: str
    start_offset: int
    end_offset: int
    chunk_index: int
    source_doc_id: str


class ChunkStrategy(str, Enum):
    """Supported chunking strategies."""
    TOKEN = "token"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"


class ChunkConfig(BaseModel):
    """Configuration for chunking."""
    strategy: ChunkStrategy = ChunkStrategy.TOKEN
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 50
    separators: list[str] = ["\n\n", "\n", "。", ".", "!", "?", " "]


class DocumentChunker:
    """
    Splits raw text into chunks using the selected strategy.
    """

    def __init__(self, config: Optional[ChunkConfig] = None) -> None:
        self._config = config or ChunkConfig()

    def chunk(
        self,
        text: str,
        *,
        doc_id: str,
        metadata: Optional[dict] = None,
    ) -> list[Chunk]:
        """Return a list of Chunk objects for *text*."""
        metadata = metadata or {}
        if self._config.strategy == ChunkStrategy.TOKEN:
            return self._chunk_by_token(text, doc_id, metadata)
        if self._config.strategy == ChunkStrategy.SENTENCE:
            return self._chunk_by_sentence(text, doc_id, metadata)
        if self._config.strategy == ChunkStrategy.SEMANTIC:
            return self._chunk_by_semantic(text, doc_id, metadata)
        raise ValueError(f"Unknown strategy: {self._config.strategy}")

    def _chunk_by_token(self, text: str, doc_id: str, metadata: dict) -> list[Chunk]:
        """Naive token-based chunking using character boundaries."""
        chars = list(text)
        chunks: list[Chunk] = []
        start = 0
        idx = 0
        while start < len(chars):
            end = min(start + self._config.chunk_size, len(chars))
            # Try to break at a separator near the chunk boundary
            best_break = end
            for sep in self._config.separators:
                pos = text.rfind(sep, start, end + len(sep) + 10)
                if pos > start and pos < best_break:
                    best_break = pos + len(sep)
            actual_end = min(best_break, len(chars))
            chunk_text = text[start:actual_end]
            if len(chunk_text.strip()) >= self._config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    start_offset=start,
                    end_offset=actual_end,
                    chunk_index=len(chunks),
                    source_doc_id=doc_id,
                ))
            start = actual_end - self._config.chunk_overlap if actual_end > start else actual_end + 1
            idx += 1
        return chunks

    def _chunk_by_sentence(self, text: str, doc_id: str, metadata: dict) -> list[Chunk]:
        """Sentence-level chunking that accumulates sentences into chunks."""
        sentences = re.split(r'(?<=[。.!?])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        chunks: list[Chunk] = []
        current: list[str] = []
        current_len = 0
        for i, sent in enumerate(sentences):
            sent_len = len(sent)
            if current_len + sent_len > self._config.chunk_size and current:
                chunks.append(Chunk(
                    text=" ".join(current),
                    start_offset=text.find(current[0]),
                    end_offset=text.find(current[-1]) + len(current[-1]),
                    chunk_index=len(chunks),
                    source_doc_id=doc_id,
                ))
                current = [sent]
                current_len = sent_len
            else:
                current.append(sent)
                current_len += sent_len
        if current:
            chunks.append(Chunk(
                text=" ".join(current),
                start_offset=text.find(current[0]),
                end_offset=text.find(current[-1]) + len(current[-1]),
                chunk_index=len(chunks),
                source_doc_id=doc_id,
            ))
        return chunks

    def _chunk_by_semantic(self, text: str, doc_id: str, metadata: dict) -> list[Chunk]:
        """
        Semantic chunking: splits on paragraph boundaries and groups by content.
        Falls back to token chunking for very short texts.
        """
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        if len(paragraphs) <= 1:
            return self._chunk_by_token(text, doc_id, metadata)
        chunks: list[Chunk] = []
        current: list[str] = []
        current_len = 0
        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > self._config.chunk_size and current:
                chunks.append(Chunk(
                    text="\n\n".join(current),
                    start_offset=text.find(current[0]),
                    end_offset=text.find(current[-1]) + len(current[-1]),
                    chunk_index=len(chunks),
                    source_doc_id=doc_id,
                ))
                current = [para]
                current_len = para_len
            else:
                current.append(para)
                current_len += para_len
        if current:
            chunks.append(Chunk(
                text="\n\n".join(current),
                start_offset=text.find(current[0]),
                end_offset=text.find(current[-1]) + len(current[-1]),
                chunk_index=len(chunks),
                source_doc_id=doc_id,
            ))
        return chunks
