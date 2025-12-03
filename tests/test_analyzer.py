import unittest
import sys
import os
import pandas as pd
import numpy as np

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzer import (
    calculate_peer_stats, calculate_summary_score, create_peer_comparison_table
)


class TestAnalyzer(unittest.TestCase):

    def setUp(self):
        """Set up sample data for tests with all necessary keys."""
        self.peer_data = {
            'PEER1': {'P/E': 10, 'Forward P/E': 9, 'PEG Ratio': 1.0, 'EPS': 1.0,
                      'EPS Growth': 0.1, 'Debt/Equity': 50, 'ROE': 0.1,
                      'Operating Margin': 0.1, 'Gross Margin': 0.3,
                      'Revenue Growth': 0.05, 'Free Cash Flow': 1000},
            'PEER2': {'P/E': 20, 'Forward P/E': 18, 'PEG Ratio': 2.0, 'EPS': 2.0,
                      'EPS Growth': 0.2, 'Debt/Equity': 100, 'ROE': 0.2,
                      'Operating Margin': 0.2, 'Gross Margin': 0.5,
                      'Revenue Growth': 0.10, 'Free Cash Flow': 2000},
            'PEER3': {'P/E': None, 'Forward P/E': None, 'PEG Ratio': None,
                      'EPS': 1.5, 'EPS Growth': 0.15, 'Debt/Equity': 75,
                      'ROE': 0.15, 'Operating Margin': 0.15, 'Gross Margin': 0.4,
                      'Revenue Growth': 0.07, 'Free Cash Flow': 1500},
        }
        self.target_data = {
            'P/E': 15, 'Forward P/E': 14, 'PEG Ratio': 1.5, 'ROE': 0.25,
            'Operating Margin': 0.25, 'Gross Margin': 0.6, 'Revenue Growth': 0.12,
            'EPS Growth': 0.25, 'Debt/Equity': 40
        }

    def test_calculate_peer_stats(self):
        stats = calculate_peer_stats(self.peer_data)
        self.assertAlmostEqual(stats['P/E']['mean'], 15.0)
        self.assertAlmostEqual(stats['P/E']['median'], 15.0)
        self.assertAlmostEqual(stats['ROE']['mean'], 0.15)
        self.assertAlmostEqual(stats['ROE']['median'], 0.15)
        self.assertAlmostEqual(stats['Debt/Equity']['mean'], 75.0)
        self.assertAlmostEqual(stats['Debt/Equity']['median'], 75.0)
        self.assertTrue(np.isnan(stats['PEG Ratio']['mean']) or
                        isinstance(stats['PEG Ratio']['mean'], float))

    def test_calculate_summary_score_stronger(self):
        peer_stats = calculate_peer_stats(self.peer_data)
        strong_target = self.target_data.copy()
        strong_target.update({'P/E': 8, 'ROE': 0.3, 'Debt/Equity': 20,
                              'Revenue Growth': 0.15})
        score = calculate_summary_score(strong_target, peer_stats)
        self.assertGreater(score, 60)

    def test_calculate_summary_score_weaker(self):
        peer_stats = calculate_peer_stats(self.peer_data)
        weak_target = self.target_data.copy()
        weak_target.update({'P/E': 30, 'ROE': 0.05, 'Debt/Equity': 200,
                            'Revenue Growth': 0.01})
        score = calculate_summary_score(weak_target, peer_stats)
        self.assertLess(score, 40)

    def test_calculate_summary_score_average(self):
        peer_stats = calculate_peer_stats(self.peer_data)
        avg_target = {k: v['mean'] for k, v in peer_stats.items()
                      if 'mean' in v and pd.notna(v['mean'])}
        for key in self.target_data:
            if key not in avg_target:
                avg_target[key] = 0
        score = calculate_summary_score(avg_target, peer_stats)
        self.assertTrue(45 <= score <= 55)

    def test_create_peer_comparison_table(self):
        peer_stats = calculate_peer_stats(self.peer_data)
        table = create_peer_comparison_table(self.target_data, peer_stats)
        self.assertIn("| P/E                | 15.00          | 15.00             | +0.0%              |", table)
        self.assertIn("| ROE                | 25.00%         | 15.00%            | +66.7%             |", table)
        self.assertIn("| Debt/Equity        | 40.00          | 75.00             | -46.7%             |", table)


if __name__ == '__main__':
    unittest.main()
