"""ORM 模型（MVP 子集；完整 22 表后续补）。"""

from __future__ import annotations

import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db import Base


class TimestampMixin:
    create_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    update_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class KnowledgeBase(TimestampMixin, Base):
    __tablename__ = "knowledge_base"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    embedding_model: Mapped[str] = mapped_column(String(128), default="")
    collection_name: Mapped[str] = mapped_column(String(128), index=True)


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_document"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kb_id: Mapped[str] = mapped_column(String(64), index=True)
    doc_name: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32), default="file")
    source_location: Mapped[str] = mapped_column(Text, default="")
    chunk_strategy: Mapped[str] = mapped_column(String(32), default="fixed_size")
    chunk_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    file_url: Mapped[str] = mapped_column(Text, default="")
    file_type: Mapped[str] = mapped_column(String(64), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeChunk(TimestampMixin, Base):
    __tablename__ = "knowledge_chunk"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kb_id: Mapped[str] = mapped_column(String(64), index=True)
    doc_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeVector(Base):
    """向量 + 全文（BM25）。embedding 走 pgvector；content_tsv 走 tsvector(在 DB 侧/应用侧维护)。"""

    __tablename__ = "knowledge_vector"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)  # collection_name/doc_id/chunk_index


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversation"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    title: Mapped[str] = mapped_column(String(512), default="")


class Message(TimestampMixin, Base):
    __tablename__ = "message"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    thinking_content: Mapped[str] = mapped_column(Text, default="")
    thinking_duration: Mapped[int] = mapped_column(Integer, default=0)


class ConversationSummary(TimestampMixin, Base):
    __tablename__ = "conversation_summary"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    last_message_id: Mapped[str] = mapped_column(String(64), default="")


class IntentNode(TimestampMixin, Base):
    __tablename__ = "intent_node"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kb_id: Mapped[str] = mapped_column(String(64), default="")
    intent_code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    examples: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[int] = mapped_column(Integer, default=2)
    parent_code: Mapped[str] = mapped_column(String(128), default="")
    kind: Mapped[int] = mapped_column(Integer, default=0)  # 0 KB / 1 SYSTEM / 2 MCP
    collection_name: Mapped[str] = mapped_column(String(128), default="")
    mcp_tool_id: Mapped[str] = mapped_column(String(128), default="")
    topk: Mapped[int] = mapped_column(Integer, default=10)
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
