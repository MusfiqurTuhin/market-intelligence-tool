"""
Simplified quality scorer without pandas dependency.
"""

import json
import re
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse


class QualityScorer:
    """Calculate data quality scores for partner records."""
    
    def __init__(self, data_dict_path: str = "config/data_dictionary.json"):
        """
        Initialize quality scorer.
        """
        with open(data_dict_path, 'r') as f:
            self.data_dict = json.load(f)
        
        self.validation_patterns = self.data_dict['data_quality_rules']['validation_patterns']
        self.mandatory_fields = self.data_dict['data_quality_rules']['mandatory_fields']['providers']
        self.completeness_weights = self.data_dict['data_quality_rules']['completeness_weights']['providers']
    
    def score_provider(self, provider: Dict) -> Dict:
        """
        Calculate quality scores for a provider record.
        """
        # Calculate completeness score
        completeness_score = self._calculate_completeness(provider)
        
        # Calculate data quality score
        quality_score = self._calculate_quality(provider)
        
        # Identify quality issues
        quality_flags = self._identify_quality_flags(provider)
        
        # Add scores to provider record
        provider['data_completeness_score'] = round(completeness_score, 2)
        provider['data_quality_score'] = round(quality_score, 2)
        provider['quality_flags'] = quality_flags
        
        return provider
    
    def _calculate_completeness(self, provider: Dict) -> float:
        """Calculate completeness score based on field presence."""
        total_weight = 0.0
        achieved_weight = 0.0
        
        for field, weight in self.completeness_weights.items():
            total_weight += weight
            
            value = provider.get(field)
            
            if value is not None:
                if isinstance(value, str) and value.strip():
                    achieved_weight += weight
                elif isinstance(value, list) and len(value) > 0:
                    list_score = min(len(value) / 3.0, 1.0)
                    achieved_weight += (weight * list_score)
                elif isinstance(value, (int, float)) and value > 0:
                    achieved_weight += weight
        
        return achieved_weight / total_weight if total_weight > 0 else 0.0
    
    def _calculate_quality(self, provider: Dict) -> float:
        """Calculate overall quality score."""
        quality_checks = []
        
        # Check 1: Mandatory fields
        mandatory_present = all(
            provider.get(field) is not None and provider.get(field) != ''
            for field in self.mandatory_fields
        )
        quality_checks.append(1.0 if mandatory_present else 0.0)
        
        # Check 2: URL validity
        url_valid = self._validate_url(provider.get('website'))
        source_valid = self._validate_url(provider.get('source_url'))
        quality_checks.append((url_valid + source_valid) / 2.0)
        
        # Check 3: Country code valid
        country_valid = bool(re.match(
            self.validation_patterns['country_code'],
            provider.get('country', '')
        ))
        quality_checks.append(1.0 if country_valid else 0.5)
        
        # Check 4: Tier valid
        tier_valid = bool(re.match(
            self.validation_patterns.get('tier', '.*'),
            provider.get('tier', 'Unknown')
        ))
        quality_checks.append(1.0 if tier_valid else 0.3)
        
        # Check 5: Description quality
        description = provider.get('description', '')
        desc_quality = min(len(description) / 200.0, 1.0) if description else 0.0
        quality_checks.append(desc_quality)
        
        return sum(quality_checks) / len(quality_checks)
    
    def _validate_url(self, url: str) -> float:
        """Validate URL format."""
        if not url:
            return 0.5
        
        try:
            result = urlparse(url)
            is_valid = all([result.scheme, result.netloc])
            return 1.0 if is_valid else 0.0
        except:
            return 0.0
    
    def _identify_quality_flags(self, provider: Dict) -> Dict[str, bool]:
        """Identify specific quality issues."""
        flags = {}
        
        for field in self.mandatory_fields:
            if not provider.get(field):
                flags[f'missing_{field}'] = True
        
        if not provider.get('website'):
            flags['no_website'] = True
        
        desc = provider.get('description')
        if not desc or len(desc) < 50:
            flags['short_description'] = True
        
        return flags
    
    def generate_quality_report(self, providers: List[Dict]) -> Dict:
        """Generate overall quality report."""
        if not providers:
            return {'error': 'No providers provided'}
        
        # Score all providers
        scored_providers = [self.score_provider(p.copy()) for p in providers]
        
        # Calculate statistics
        completeness_scores = [p['data_completeness_score'] for p in scored_providers]
        quality_scores = [p['data_quality_score'] for p in scored_providers]
        
        # Count flags
        flag_counts = {}
        for provider in scored_providers:
            for flag in provider.get('quality_flags', {}).keys():
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        report = {
            'total_providers': len(providers),
            'average_completeness': round(sum(completeness_scores) / len(completeness_scores), 3),
            'average_quality': round(sum(quality_scores) / len(quality_scores), 3),
            'completeness_distribution': {
                'high (>0.8)': sum(1 for s in completeness_scores if s > 0.8),
                'medium (0.5-0.8)': sum(1 for s in completeness_scores if 0.5 <= s <= 0.8),
                'low (<0.5)': sum(1 for s in completeness_scores if s < 0.5),
            },
            'quality_distribution': {
                'high (>0.8)': sum(1 for s in quality_scores if s > 0.8),
                'medium (0.5-0.8)': sum(1 for s in quality_scores if 0.5 <= s <= 0.8),
                'low (<0.5)': sum(1 for s in quality_scores if s < 0.5),
            },
            'common_quality_issues': {
                flag: count for flag, count in sorted(
                    flag_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return report


def main():
    """Generate quality report."""
    import glob
    from pathlib import Path
    
    cleaned_files = glob.glob('data/cleaned/*_partners_*.json')
    if not cleaned_files:
        print("No cleaned data files found")
        return
    
    latest_file = max(cleaned_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"Analyzing quality for: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    scorer = QualityScorer()
    report = scorer.generate_quality_report(data['providers'])
    
    # Save report
    report_file = Path(latest_file).parent / 'quality_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n===== QUALITY REPORT =====")
    print(f"Total Providers: {report['total_providers']}")
    print(f"Average Completeness: {report['average_completeness']:.1%}")
    print(f"Average Quality: {report['average_quality']:.1%}")
    print("\nCommon Issues:")
    for flag, count in list(report['common_quality_issues'].items())[:5]:
        print(f"  - {flag}: {count} providers ({count/report['total_providers']:.1%})")
    print(f"\nFull report saved to: {report_file}")


if __name__ == '__main__':
    main()
