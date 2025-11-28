# Generic Market Intelligence Scraper

A comprehensive, configurable web scraping framework designed to collect, clean, and analyze data from various service provider directories.

## 🎯 Objective

Systematically identify, score, and target high-potential service providers by collecting and analyzing data from public sources.

## 📊 Features

- **Configurable Scraping**: Easily adapt to different websites via JSON configuration.
- **Data Cleaning**: Automated normalization and deduplication.
- **Quality Scoring**: Data completeness and validity checks.
- **Export**: Data export to JSON and CSV formats.

## 🏗️ Project Structure

```
.
├── config/                      # Configuration files
│   ├── data_dictionary.json    # Standardized taxonomies
│   └── scraper_config.json     # Target website configurations
├── schema/                      # Database schemas
│   └── schema_providers.sql
├── scrapers/                    # Scraping logic
│   ├── base_scraper.py         # Base class
│   └── generic_scraper.py      # Config-driven scraper
├── processors/                  # Data processing
│   ├── data_cleaner.py
│   └── quality_scorer.py
├── data/                        # Data storage
│   ├── raw/
│   └── cleaned/
└── tests/
```

## 🚀 Quick Start

### 1. Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration

Edit `config/scraper_config.json` to define your target websites and selectors.

### 3. Run Scraper

```bash
python scrapers/generic_scraper.py
```

## 📝 Data Schema

The system extracts standard fields:
- **Provider Name**
- **Location** (City, Country)
- **Services/Capabilities**
- **References/Clients**

## 📜 Ethical Web Scraping

- ✅ Respects `robots.txt`
- ✅ Implements rate limiting
- ✅ Collects only public data

## 📄 License

MIT License
