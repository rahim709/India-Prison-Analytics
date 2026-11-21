"""Verify image artifacts and the source values used by additional plots."""
import json
from pathlib import Path
import unittest
import pandas as pd
from PIL import Image
from src.preprocessing.selection import load_descriptive_view

ROOT = Path(__file__).resolve().parents[1]

class VisualizationTest(unittest.TestCase):
    def test_catalog_has_unique_valid_high_resolution_images(self):
        rows=json.loads((ROOT/'results/plots/plot_catalog.json').read_text())
        self.assertEqual(len(rows),26)
        self.assertEqual(len({r['file'] for r in rows}),26)
        for row in rows:
            with Image.open(ROOT/'results/plots'/row['file']) as im:
                self.assertGreaterEqual(min(im.size),1000)
                self.assertAlmostEqual(im.info['dpi'][0],300,places=1)
                im.verify()
            self.assertTrue(row['inference'])
        self.assertFalse((ROOT/'results/plots/13_status_annual_bars.png').exists())

    def test_crime_rankings_use_latest_year_source_values(self):
        source=load_descriptive_view(ROOT,'IPC_crime_inmates_convicted.csv')
        fields=[c for c in source if c.startswith(('Male ','Female '))]
        expected=source[source.year.eq(2013)].set_index(['state','CRIME HEAD'])[fields].sum(axis=1)
        for path in (ROOT/'results/tables/visualization').glob('*crime_rankings*.csv'):
            data=pd.read_csv(path)
            self.assertTrue(data.year.eq(2013).all())
            values=expected.reindex(pd.MultiIndex.from_frame(data[['state','CRIME HEAD']]))
            self.assertEqual(values.tolist(),data.reported_count.tolist())

    def test_crime_trends_use_a_fixed_complete_panel(self):
        source=load_descriptive_view(ROOT,'IPC_crime_inmates_convicted.csv')
        complete=source.groupby('state').year.nunique()
        fixed=source[source.state.isin(complete[complete.eq(13)].index)]
        fields=[c for c in fixed if c.startswith(('Male ','Female '))]
        expected=fixed.assign(n=fixed[fields].sum(axis=1)).groupby(['year','CRIME HEAD']).n.sum()
        self.assertEqual(fixed.state.nunique(),32)
        for path in (ROOT/'results/tables/visualization').glob('*crime_trends*.csv'):
            data=pd.read_csv(path)
            values=expected.reindex(pd.MultiIndex.from_frame(data[['year','CRIME HEAD']]))
            self.assertEqual(values.tolist(),data.reported_count.tolist())

    def test_notebook_generates_each_chart_directly(self):
        notebook=json.loads((ROOT/'notebooks/03_Visualization.ipynb').read_text())
        cells=[c for c in notebook['cells'] if c['cell_type']=='code']
        self.assertEqual(len(cells),28)
        source='\n'.join(''.join(c['source']) for c in cells)
        self.assertNotIn('run_visualization',source)
        self.assertNotIn('Image(filename',source)
        self.assertNotIn('plt.imread',source)
        chart_cells=cells[1:-1]
        for cell in chart_cells:
            code=''.join(cell['source'])
            self.assertTrue('plt.figure(' in code or 'plt.subplots(' in code)
            self.assertTrue(cell['execution_count'] is not None)
            self.assertFalse(any(o.get('output_type')=='error' for o in cell.get('outputs',[])))
            self.assertEqual(sum('image/png' in o.get('data',{}) for o in cell.get('outputs',[])),1)

    def test_status_rankings_do_not_pool_years(self):
        plot=pd.read_csv(ROOT/'results/tables/visualization/11_status_state_rankings.csv')
        reference=pd.read_csv(ROOT/'results/tables/descriptive/latest_state_snapshot.csv')
        self.assertTrue(plot.year.eq(2013).all())
        for field in ['convicts','under_trial']:
            self.assertEqual(plot.set_index('state')[field].sort_index().tolist(),reference.set_index('state')[field].sort_index().tolist())

if __name__=='__main__':unittest.main()
