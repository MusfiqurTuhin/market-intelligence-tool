import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import re
import os
import argparse

# --- CONFIGURATION ---
# Define your service categories and associated keywords here.
# This dictionary is used to classify gigs into specific service offerings relevant to your business.
# Customize these keys and values to match your specific domain (e.g., "Web Development", "SEO", "Graphic Design").
SERVICE_KEYWORDS = {
    'Implementation': ['implementation', 'setup', 'install', 'deploy', 'configure'],
    'Customization': ['customization', 'customize', 'custom', 'module', 'develop'],
    'Integration': ['integration', 'integrate', 'api', 'payment', 'gateway'],
    'Migration': ['migration', 'migrate', 'upgrade', 'data'],
    'Support & Training': ['support', 'training', 'consultant', 'consulting', 'help', 'fix', 'bug'],
    'Web & E-commerce': ['website', 'ecommerce', 'store', 'shop', 'design', 'theme']
}
# ---------------------

def clean_price(price_str):
    if pd.isna(price_str):
        return 0
    # Remove "From ", "$", "," and extra spaces
    clean = re.sub(r'[^\d]', '', str(price_str))
    try:
        return float(clean)
    except ValueError:
        return 0

def analyze_market(input_csv, output_excel):
    print(f"Loading data from {input_csv}...")
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: {input_csv} not found.")
        return

    # 1. Data Cleaning
    print("Cleaning data...")
    if 'price' in df.columns:
        df['price_numeric'] = df['price'].apply(clean_price)
    else:
        print("Warning: 'price' column not found. Skipping price cleaning.")
        df['price_numeric'] = 0
        
    df['title_clean'] = df['title'].fillna('').str.lower().str.replace(r'[^\w\s]', '', regex=True)

    # 2. ML Clustering (K-Means)
    print("Running ML clustering...")
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    X = vectorizer.fit_transform(df['title_clean'])

    num_clusters = 8
    # Ensure we don't have more clusters than samples
    if X.shape[0] < num_clusters:
        num_clusters = max(1, X.shape[0] // 2)
        
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X)

    # Identify Cluster Names
    print("Identifying cluster themes...")
    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
    terms = vectorizer.get_feature_names_out()
    
    cluster_names = {}
    for i in range(num_clusters):
        top_terms = [terms[ind] for ind in order_centroids[i, :3]]
        cluster_names[i] = ", ".join(top_terms).title()
        print(f"Cluster {i}: {cluster_names[i]}")

    df['Category'] = df['cluster'].map(cluster_names)

    # 3. Strategic Analysis (Service Matching)
    print("Performing strategic analysis...")
    
    def classify_service(title):
        title = str(title).lower()
        found_services = []
        for service, keywords in SERVICE_KEYWORDS.items():
            if any(k in title for k in keywords):
                found_services.append(service)
        return ", ".join(found_services) if found_services else "Other"

    df['Service_Match'] = df['title'].apply(classify_service)

    # 4. Generate Excel Dashboard
    print(f"Generating {output_excel}...")
    
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        # --- Sheet 1: Executive Summary ---
        summary_data = {
            'Metric': ['Total Gigs Analyzed', 'Average Market Price', 'Median Market Price', 'Total Market Value (Est.)', 'Highest Price Gig'],
            'Value': [len(df), df['price_numeric'].mean(), df['price_numeric'].median(), df['price_numeric'].sum(), df['price_numeric'].max()]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # --- Sheet 2: Category Analysis (ML Clusters) ---
        category_stats = df.groupby('Category')['price_numeric'].agg(['count', 'mean', 'min', 'max', 'sum']).sort_values('sum', ascending=False)
        category_stats.columns = ['Gig Count', 'Avg Price ($)', 'Min Price ($)', 'Max Price ($)', 'Total Value ($)']
        category_stats.to_excel(writer, sheet_name='Category Analysis')

        # --- Sheet 3: Service Gap Analysis ---
        service_stats = df.groupby('Service_Match')['price_numeric'].agg(['count', 'mean', 'max']).sort_values('mean', ascending=False)
        service_stats.columns = ['Gig Count', 'Avg Price ($)', 'Max Price ($)']
        service_stats.to_excel(writer, sheet_name='Service Gaps')

        # --- Sheet 4: Raw Data ---
        cols_to_save = ['title', 'seller_name', 'price', 'price_numeric', 'Category', 'Service_Match', 'link']
        # Only save columns that exist
        cols_to_save = [c for c in cols_to_save if c in df.columns]
        df[cols_to_save].to_excel(writer, sheet_name='Raw Data', index=False)

        # Formatting (Auto-adjust column widths)
        workbook = writer.book
        money_fmt = workbook.add_format({'num_format': '$#,##0'})
        
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column('A:Z', 20) # Default width
            
            if sheet_name == 'Category Analysis':
                 worksheet.set_column('B:E', 15, money_fmt)
            if sheet_name == 'Service Gaps':
                 worksheet.set_column('B:C', 15, money_fmt)

    print("Analysis complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Fiverr market data.")
    parser.add_argument("--input", type=str, default="fiverr_gigs.csv", help="Input CSV file path (default: fiverr_gigs.csv)")
    parser.add_argument("--output", type=str, default="fiverr_market_intelligence.xlsx", help="Output Excel file path (default: fiverr_market_intelligence.xlsx)")
    
    args = parser.parse_args()
    
    analyze_market(args.input, args.output)
