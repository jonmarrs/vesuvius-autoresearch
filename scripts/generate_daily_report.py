import os
import datetime
from fpdf import FPDF
import pandas as pd

class VesuviusReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Vesuvius Autoresearch: Daily Experimental Report', 0, new_x='LMARGIN', new_y='NEXT', align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, new_x='RIGHT', new_y='TOP', align='C')

def generate_pdf():
    print("Generating Professional PDF Report...")
    pdf = VesuviusReport()
    pdf.add_page()
    
    # 1. Executive Summary from LAB_NOTEBOOK.md
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Executive Summary & Insights', 0, new_x='LMARGIN', new_y='NEXT', align='L')
    pdf.set_font('helvetica', '', 10)
    
    if os.path.exists('LAB_NOTEBOOK.md'):
        with open('LAB_NOTEBOOK.md', 'r') as f:
            lines = f.readlines()
            # Get the first relevant section (latest entry)
            summary_lines = []
            for line in lines:
                if line.startswith('## '):
                    if len(summary_lines) > 5: break # Limit to latest
                summary_lines.append(line.strip())
            
            summary_text = "\n".join(summary_lines[:20]) # Limit length
            pdf.multi_cell(0, 5, summary_text)
    else:
        pdf.cell(0, 10, 'Lab notebook not found.', 0, 1, 'L')
    
    pdf.ln(10)

    # 2. Key Visualizations
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Performance Metrics & Frontier', 0, new_x='LMARGIN', new_y='NEXT', align='L')
    
    frontier_img = 'reports/figures/research_frontier.png'
    if os.path.exists(frontier_img):
        pdf.image(frontier_img, x=10, w=190)
    else:
        pdf.cell(0, 10, 'Frontier chart not found. Run plot_results.py first.', 0, 1, 'L')
    
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Hardware Efficiency Pareto', 0, new_x='LMARGIN', new_y='NEXT', align='L')
    
    pareto_img = 'reports/figures/hardware_efficiency.png'
    if os.path.exists(pareto_img):
        pdf.image(pareto_img, x=10, w=190)
    
    pdf.ln(10)

    # 4. Training Samples
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Training Data Samples (Visual Audit)', 0, new_x='LMARGIN', new_y='NEXT', align='L')
    
    import glob
    sample_images = sorted(glob.glob('reports/figures/training_samples/*.png'))
    if sample_images:
        latest_sample = sample_images[-1]
        pdf.image(latest_sample, x=10, w=190)
    else:
        pdf.cell(0, 10, 'Training samples not found. Run visualize_training_data.py first.', 0, 1, 'L')

    pdf.ln(10)

    # 5. Top Discoveries Table
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '5. Top discovery Milestones', 0, new_x='LMARGIN', new_y='NEXT', align='L')
    
    if os.path.exists('results.tsv'):
        df = pd.read_csv('results.tsv', sep='\t')
        if not df.empty:
            top_df = df.nsmallest(5, 'val_bpb')
            
            # Table Header
            pdf.set_font('helvetica', 'B', 10)
            pdf.cell(40, 10, 'Timestamp', 1, new_x='RIGHT', new_y='TOP')
            pdf.cell(30, 10, 'Val Dice Loss', 1, new_x='RIGHT', new_y='TOP')
            pdf.cell(30, 10, 'Throughput', 1, new_x='RIGHT', new_y='TOP')
            pdf.cell(30, 10, 'Params (M)', 1, new_x='LMARGIN', new_y='NEXT')
            
            # Table Rows
            pdf.set_font('helvetica', '', 9)
            for _, row in top_df.iterrows():
                pdf.cell(40, 10, str(row['timestamp'])[:16], 1, new_x='RIGHT', new_y='TOP')
                pdf.cell(30, 10, f"{row['val_bpb']:.6f}", 1, new_x='RIGHT', new_y='TOP')
                pdf.cell(30, 10, f"{row['throughput_Mvps']:.2f}", 1, new_x='RIGHT', new_y='TOP')
                pdf.cell(30, 10, f"{row['num_params_M']:.2f}", 1, new_x='LMARGIN', new_y='NEXT')
    
    os.makedirs('reports', exist_ok=True)
    report_path = f'reports/Vesuvius_Research_Report_{datetime.datetime.now().strftime("%Y-%m-%d")}.pdf'
    pdf.output(report_path)
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    generate_pdf()
