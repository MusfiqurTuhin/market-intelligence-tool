"""
Simplified data cleaner without pandas dependency.
Uses only Python stdlib for JSON/CSV processing.
"""

import json
import re
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataCleaner:
    """Utilities for cleaning and normalizing scraped provider data."""
    
    def __init__(self, data_dict_path: str = "config/data_dictionary.json"):
        """
        Initialize data cleaner with data dictionary.
        
        Args:
            data_dict_path: Path to data dictionary JSON file
        """
        with open(data_dict_path, 'r') as f:
            self.data_dict = json.load(f)
        
        self.country_map = self.data_dict['countries']
        self.industry_map = self.data_dict['industries']['normalization_map']
        self.module_aliases = self.data_dict['service_modules']['module_aliases']
    
    def clean_providers(self, providers: List[Dict]) -> List[Dict]:
        """
        Clean and normalize a list of provider records.
        
        Args:
            providers: List of raw provider dictionaries
            
        Returns:
            List of cleaned provider dictionaries
        """
        cleaned = []
        
        for provider in providers:
            cleaned_provider = self._clean_provider(provider)
            if cleaned_provider:
                cleaned.append(cleaned_provider)
        
        return cleaned
    
    def _clean_provider(self, provider: Dict) -> Optional[Dict]:
        """Clean a single provider record."""
        try:
            cleaned = {
                'provider_id': provider.get('provider_id', ''),
                'name': self._clean_company_name(provider.get('name', '')),
                'country': self._normalize_country(provider.get('country', '')),
                'location': self._clean_text(provider.get('location')),
                'tier': self._normalize_tier(provider.get('tier', '')),
                'website': self._clean_url(provider.get('website')),
                'description': self._clean_text(provider.get('description', '')),
                'services': provider.get('services', []),
                'references': provider.get('references', []),
                'source_url': provider.get('source_url', ''),
            }
            
            return cleaned
            
        except Exception as e:
            print(f"Error cleaning provider {provider.get('name', 'unknown')}: {e}")
            return None
    
    def _clean_company_name(self, name: str) -> str:
        """Clean and standardize company name."""
        if not name:
            return ""
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove tier badges if present
        name = re.sub(r'\s*(Gold|Silver|Ready)\s*$', '', name, flags=re.I)
        
        return name.strip()
    
    def _normalize_country(self, country: str) -> str:
        """Normalize country names to 2-letter codes."""
        if not country:
            return ""
        
        # If already 2-letter code
        if len(country) == 2:
            return country.upper()
        
        # Map full names to codes
        country_lower = country.lower()
        for code, info in self.country_map.items():
            if country_lower in [info['name'].lower(), info['full_name'].lower()]:
                return code
        
        return country
    
    def _normalize_tier(self, tier: str) -> str:
        """Normalize partner tier."""
        if not tier:
            return "Unknown"
        
        tier = tier.strip().capitalize()
        
        if tier in ['Gold', 'Silver', 'Ready']:
            return tier
        
        return "Unknown"
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean text fields."""
        if not text:
            return None
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters that might cause issues
        text = text.replace('\x00', '').replace('\r', ' ')
        
        return text.strip() if text.strip() else None
    
    def _clean_url(self, url: Optional[str]) -> Optional[str]:
        """Validate and clean URLs."""
        if not url:
            return None
        
        url = url.strip()
        
        # Basic URL validation
        if not re.match(r'^https?://', url):
            return None
        
        return url
    
    def _normalize_industries(self, industries: List[str]) -> List[str]:
        """Normalize industry names using data dictionary."""
        if not industries:
            return []
        
        normalized = set()
        
        for industry in industries:
            industry = industry.strip()
            
            # Check if it's in the normalization map
            if industry in self.industry_map:
                normalized.add(self.industry_map[industry])
            else:
                # Check if it's already in the standard taxonomy
                for standard_name in self.data_dict['industries']['standardized_taxonomy']:
                    if industry.lower() == standard_name.lower():
                        normalized.add(standard_name)
                        break
                else:
                    # Keep original if no match found
                    normalized.add(industry)
        
        return sorted(list(normalized))
    
    def _normalize_modules(self, modules: List[str]) -> List[str]:
        """Normalize service module names."""
        if not modules:
            return []
        
        normalized = set()
        
        for module in modules:
            module = module.strip()
            
            # Check aliases
            if module in self.module_aliases:
                normalized.add(self.module_aliases[module])
            else:
                # Check core modules (case-insensitive)
                for core_module in self.data_dict['service_modules']['core_modules']:
                    if module.lower() == core_module.lower():
                        normalized.add(core_module)
                        break
                else:
                    # Keep original
                    normalized.add(module)
        
        return sorted(list(normalized))
    
    def deduplicate_providers(self, providers: List[Dict], threshold: float = 0.85) -> List[Dict]:
        """
        Deduplicate providers using simple string similarity.
        
        Args:
            providers: List of provider dictionaries
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            List of unique providers
        """
        if not providers:
            return []
        
        unique_providers = []
        seen_names = []
        
        for provider in providers:
            name = provider.get('name', '').lower()
            
            # Check against seen names using simple character overlap
            is_duplicate = False
            for seen_name in seen_names:
                similarity = self._simple_similarity(name, seen_name)
                if similarity >= threshold:
                    is_duplicate = True
                    print(f"Duplicate detected: '{name}' matches '{seen_name}' ({similarity:.1%} similar)")
                    break
            
            if not is_duplicate:
                unique_providers.append(provider)
                seen_names.append(name)
        
        print(f"Deduplication: {len(providers)} -> {len(unique_providers)} providers")
        
        return unique_providers
    
    def _simple_similarity(self, str1: str, str2: str) -> float:
        """Simple character-based similarity (Jaccard similarity on character bigrams)."""
        if not str1 or not str2:
            return 0.0
        
        if str1 == str2:
            return 1.0
        
        # Create character bigrams
        bigrams1 = set(str1[i:i+2] for i in range(len(str1)-1))
        bigrams2 = set(str2[i:i+2] for i in range(len(str2)-1))
        
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def to_csv(self, providers: List[Dict], output_file: str) -> None:
        """
        Export providers to CSV file.
        
        Args:
            providers: List of provider dictionaries
            output_file: Path to output CSV file
        """
        if not providers:
            print("No providers to export")
            return
        
        # Flatten nested structures
        flattened = []
        for provider in providers:
            flat = provider.copy()
            
            # Convert lists to semicolon-separated strings
            if 'services' in flat and isinstance(flat['services'], list):
                flat['services'] = '; '.join(flat['services'])
            
            if 'references' in flat and isinstance(flat['references'], list):
                flat['references'] = '; '.join(flat['references'])
            
            flattened.append(flat)
        
        # Write CSV
        if flattened:
            fieldnames = flattened[0].keys()
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened)
            
            print(f"Exported {len(flattened)} partners to {output_file}")


def main():
    """Test data cleaning functionality."""
    import glob
    from datetime import datetime
    
    # Find latest raw data
    raw_files = glob.glob('data/raw/*_partners_*.json')
    if not raw_files:
        print("No raw data files found. Run scraper first.")
        return
    
    latest_file = max(raw_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"Cleaning data from: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    cleaner = DataCleaner()
    
    # Clean providers
    cleaned_providers = cleaner.clean_providers(data['providers'])
    print(f"Cleaned {len(cleaned_providers)} providers")
    
    # Deduplicate
    unique_providers = cleaner.deduplicate_providers(cleaned_providers)
    
    # Save cleaned data
    cleaned_dir = Path('data/cleaned')
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    input_path = Path(latest_file)
    base_name = input_path.stem
    
    # Save JSON
    json_file = cleaned_dir / f"{base_name}_cleaned.json"
    with open(json_file, 'w') as f:
        json.dump({
            'metadata': {
                **data.get('metadata', {}),
                'cleaned_at': datetime.now().isoformat(),
                'original_count': len(data['providers']),
                'cleaned_count': len(cleaned_providers),
                'unique_count': len(unique_providers)
            },
            'providers': unique_providers
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Saved cleaned JSON: {json_file}")
    
    # Save CSV
    csv_file = cleaned_dir / f"{base_name}_cleaned.csv"
    cleaner.to_csv(unique_providers, str(csv_file))


if __name__ == '__main__':
    main()
