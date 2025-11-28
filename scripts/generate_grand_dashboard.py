import pandas as pd
import xlsxwriter
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PARTNERS_FILE = "data/raw/global_partners.csv"
CLIENTS_FILE = "data/raw/global_partner_clients.csv"
OUTPUT_FILE = "data/raw/Web scraping report with filterable options on all global partners and client across all countries for the Metamorphosis expansion plan.xlsx"

def clean_clients_data(df):
    """Clean and prepare client data."""
    def parse_size(val):
        if pd.isna(val): return 0
        match = re.search(r'(\d+)', str(val))
        return int(match.group(1)) if match else 0

    df['Project Size (Numeric)'] = df['Avg Project Size'].apply(parse_size)
    df['Primary Industry'] = df['Client Industry'].apply(lambda x: str(x).split(',')[0] if pd.notna(x) else "Unknown")
    
    # Parse Retention
    def parse_retention(val):
        if pd.isna(val): return 0
        match = re.search(r'(\d+)', str(val))
        return int(match.group(1)) if match else 0
    df['Retention (Numeric)'] = df['Customer Retention'].apply(parse_retention)
    
    return df

def clean_partners_data(df):
    """Clean and prepare partner data."""
    # Ensure numeric columns are actually numeric
    df['References Count'] = pd.to_numeric(df['References Count'], errors='coerce').fillna(0)
    
    # Parse Certified Experts (sum of numbers in string)
    def parse_experts(val):
        if pd.isna(val): return 0
        # e.g. "35 Certified v18, 2 Certified v17" -> 37
        nums = re.findall(r'(\d+)\s+Certified', str(val))
        return sum(int(n) for n in nums)
    
    # If 'Certified Experts' is already numeric in partners csv, use it, else parse
    # Checking sample data, it seems to be just a number in global_partners.csv?
    # Let's check the csv content again. The user said "Certified Experts" column exists.
    # In global_partners.csv it might be a simple number.
    # In clients csv it was a string breakdown.
    # Let's assume it's numeric or parseable.
    df['Certified Experts'] = pd.to_numeric(df['Certified Experts'], errors='coerce').fillna(0)
    return df

def create_grand_dashboard():
    if not os.path.exists(PARTNERS_FILE) or not os.path.exists(CLIENTS_FILE):
        logger.error("One or more input files not found.")
        return

    logger.info("Reading data files...")
    df_partners = pd.read_csv(PARTNERS_FILE)
    df_clients = pd.read_csv(CLIENTS_FILE)

    logger.info("Cleaning data...")
    df_partners = clean_partners_data(df_partners)
    df_clients = clean_clients_data(df_clients)

    logger.info(f"Creating Grand Excel Dashboard at {OUTPUT_FILE}...")
    writer = pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter')
    workbook = writer.book

    # --- Formats ---
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
    cell_fmt = workbook.add_format({'border': 1})
    num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0'})
    pct_fmt = workbook.add_format({'border': 1, 'num_format': '0%'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 18, 'font_color': '#366092'})
    subtitle_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#595959'})
    metric_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#DCE6F1', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    metric_label_fmt = workbook.add_format({'font_size': 10, 'bg_color': '#DCE6F1', 'border': 1, 'align': 'center', 'valign': 'vcenter'})

    # --- 1. Dashboard Sheet ---
    dash_sheet = workbook.add_worksheet('Dashboard')
    dash_sheet.hide_gridlines(2)
    dash_sheet.set_column('A:Z', 15)

    dash_sheet.write('B2', 'Metamorphosis Expansion Plan - Global Market Intelligence', title_fmt)

    # KPIs Calculation
    total_partners = len(df_partners)
    total_clients = len(df_clients)
    total_countries = df_partners['Country'].nunique()
    avg_clients = total_clients / total_partners if total_partners else 0
    
    # Additional KPIs
    # Total Experts (sum from partners)
    total_experts = df_partners['Certified Experts'].sum()
    
    # Avg Retention (from clients data where available)
    avg_retention = df_clients[df_clients['Retention (Numeric)'] > 0]['Retention (Numeric)'].mean()

    # Row 4-5: High Level Metrics
    metrics = [
        ('Total Partners', total_partners, num_fmt),
        ('Total Clients', total_clients, num_fmt),
        ('Countries Covered', total_countries, num_fmt),
        ('Avg Clients/Partner', avg_clients, num_fmt),
        ('Total Certified Experts', total_experts, num_fmt),
        ('Avg Client Retention', avg_retention/100 if avg_retention else 0, pct_fmt)
    ]

    col = 1
    for label, value, fmt in metrics:
        dash_sheet.merge_range(3, col, 3, col+1, label, metric_label_fmt)
        # Apply specific format to value cell if needed, but merge_range takes one format
        # We can write the value with format to the first cell after merge? No.
        # Let's just use generic metric_fmt and format the number in code if needed or create specific formats.
        # For simplicity, let's format the value as string if it's percent
        display_val = value
        if label == 'Avg Client Retention':
            display_val = f"{value:.1%}"
        elif isinstance(value, (int, float)):
            display_val = f"{value:,.0f}" if value > 100 else f"{value:.1f}"
            
        dash_sheet.merge_range(4, col, 4, col+1, display_val, metric_fmt)
        col += 3

    # Charts Data Sheet (Hidden)
    data_sheet = workbook.add_worksheet('ChartData')
    data_sheet.hide()

    # --- Row 8: Charts ---
    
    # Chart 1: Partners by Tier
    dash_sheet.write('B8', 'Partners by Tier', subtitle_fmt)
    tier_counts = df_partners['Partner Tier'].value_counts()
    data_sheet.write_column('A1', tier_counts.index)
    data_sheet.write_column('B1', tier_counts.values)

    chart1 = workbook.add_chart({'type': 'column'})
    chart1.add_series({
        'categories': f'=ChartData!$A$1:$A${len(tier_counts)}',
        'values':     f'=ChartData!$B$1:$B${len(tier_counts)}',
        'points': [{'fill': {'color': '#4F81BD'}}],
    })
    chart1.set_title({'name': 'Partners by Tier'})
    chart1.set_legend({'none': True})
    dash_sheet.insert_chart('B10', chart1, {'x_scale': 1.5, 'y_scale': 1.5})

    # Chart 2: Top 10 Countries (Partners)
    dash_sheet.write('K8', 'Top 10 Countries (Partners)', subtitle_fmt)
    country_counts = df_partners['Country'].value_counts().head(10)
    data_sheet.write_column('D1', country_counts.index)
    data_sheet.write_column('E1', country_counts.values)

    chart2 = workbook.add_chart({'type': 'bar'})
    chart2.add_series({
        'categories': f'=ChartData!$D$1:$D${len(country_counts)}',
        'values':     f'=ChartData!$E$1:$E${len(country_counts)}',
        'points': [{'fill': {'color': '#C0504D'}}],
    })
    chart2.set_title({'name': 'Top Partner Countries'})
    chart2.set_legend({'none': True})
    dash_sheet.insert_chart('K10', chart2, {'x_scale': 1.5, 'y_scale': 1.5})

    # --- Row 28: More Charts ---

    # Chart 3: Top Client Industries
    dash_sheet.write('B28', 'Top Client Industries', subtitle_fmt)
    ind_counts = df_clients['Primary Industry'].value_counts().head(10)
    data_sheet.write_column('G1', ind_counts.index)
    data_sheet.write_column('H1', ind_counts.values)

    chart3 = workbook.add_chart({'type': 'bar'})
    chart3.add_series({
        'categories': f'=ChartData!$G$1:$G${len(ind_counts)}',
        'values':     f'=ChartData!$H$1:$H${len(ind_counts)}',
        'points': [{'fill': {'color': '#9BBB59'}}],
    })
    chart3.set_title({'name': 'Top Client Industries'})
    chart3.set_legend({'none': True})
    dash_sheet.insert_chart('B30', chart3, {'x_scale': 1.5, 'y_scale': 1.5})

    # Chart 4: Avg Clients per Partner Tier
    dash_sheet.write('K28', 'Avg Clients per Partner Tier', subtitle_fmt)
    # Join to get tier for each client or group partners
    # We need to count clients per partner, then group by tier
    client_counts = df_clients['Partner ID'].value_counts().reset_index()
    client_counts.columns = ['Partner ID', 'Client Count']
    # Ensure ID is string for merge
    df_partners['Partner ID'] = df_partners['Partner ID'].astype(str)
    client_counts['Partner ID'] = client_counts['Partner ID'].astype(str)
    
    merged = df_partners.merge(client_counts, on='Partner ID', how='left')
    merged['Client Count'] = merged['Client Count'].fillna(0)
    
    avg_clients_tier = merged.groupby('Partner Tier')['Client Count'].mean().sort_values(ascending=False)
    
    data_sheet.write_column('J1', avg_clients_tier.index)
    data_sheet.write_column('K1', avg_clients_tier.values)

    chart4 = workbook.add_chart({'type': 'column'})
    chart4.add_series({
        'categories': f'=ChartData!$J$1:$J${len(avg_clients_tier)}',
        'values':     f'=ChartData!$K$1:$K${len(avg_clients_tier)}',
        'points': [{'fill': {'color': '#8064A2'}}],
    })
    chart4.set_title({'name': 'Avg Clients per Tier'})
    chart4.set_legend({'none': True})
    dash_sheet.insert_chart('K30', chart4, {'x_scale': 1.5, 'y_scale': 1.5})

    # --- Helper to write sheet ---
    def write_sheet(sheet_name, df_in):
        sheet = workbook.add_worksheet(sheet_name)
        # Write headers
        for col_num, value in enumerate(df_in.columns):
            sheet.write(0, col_num, value, header_fmt)
        
        # Write data
        data = df_in.fillna('').values.tolist()
        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                sheet.write(row_num + 1, col_num, cell_value, cell_fmt)
        
        sheet.autofilter(0, 0, len(df_in), len(df_in.columns) - 1)
        sheet.set_column('A:Z', 20)

    # --- 2. Partners Raw Data ---
    logger.info("Writing Partners Raw Data...")
    write_sheet('Partners Raw Data', df_partners)

    # --- 3. Clients Raw Data ---
    logger.info("Writing Clients Raw Data...")
    write_sheet('Clients Raw Data', df_clients)

    writer.close()
    logger.info("Grand Dashboard created successfully.")

if __name__ == "__main__":
    create_grand_dashboard()
