import unittest
import os
import shutil
import pandas as pd
from scripts.generate_daily_report import generate_pdf

class TestDailyReport(unittest.TestCase):
    def setUp(self):
        # Create mock data files
        with open('LAB_NOTEBOOK.md', 'w') as f:
            f.write("## 2026-05-15: Test Entry\nMock discovery logic worked well.")
            
        # Mock results.tsv
        df = pd.DataFrame({
            'timestamp': ['2026-05-15 20:44:15'],
            'val_bpb': [0.4136],
            'throughput_Mvps': [10.5],
            'num_params_M': [24.0]
        })
        df.to_csv('results.tsv', sep='\t', index=False)
        
        os.makedirs('reports', exist_ok=True)

    def tearDown(self):
        # Cleanup mock files
        if os.path.exists('LAB_NOTEBOOK.md'):
            os.remove('LAB_NOTEBOOK.md')
        if os.path.exists('results.tsv'):
            os.remove('results.tsv')
        # We don't necessarily want to delete all reports, 
        # but let's delete the specific test one if we can identify it.

    def test_report_generation_smoke(self):
        # This will test if the PDF generator runs without crashing
        # even if images are missing (it has checks for that).
        try:
            generate_pdf()
            # Success if no exception
            import datetime
            report_path = f'reports/Vesuvius_Research_Report_{datetime.datetime.now().strftime("%Y-%m-%d")}.pdf'
            self.assertTrue(os.path.exists(report_path))
        except Exception as e:
            self.fail(f"generate_pdf() raised {type(e).__name__} unexpectedly: {e}")

if __name__ == "__main__":
    unittest.main()
