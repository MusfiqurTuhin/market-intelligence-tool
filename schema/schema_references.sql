-- References Table Schema
-- Stores information about client implementations and projects

CREATE TABLE IF NOT EXISTS references (
    -- Primary identification
    reference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES providers(provider_id) ON DELETE CASCADE,
    
    -- Basic information
    client_name TEXT NOT NULL,
    country VARCHAR(2) NOT NULL,
    industry TEXT NOT NULL,
    
    -- Project scope and scale
    project_size_users INTEGER, -- Number of users/licenses
    is_large_project BOOLEAN DEFAULT FALSE,
    
    -- Implementation details
    services_implemented JSONB DEFAULT '[]'::jsonb, -- Array of services used
    implementation_timeline_months INTEGER,
    
    -- Outcomes and impact
    roi_estimate TEXT, -- Free text
    impact_metrics JSONB DEFAULT '{}'::jsonb, -- Structured metrics
    project_status VARCHAR(20),
    
    -- References
    case_study_url TEXT,
    reference_notes TEXT,
    testimonial TEXT,
    
    -- Data quality and provenance
    source_url TEXT NOT NULL,
    date_collected TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_quality_flag VARCHAR(20) DEFAULT 'medium',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_references_provider ON references(provider_id);
CREATE INDEX idx_references_country ON references(country);
CREATE INDEX idx_references_industry ON references(industry);
CREATE INDEX idx_references_services ON references USING GIN (services_implemented);

COMMENT ON TABLE references IS 'Client implementations and project references for providers';
