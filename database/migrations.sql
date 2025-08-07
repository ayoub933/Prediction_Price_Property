CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    address TEXT,
    price DECIMAL(12,2),
    surface DECIMAL(8,2),
    rooms INTEGER,
    property_type VARCHAR(50), -- maison, appartement
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    description TEXT,
    features TEXT[], -- [parking, balcon, cave]
    source VARCHAR(50), -- leboncoin, seloger, pap
    url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des prédictions ML
CREATE TABLE IF NOT EXISTS price_predictions (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    predicted_price DECIMAL(12,2),
    confidence_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des tendances marché
CREATE TABLE IF NOT EXISTS market_trends (
    id SERIAL PRIMARY KEY,
    area VARCHAR(100),
    avg_price_sqm DECIMAL(10,2),
    evolution_percentage DECIMAL(5,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les recherches
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_area ON properties(address);
CREATE INDEX IF NOT EXISTS idx_properties_scraped ON properties(scraped_at);