# Fiverr Keyword Search & Gig Scraper

This tool allows you to scrape gig data from Fiverr based on a specific keyword search, process the data into a CSV, and perform a market analysis using Machine Learning to identify trends, pricing strategies, and service gaps.

## 📂 Contents

*   `process_fiverr_data.py`: Aggregates scraped JSON data into a CSV file.
*   `analyze_fiverr_market.py`: Analyzes the CSV data using ML clustering and generates an Excel dashboard.
*   `fiverr_gigs.csv`: Sample dataset (aggregated from scraped pages).
*   `fiverr_market_intelligence.xlsx`: Sample analysis report.

## 🚀 Usage

### 1. Prerequisites

Ensure you have Python installed and the required dependencies:

```bash
pip install pandas scikit-learn xlsxwriter openpyxl
```

### 2. Scraping Data (Manual/Browser)

Currently, the scraping is performed using a browser automation tool (like the one used to generate the JSON files in this repo). Save your scraped data as `fiverr_page_1.json`, `fiverr_page_2.json`, etc.

### 3. Processing Data

Combine the JSON files into a single CSV:

```bash
python process_fiverr_data.py --keyword your_keyword --pattern "fiverr_page_*.json"
```

*   `--keyword`: The prefix for your output CSV (e.g., `odoo` -> `odoo_gigs.csv`). Default is `fiverr`.
*   `--pattern`: The glob pattern to match your JSON files.

### 4. Analyzing Market Data

Run the analysis script to generate an Excel dashboard:

```bash
python analyze_fiverr_market.py --input your_keyword_gigs.csv --output market_report.xlsx
```

*   `--input`: Path to your processed CSV file.
*   `--output`: Desired filename for the Excel report.

**Customization:**
You can customize the `SERVICE_KEYWORDS` dictionary in `analyze_fiverr_market.py` to match the specific services or categories you are interested in for your domain.

## 📊 Output

The analysis script generates an Excel file with:
*   **Executive Summary**: Key market metrics.
*   **Category Analysis**: ML-generated clusters of gigs.
*   **Service Gaps**: Analysis based on your defined keywords.
*   **Raw Data**: The full dataset with classification tags.
