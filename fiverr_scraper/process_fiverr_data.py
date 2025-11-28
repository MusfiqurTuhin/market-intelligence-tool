import json
import csv
import glob
import os
import re
import argparse

def process_fiverr_data(keyword="fiverr", input_pattern="fiverr_page_*.json"):
    # Construct output filename based on keyword
    output_file = f"{keyword}_gigs.csv"
    
    # Find JSON files
    json_files = glob.glob(input_pattern)
    all_gigs = []

    print(f"Looking for files matching: {input_pattern}")
    print(f"Found {len(json_files)} JSON files: {json_files}")

    for file in json_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_gigs.extend(data)
                    print(f"Loaded {len(data)} gigs from {file}")
                else:
                    print(f"Warning: {file} does not contain a list of gigs.")
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not all_gigs:
        print("No data found.")
        return

    # Get all keys from the first gig to define headers
    headers = list(all_gigs[0].keys())
    if 'price_numeric' not in headers:
        headers.append('price_numeric')

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for gig in all_gigs:
            # Extract numeric price
            price_str = gig.get('price', '')
            price_numeric = ''
            if price_str:
                # Remove non-numeric characters except for the first number found
                match = re.search(r'(\d+)', str(price_str))
                if match:
                    price_numeric = match.group(1)
            
            gig['price_numeric'] = price_numeric
            writer.writerow(gig)

    print(f"Saved {len(all_gigs)} gigs to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Fiverr JSON data into CSV.")
    parser.add_argument("--keyword", type=str, default="fiverr", help="Keyword used for filename prefix (default: fiverr)")
    parser.add_argument("--pattern", type=str, default="fiverr_page_*.json", help="Glob pattern for input JSON files (default: fiverr_page_*.json)")
    
    args = parser.parse_args()
    
    process_fiverr_data(keyword=args.keyword, input_pattern=args.pattern)
