"""
Simplified pipeline script without pandas dependency.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Import our modules
from scrapers.main_scraper_bangladesh import BangladeshScraper
from processors.data_cleaner import DataCleaner
from processors.quality_scorer import QualityScorer


def setup_logging():
    """Set up logging configuration."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'pipeline.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('Pipeline')


def run_scraper(country: str, logger: logging.Logger) -> str:
    """Run the scraper for the specified country."""
    logger.info(f"Starting scraper for {country}")
    
    if country.lower() == 'bangladesh':
        scraper = BangladeshScraper()
        output_file = scraper.run()
        logger.info(f"Scraping completed: {output_file}")
        return output_file
    else:
        logger.error(f"Scraper for {country} not implemented yet")
        raise NotImplementedError(f"Scraper for {country} not available")


def clean_data(input_file: str, logger: logging.Logger) -> tuple:
    """Clean and normalize scraped data."""
    logger.info(f"Cleaning data from {input_file}")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    cleaner = DataCleaner()
    cleaned_partners = cleaner.clean_partners(data['partners'])
    logger.info(f"Cleaned {len(cleaned_partners)} partners")
    
    unique_partners = cleaner.deduplicate_partners(cleaned_partners)
    logger.info(f"After deduplication: {len(unique_partners)} unique partners")
    
    cleaned_dir = Path('data/cleaned')
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    input_path = Path(input_file)
    base_name = input_path.stem
    
    # Save JSON
    json_file = cleaned_dir / f"{base_name}_cleaned.json"
    with open(json_file, 'w') as f:
        json.dump({
            'metadata': {
                **data.get('metadata', {}),
                'cleaned_at': datetime.now().isoformat(),
                'original_count': len(data['partners']),
                'cleaned_count': len(cleaned_partners),
                'unique_count': len(unique_partners)
            },
            'partners': unique_partners
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved cleaned JSON: {json_file}")
    
    # Save CSV
    csv_file = cleaned_dir / f"{base_name}_cleaned.csv"
    cleaner.to_csv(unique_partners, str(csv_file))
    
    return str(json_file), str(csv_file)


def score_quality(input_file: str, logger: logging.Logger) -> str:
    """Calculate quality scores and generate report."""
    logger.info(f"Scoring quality for {input_file}")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Handle empty datasets
    if not data.get('partners'):
        logger.warning("No partners found in dataset")
        report_file = Path(input_file).parent / 'quality_report.json'
        with open(report_file, 'w') as f:
            json.dump({
                'error': 'No partners in dataset',
                'generated_at': datetime.now().isoformat()
            }, f, indent=2)
        print("\n⚠️  No partners found in dataset")
        return str(report_file)
    
    scorer = QualityScorer()
    scored_partners = [scorer.score_partner(p.copy()) for p in data['partners']]
    report = scorer.generate_quality_report(data['partners'])
    
    # Update data with scores
    output_file = Path(input_file)
    with open(output_file, 'w') as f:
        json.dump({
            **data,
            'partners': scored_partners
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Updated {output_file} with quality scores")
    
    # Save report
    report_file = output_file.parent / 'quality_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("QUALITY REPORT SUMMARY")
    print("=" * 60)
    print(f"Total Partners: {report.get('total_partners', 0)}")
    print(f"Average Completeness: {report.get('average_completeness', 0):.1%}")
    print(f"Average Quality: {report.get('average_quality', 0):.1%}")
    print("\nTop Quality Issues:")
    for flag, count in list(report.get('common_quality_issues', {}).items())[:5]:
        pct = count / report.get('total_partners', 1) * 100
        print(f"  - {flag}: {count} ({pct:.1f}%)")
    print("=" * 60 + "\n")
    
    return str(report_file)


def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(description='Odoo Market Intelligence Data Pipeline')
    parser.add_argument(
        '--country',
        type=str,
        choices=['bangladesh', 'india', 'usa'],
        default='bangladesh',
        help='Country to scrape (default: bangladesh)'
    )
    parser.add_argument(
        '--scrape-only',
        action='store_true',
        help='Only run scraper'
    )
    
    args = parser.parse_args()
    logger = setup_logging()
    logger.info("Starting Odoo Market Intelligence Pipeline")
    
    try:
        if args.scrape_only:
            raw_file = run_scraper(args.country, logger)
            print(f"\n✅ Scraping completed!")
            print(f"📁 Raw data: {raw_file}")
            return
        
        # Full pipeline
        print("\n" + "=" * 60)
        print("STEP 1/3: SCRAPING")
        print("=" * 60)
        raw_file = run_scraper(args.country, logger)
        print(f"✅ Scraped data saved: {raw_file}")
        
        print("\n" + "=" * 60)
        print("STEP 2/3: CLEANING & NORMALIZATION")
        print("=" * 60)
        json_file, csv_file = clean_data(raw_file, logger)
        print(f"✅ Cleaned data: {json_file}")
        print(f"✅ CSV export: {csv_file}")
        
        print("\n" + "=" * 60)
        print("STEP 3/3: QUALITY SCORING")
        print("=" * 60)
        report_file = score_quality(json_file, logger)
        
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📁 Outputs:")
        print(f"   - JSON: {json_file}")
        print(f"   - CSV: {csv_file}")
        print(f"   - Quality Report: {report_file}")
        print("=" * 60 + "\n")
    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
