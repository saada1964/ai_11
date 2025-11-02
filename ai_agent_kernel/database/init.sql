-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create LLM Models table
CREATE TABLE llm_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(100) NOT NULL,
    api_endpoint TEXT,
    api_standard VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'groq', etc.
    price_per_million_tokens DECIMAL(10, 6) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'planner', 'summarizer', 'direct_answer'
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3, 2) DEFAULT 0.7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Tools table
CREATE TABLE tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    function_name VARCHAR(255) NOT NULL,
    price_usd DECIMAL(10, 6) DEFAULT 0.0,
    api_key_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    parameters JSONB, -- Tool parameters schema
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    balance BIGINT DEFAULT 100000, -- Balance in units (not cents)
    is_active BOOLEAN DEFAULT true,
    memory_profile JSONB DEFAULT '{}', -- User's long-term memory
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'New Conversation',
    summary TEXT, -- Medium-term conversation summary
    total_messages INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Files table for RAG
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    file_type VARCHAR(50), -- 'pdf', 'docx', 'txt', 'md'
    processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    vector_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create File Chunks table for vector storage
CREATE TABLE file_chunks (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimensions
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Usage Logs table for accounting
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- 'llm_call', 'tool_usage', 'streaming'
    model_name VARCHAR(255),
    tool_name VARCHAR(255),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Credit Codes table
CREATE TABLE credit_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credit_amount INTEGER NOT NULL,
    discount_percentage DECIMAL(5, 2) DEFAULT 0.0,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_credit_codes_code ON credit_codes(code);
CREATE INDEX idx_credit_codes_is_active ON credit_codes(is_active);


-- Create Credit Transactions table
CREATE TABLE credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credit_code_id INTEGER REFERENCES credit_codes(id) ON DELETE SET NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    amount_usd DECIMAL(10, 2) DEFAULT 0.0,
    payment_method VARCHAR(50),
    payment_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    meta_data JSONB DEFAULT '{}',
    processed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX idx_credit_transactions_status ON credit_transactions(status);


-- Create Payment Methods table
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    min_amount_usd DECIMAL(10, 2) DEFAULT 1.0,
    max_amount_usd DECIMAL(10, 2) DEFAULT 1000.0,
    supported_currencies JSONB DEFAULT '["USD"]',
    fees_percentage DECIMAL(5, 2) DEFAULT 0.0,
    fixed_fee_usd DECIMAL(10, 2) DEFAULT 0.0,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_payment_methods_provider ON payment_methods(provider);
CREATE INDEX idx_payment_methods_is_active ON payment_methods(is_active);


-- Create Payment Records table
CREATE TABLE payment_records (
    id SERIAL PRIMARY KEY,
    credit_transaction_id INTEGER NOT NULL REFERENCES credit_transactions(id) ON DELETE CASCADE,
    payment_method_id INTEGER NOT NULL REFERENCES payment_methods(id) ON DELETE CASCADE,
    external_payment_id VARCHAR(255),
    payment_intent_id VARCHAR(255),
    session_id VARCHAR(255),
    amount_usd DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',
    gateway_response JSONB DEFAULT '{}',
    webhook_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_payment_records_transaction_id ON payment_records(credit_transaction_id);
CREATE INDEX idx_payment_records_external_id ON payment_records(external_payment_id);
CREATE INDEX idx_payment_records_status ON payment_records(status);


-- Create Subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(100) NOT NULL,
    monthly_credits INTEGER NOT NULL,
    monthly_price_usd DECIMAL(10, 2) NOT NULL,
    payment_method_id INTEGER REFERENCES payment_methods(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'active',
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    next_billing_date TIMESTAMP WITH TIME ZONE,
    auto_renewal BOOLEAN DEFAULT true,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_billing ON subscriptions(next_billing_date);
-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_processing_status ON files(processing_status);
CREATE INDEX idx_file_chunks_file_id ON file_chunks(file_id);
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);

-- Create vector index for semantic search
CREATE INDEX idx_file_chunks_embedding ON file_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert default LLM models
INSERT INTO llm_models (name, provider, api_endpoint, api_standard, price_per_million_tokens, role, max_tokens, temperature) VALUES
('llama-3.1-8b-instant', 'Groq', 'https://api.groq.com/openai/v1/chat/completions', 'openai', 0.06, 'planner', 4000, 0.3),
('llama-3.1-70b-versatile', 'Groq', 'https://api.groq.com/openai/v1/chat/completions', 'openai', 0.59, 'planner', 8000, 0.3),
('gpt-3.5-turbo', 'OpenAI', 'https://api.openai.com/v1/chat/completions', 'openai', 1.50, 'summarizer', 4000, 0.5),
('gpt-4-turbo', 'OpenAI', 'https://api.openai.com/v1/chat/completions', 'openai', 10.00, 'direct_answer', 8000, 0.7),
('claude-3-haiku-20240307', 'Anthropic', 'https://api.anthropic.com/v1/messages', 'anthropic', 0.25, 'planner', 4000, 0.3);

-- Insert default tools
INSERT INTO tools (name, description, function_name, price_usd, api_key_name) VALUES
('web_search_serper', 'Perform fast web search using Serper.dev API', 'web_search_serper', 0.001, 'SERPER_API_KEY'),
('wikipedia_search', 'Search Wikipedia articles with smart language detection', 'wikipedia_search', 0.0001, NULL),
('advanced_calculator', 'Safe mathematical expression evaluator using numexpr', 'advanced_calculator', 0.00001, NULL),
('search_user_documents', 'Search through user uploaded documents using RAG', 'search_user_documents', 0.001, NULL);

-- Create a default admin user
INSERT INTO users (username, email, hashed_password, balance) VALUES
('admin', 'admin@aiagent.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldQKzEBmnuQ9kG', 1000000); -- password: admin123


