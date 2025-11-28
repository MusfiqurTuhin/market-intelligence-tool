import pandas as pd
import xlsxwriter
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INPUT_FILE = "data/raw/global_partner_clients.csv"
OUTPUT_FILE = "data/raw/global_partner_clients.xlsx"

def clean_data(df):
    """Clean and prepare data for analysis."""
    # Convert Project Size to numeric (extract lower bound)
    # e.g., "10 users" -> 10, "200+ users" -> 200
    def parse_size(val):
        if pd.isna(val): return 0
        import re
        match = re.search(r'(\d+)', str(val))
        return int(match.group(1)) if match else 0

    df['Project Size (Numeric)'] = df['Avg Project Size'].apply(parse_size)
    
    # Clean Industry (take first if multiple)
    df['Primary Industry'] = df['Client Industry'].apply(lambda x: str(x).split(',')[0] if pd.notna(x) else "Unknown")
    
    return df

def create_dashboard():
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found.")
        return

    logger.info(f"Reading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    df = clean_data(df)

    logger.info(f"Creating Excel dashboard at {OUTPUT_FILE}...")
    writer = pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter')
    workbook = writer.book

    # --- Formats ---
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
    cell_fmt = workbook.add_format({'border': 1})
    num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#366092'})
    metric_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#DCE6F1', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    metric_label_fmt = workbook.add_format({'font_size': 10, 'bg_color': '#DCE6F1', 'border': 1, 'align': 'center', 'valign': 'vcenter'})

    # --- 1. Dashboard Sheet ---
    dash_sheet = workbook.add_worksheet('Dashboard')
    dash_sheet.hide_gridlines(2)
    dash_sheet.set_column('A:Z', 15)

    # Title
    dash_sheet.write('B2', 'Odoo Partner Client Dashboard', title_fmt)

    # KPIs
    total_partners = df['Partner ID'].nunique()
    total_clients = len(df)
    avg_clients_per_partner = total_clients / total_partners if total_partners else 0

    dash_sheet.merge_range('B4:C4', 'Total Partners', metric_label_fmt)
    dash_sheet.merge_range('B5:C5', total_partners, metric_fmt)

    dash_sheet.merge_range('E4:F4', 'Total Clients Scraped', metric_label_fmt)
    dash_sheet.merge_range('E5:F5', total_clients, metric_fmt)

    dash_sheet.merge_range('H4:I4', 'Avg Clients/Partner', metric_label_fmt)
    dash_sheet.merge_range('H5:I5', round(avg_clients_per_partner, 1), metric_fmt)

    # Chart 1: Top 10 Industries
    top_industries = df['Primary Industry'].value_counts().head(10)
    dash_sheet.write('B8', 'Top 10 Client Industries', workbook.add_format({'bold': True}))
    
    # Write data for chart (hidden)
    data_sheet = workbook.add_worksheet('ChartData')
    data_sheet.hide()
    data_sheet.write_column('A1', top_industries.index)
    data_sheet.write_column('B1', top_industries.values)

    chart1 = workbook.add_chart({'type': 'bar'})
    chart1.add_series({
        'categories': '=ChartData!$A$1:$A$10',
        'values':     '=ChartData!$B$1:$B$10',
        'points': [{'fill': {'color': '#4F81BD'}}],
    })
    chart1.set_title({'name': 'Top 10 Client Industries'})
    chart1.set_legend({'none': True})
    dash_sheet.insert_chart('B10', chart1, {'x_scale': 1.5, 'y_scale': 1.5})

    # Chart 2: Project Size Distribution
    size_dist = df['Large Project Size'].value_counts().head(5)
    dash_sheet.write('K8', 'Project Size Distribution', workbook.add_format({'bold': True}))
    
    data_sheet.write_column('D1', size_dist.index)
    data_sheet.write_column('E1', size_dist.values)

    chart2 = workbook.add_chart({'type': 'pie'})
    chart2.add_series({
        'categories': '=ChartData!$D$1:$D$5',
        'values':     '=ChartData!$E$1:$E$5',
    })
    chart2.set_title({'name': 'Project Size Distribution'})
    dash_sheet.insert_chart('K10', chart2, {'x_scale': 1.5, 'y_scale': 1.5})

    # Top Partners Table
    dash_sheet.write('B28', 'Top Partners by Client Count', workbook.add_format({'bold': True}))
    top_partners = df.groupby('Partner Name').size().sort_values(ascending=False).head(10)
    
    dash_sheet.write('B29', 'Partner Name', header_fmt)
    dash_sheet.write('C29', 'Client Count', header_fmt)
    
    for i, (partner, count) in enumerate(top_partners.items()):
        dash_sheet.write(29 + i, 1, partner, cell_fmt)
        dash_sheet.write(29 + i, 2, count, num_fmt)

    # --- 2. Data Sheet ---
    sheet_data = workbook.add_worksheet('Client Data')
    
    # Write headers
    for col_num, value in enumerate(df.columns):
        sheet_data.write(0, col_num, value, header_fmt)

    # Write data
    # Use to_excel logic but manually to apply formats if needed, or just loop
    # For speed with large data, we can use writerows if we convert to list
    # But xlsxwriter doesn't support writerows directly on worksheet object like csv
    # We iterate.
    
    data = df.values.tolist()
    for row_num, row_data in enumerate(data):
        for col_num, cell_value in enumerate(row_data):
            # Handle NaN
            if pd.isna(cell_value):
                cell_value = ""
            sheet_data.write(row_num + 1, col_num, cell_value, cell_fmt)

    # Add autofilter
    sheet_data.autofilter(0, 0, len(df), len(df.columns) - 1)
    sheet_data.set_column('A:Z', 20) # Set default width

    writer.close()
    logger.info("Dashboard created successfully.")

if __name__ == "__main__":
    create_dashboard()
