-- Ragent Python MVP 建表（PostgreSQL + pgvector）。维度 1024(bge-m3)。
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_base (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  embedding_model VARCHAR(128) DEFAULT '',
  collection_name VARCHAR(128) NOT NULL,
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_collection ON knowledge_base(collection_name);

CREATE TABLE IF NOT EXISTS knowledge_document (
  id VARCHAR(64) PRIMARY KEY,
  kb_id VARCHAR(64) NOT NULL,
  doc_name VARCHAR(512) NOT NULL,
  source_type VARCHAR(32) DEFAULT 'file',
  source_location TEXT DEFAULT '',
  chunk_strategy VARCHAR(32) DEFAULT 'fixed_size',
  chunk_config JSONB DEFAULT '{}'::jsonb,
  status VARCHAR(32) DEFAULT 'pending',
  file_url TEXT DEFAULT '',
  file_type VARCHAR(64) DEFAULT '',
  file_size BIGINT DEFAULT 0,
  chunk_count INT DEFAULT 0,
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doc_kb ON knowledge_document(kb_id);

CREATE TABLE IF NOT EXISTS knowledge_chunk (
  id VARCHAR(64) PRIMARY KEY,
  kb_id VARCHAR(64) NOT NULL,
  doc_id VARCHAR(64) NOT NULL,
  chunk_index INT DEFAULT 0,
  content TEXT NOT NULL,
  content_hash VARCHAR(64),
  char_count INT DEFAULT 0,
  token_count INT DEFAULT 0,
  enabled BOOLEAN DEFAULT TRUE,
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunk_doc ON knowledge_chunk(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunk_hash ON knowledge_chunk(content_hash);

-- 向量 + 全文(BM25)。content_tsv 由应用写入(jieba 分词后的 'simple' tsvector)。
CREATE TABLE IF NOT EXISTS knowledge_vector (
  id VARCHAR(64) PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(1024),
  metadata JSONB DEFAULT '{}'::jsonb,
  content_tsv tsvector
);
CREATE INDEX IF NOT EXISTS idx_vec_hnsw ON knowledge_vector USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_vec_meta ON knowledge_vector USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_vec_tsv ON knowledge_vector USING gin (content_tsv);

CREATE TABLE IF NOT EXISTS conversation (
  id VARCHAR(64) PRIMARY KEY,
  conversation_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(64) DEFAULT '',
  title VARCHAR(512) DEFAULT '',
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conv_cid ON conversation(conversation_id);

CREATE TABLE IF NOT EXISTS message (
  id VARCHAR(64) PRIMARY KEY,
  conversation_id VARCHAR(64) NOT NULL,
  role VARCHAR(16) NOT NULL,
  content TEXT NOT NULL,
  thinking_content TEXT DEFAULT '',
  thinking_duration INT DEFAULT 0,
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON message(conversation_id);

-- P4 记忆摘要：长对话压缩水位线
CREATE TABLE IF NOT EXISTS conversation_summary (
  id VARCHAR(64) PRIMARY KEY,
  conversation_id VARCHAR(64) NOT NULL,
  content TEXT DEFAULT '',
  last_message_id VARCHAR(64) DEFAULT '',
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_summary_conv ON conversation_summary(conversation_id);

-- P5 意图树：DOMAIN(0)/CATEGORY(1)/TOPIC(2 叶子打分)；kind 0=KB 1=SYSTEM 2=MCP
CREATE TABLE IF NOT EXISTS intent_node (
  id VARCHAR(64) PRIMARY KEY,
  kb_id VARCHAR(64) DEFAULT '',
  intent_code VARCHAR(128) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT DEFAULT '',
  examples TEXT DEFAULT '',
  level INT DEFAULT 2,
  parent_code VARCHAR(128) DEFAULT '',
  kind INT DEFAULT 0,
  collection_name VARCHAR(128) DEFAULT '',
  mcp_tool_id VARCHAR(128) DEFAULT '',
  topk INT DEFAULT 10,
  prompt_template TEXT DEFAULT '',
  enabled BOOLEAN DEFAULT TRUE,
  deleted BOOLEAN DEFAULT FALSE,
  create_time TIMESTAMPTZ DEFAULT now(),
  update_time TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intent_level ON intent_node(level);
