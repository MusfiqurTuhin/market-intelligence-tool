"""
Process USA Scraper JSON into Grand CSV format.
"""
import json
import csv
import sys
import os

def process_usa_data(input_file='data/raw/usa_partners_detailed.json', output_file='data/cleaned/usa_grand_client_dataset.csv'):
    print(f"Processing {input_file}...")
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
            # Handle BaseScraper output structure
            if isinstance(data, dict) and 'partners' in data:
                partners = data['partners']
            else:
                partners = data
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        return

    all_records = []
    
    for partner in partners:
        partner_name = partner.get('company_name', 'Unknown')
        partner_tier = partner.get('tier', 'Unknown')
        partner_website = partner.get('website', '')
        partner_city = partner.get('city', '')
        partner_id = partner.get('partner_id', '')
        
        # Check for detailed references
        detailed_refs = partner.get('client_references_detailed', [])
        
        if detailed_refs:
            for ref in detailed_refs:
                # Extract fields
                client_name = ref.get('client_name', 'Unknown')
                desc = ref.get('description', '')
                modules = ', '.join(ref.get('modules_implemented', []))
                outcomes = ref.get('outcomes', '')
                
                # Infer Industry if not present (simple keyword matching)
                industry = 'General'
                desc_lower = desc.lower()
                if 'manufacturing' in desc_lower: industry = 'Manufacturing'
                elif 'retail' in desc_lower: industry = 'Retail'
                elif 'health' in desc_lower: industry = 'Healthcare'
                elif 'finance' in desc_lower: industry = 'Finance'
                elif 'education' in desc_lower: industry = 'Education'
                elif 'service' in desc_lower: industry = 'Services'
                
                # New Metrics
                avg_project = partner.get('average_project_size', 'N/A')
                large_project = partner.get('large_project_size', 'N/A')
                experts = partner.get('certified_experts', 'N/A')
                certs = partner.get('certifications', {})
                
                # Format certifications (e.g., "v18: 5, v17: 3")
                cert_str = ', '.join([f"{k}: {v}" for k, v in certs.items()])

                all_records.append({
                    'Partner Name': partner_name,
                    'Partner Tier': partner_tier,
                    'Client Name': client_name,
                    'Client Industry': industry,
                    'Modules Implemented': modules,
                    'Key Outcomes': outcomes,
                    'Project Description': desc,
                    'Partner Website': partner_website,
                    'Partner City': partner_city,
                    'Partner ID': partner_id,
                    'Avg Project Size': avg_project,
                    'Large Project Size': large_project,
                    'Certified Experts': experts,
                    'Total References Listed': partner.get('reference_count_listed', 'N/A'),
                    'Certifications': cert_str
                })
        else:
            # Add entry for partner even if no references
            # New Metrics
            avg_project = partner.get('average_project_size', 'N/A')
            large_project = partner.get('large_project_size', 'N/A')
            experts = partner.get('certified_experts', 'N/A')
            certs = partner.get('certifications', {})
            cert_str = ', '.join([f"{k}: {v}" for k, v in certs.items()])

            all_records.append({
                'Partner Name': partner_name,
                'Partner Tier': partner_tier,
                'Client Name': 'N/A', # Explicitly mark as N/A
                'Client Industry': 'N/A',
                'Modules Implemented': '',
                'Key Outcomes': '',
                'Project Description': '',
                'Partner Website': partner_website,
                'Partner City': partner_city,
                'Partner ID': partner_id,
                'Avg Project Size': avg_project,
                'Large Project Size': large_project,
                'Certified Experts': experts,
                'Total References Listed': partner.get('reference_count_listed', 'N/A'),
                'Certifications': cert_str
            })

    # Deduplicate based on Partner ID and Client Name
    unique_records = {}
    for record in all_records:
        # Create a unique key
        key = (record['Partner ID'], record['Client Name'])
        # Overwrite if exists (taking the latest version effectively, or just the last one processed)
        unique_records[key] = record
    
    final_records = list(unique_records.values())

    # Sort
    tier_order = {'Gold': 0, 'Silver': 1, 'Ready': 2}
    final_records.sort(key=lambda x: (tier_order.get(x['Partner Tier'], 3), x['Partner Name'], x['Client Name']))

    # Save
    fieldnames = [
        'Partner Name', 'Partner Tier', 'Client Name', 'Client Industry', 
        'Modules Implemented', 'Key Outcomes', 'Project Description', 
        'Partner Website', 'Partner City', 'Partner ID',
        'Avg Project Size', 'Large Project Size', 'Certified Experts', 'Total References Listed', 'Certifications'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_records)
        
    print(f"✅ Processed {len(final_records)} unique client references.")
    print(f"📁 Saved to {output_file}")

    print(f"✅ Created USA Grand Dataset with {len(all_records)} records")
    print(f"📁 Saved to: {output_file}")

if __name__ == '__main__':
    import glob
    
    # Pattern to match all partial files (including those with timestamps)
    partial_pattern = 'data/raw/usa_partners_page_*_partial.json*'
    partials = glob.glob(partial_pattern)
    
    if partials:
        print(f"Found {len(partials)} partial data files. Aggregating...")
        
        all_partners_data = []
        for file_path in partials:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'partners' in data:
                        all_partners_data.extend(data['partners'])
                    elif isinstance(data, list):
                        all_partners_data.extend(data)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
        # Save combined temporary file to pass to processing function
        combined_file = 'data/raw/usa_partners_combined_temp.json'
        with open(combined_file, 'w') as f:
            json.dump(all_partners_data, f)
            
        process_usa_data(input_file=combined_file)
        
        # Clean up temp file
        if os.path.exists(combined_file):
            os.remove(combined_file)
            
    elif os.path.exists('data/raw/usa_partners_detailed.json'):
        process_usa_data()
    else:
        print("No data files found.")
