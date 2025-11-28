-- Providers Table Schema
-- Stores information about service providers

CREATE TABLE IF NOT EXISTS providers (
    -- Primary identification
    provider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic information
    name TEXT NOT NULL,
    country VARCHAR(2) NOT NULL,
    location TEXT,
    
    -- Tier and status
    tier VARCHAR(20),
    
    -- Capabilities and focus
    services TEXT[], -- Array of services offered
    references TEXT[], -- Array of client references
    
    -- Contact and web presence
    website TEXT,
    
    -- Data quality and provenance
    source_url TEXT NOT NULL,
    date_collected TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_quality_score DECIMAL(3,2) CHECK (data_quality_score BETWEEN 0.0 AND 1.0),
    data_completeness_score DECIMAL(3,2) CHECK (data_completeness_score BETWEEN 0.0 AND 1.0),
    quality_flags JSONB DEFAULT '{}'::jsonb, -- Store specific quality issues
    
    -- Indexing for performance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_providers_country ON providers(country);
CREATE INDEX idx_providers_tier ON providers(tier);
CREATE INDEX idx_providers_quality ON providers(data_quality_score DESC);

-- Full-text search on names
CREATE INDEX idx_providers_name_fts ON providers USING gin(to_tsvector('english', name));

COMMENT ON TABLE providers IS 'Service providers directory';
