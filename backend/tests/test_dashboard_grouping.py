import sys
import unittest
from unittest.mock import MagicMock, call

# Mock streamlit before importing pages
mock_st = MagicMock()
# Make mock expander work as context manager
mock_expander = MagicMock()
mock_st.expander.return_value = mock_expander
mock_expander.__enter__.return_value = mock_expander

# Mock columns to return an iterable of sub-mocks matching the count
def mock_columns(n):
    return [MagicMock() for _ in range(n)]
mock_st.columns.side_effect = mock_columns

# Assign mock streamlit to sys.modules
sys.modules['streamlit'] = mock_st

import pandas as pd
from console.pages.command_center import render_command_center
from console.pages.active_forecasts import render_active_forecasts

class TestDashboardGrouping(unittest.TestCase):
    def setUp(self):
        # Reset mock after each test
        mock_st.reset_mock()
        mock_expander.reset_mock()
        
        # Standard app state and mock market snaps
        self.app_state = {
            "weather_gate": {
                "status": "OK",
                "allow_paper_recommendations": True,
                "observation_age_minutes": 10.0,
                "warnings": []
            },
            "latest_kalshi_json": MagicMock(),
            "latest_status_json": MagicMock(),
        }
        self.app_state["latest_kalshi_json"].exists.return_value = False
        
        self.mkts = {
            "total_markets_returned": 2,
            "selected_temperature_markets": [{"ticker": "KX-1"}]
        }

        # Setup standard mock signals for date-specific and fallback scenarios
        self.mock_signals = [
            {
                "market_ticker": "KXHIGHMIA-26MAY20-B88.5",
                "event_ticker": "KXHIGHMIA-26MAY20",
                "market_title": "Miami Max Temp >= 89°F",
                "status": "ACTIVE",
                "condition_type": "above",
                "contract_range": "88.0-89.0",
                "model_probability": 0.55,
                "market_probability": 0.40,
                "raw_edge": 0.15,
                "executable_edge": 0.14,
                "paper_action": "PAPER BUY CANDIDATE",
                "no_trade_reason": "All risk gates passed.",
                "warnings": ["Low liquidity"]
            }
        ]

    def test_single_date_behavior_zero_regression(self):
        """1. Verify single-date layout behaves exactly as before with no collapsible expanders."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "forecast_source": "forecast_2026-05-20.json",
            "signals": self.mock_signals,
            "dynamic_contract_probabilities": {
                "88-89": 0.55
            },
            "status": "OK",
            "warnings": []
        }

        # Render Command Center
        render_command_center(self.app_state, p_data, self.mkts)
        
        # Check no expanders were created for grouping (st.expander should not be called with 'Market Date')
        for call_args in mock_st.expander.call_args_list:
            self.assertNotIn("Market Date", call_args[0][0])

        # Verify st.dataframe was called for the bins and signals tables
        df_calls = [c for c in mock_st.dataframe.call_args_list]
        self.assertTrue(len(df_calls) >= 2)
        
        # Verify columns of Suggested Paper Contracts table
        sig_df = df_calls[-1][0][0]
        self.assertTrue(isinstance(sig_df, pd.DataFrame))
        # For single date on Command Center, it formats using the 11 columns
        expected_cols = [
            "Market Date", "Market Ticker", "Contract Ticker", "Bin/Range",
            "Model Prob", "Market Prob", "Raw Edge", "Executable Edge",
            "Paper Action", "No-Trade Reason", "Warnings"
        ]
        self.assertEqual(list(sig_df.columns), expected_cols)

        # Reset and check Active Forecasts
        mock_st.reset_mock()
        render_active_forecasts(p_data)
        
        # Active Forecasts with single date must not use expanders
        for call_args in mock_st.expander.call_args_list:
            self.assertNotIn("Market Date", call_args[0][0])
            
        # For single-date Active Forecasts, it must use the original 16-column layout
        df_calls_active = [c for c in mock_st.dataframe.call_args_list]
        self.assertTrue(len(df_calls_active) >= 2)
        sig_df_active = df_calls_active[-1][0][0]
        self.assertIn("Ticker", sig_df_active.columns)
        self.assertIn("Contract", sig_df_active.columns)
        self.assertIn("Threshold", sig_df_active.columns)
        self.assertIn("Model %", sig_df_active.columns)

    def test_multi_date_rendering_with_expanders(self):
        """2. Verify multiple dates render as separate grouped expanders using the 11-column format."""
        p_data = {
            "events_by_date": {
                "2026-05-20": {
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "forecast_source": "f_20",
                    "signals": self.mock_signals,
                    "dynamic_contract_probabilities": {"88-89": 0.55},
                    "status": "OK",
                    "warnings": []
                },
                "2026-05-21": {
                    "event_ticker": "KXHIGHMIA-26MAY21",
                    "forecast_source": "f_21",
                    "signals": [
                        {
                            "market_ticker": "KXHIGHMIA-26MAY21-B90.5",
                            "event_ticker": "KXHIGHMIA-26MAY21",
                            "contract_range": "90.0-91.0",
                            "model_probability": 0.30,
                            "market_probability": 0.25,
                            "raw_edge": 0.05,
                            "executable_edge": 0.04,
                            "paper_action": "PAPER BUY CANDIDATE",
                            "no_trade_reason": "All risk gates passed.",
                            "warnings": []
                        }
                    ],
                    "dynamic_contract_probabilities": {"90-91": 0.30},
                    "status": "OK",
                    "warnings": []
                }
            }
        }

        # Check Command Center multi-date grouping
        render_command_center(self.app_state, p_data, self.mkts)
        
        # Verify expanders were opened for both dates
        expander_titles = [call_args[0][0] for call_args in mock_st.expander.call_args_list if "Market Date" in call_args[0][0]]
        self.assertEqual(len(expander_titles), 2)
        self.assertIn("📅 Market Date: 2026-05-20 (KXHIGHMIA-26MAY20)", expander_titles)
        self.assertIn("📅 Market Date: 2026-05-21 (KXHIGHMIA-26MAY21)", expander_titles)

        # Check Active Forecasts multi-date grouping
        mock_st.reset_mock()
        render_active_forecasts(p_data)
        
        expander_titles_active = [call_args[0][0] for call_args in mock_st.expander.call_args_list if "Market Date" in call_args[0][0]]
        self.assertEqual(len(expander_titles_active), 2)
        
        # Verify the Suggeted Paper Contracts table in both dates uses the exact 11 columns in order
        df_calls = [c for c in mock_st.dataframe.call_args_list]
        # We should have 4 dataframes rendered: Bins(Date 1), Signals(Date 1), Bins(Date 2), Signals(Date 2)
        self.assertEqual(len(df_calls), 4)
        
        expected_cols = [
            "Market Date", "Market Ticker", "Contract Ticker", "Bin/Range",
            "Model Prob", "Market Prob", "Raw Edge", "Executable Edge",
            "Paper Action", "No-Trade Reason", "Warnings"
        ]
        
        # Inspect second and fourth dataframe columns (which are the signals tables)
        sig_df_1 = df_calls[1][0][0]
        sig_df_2 = df_calls[3][0][0]
        self.assertEqual(list(sig_df_1.columns), expected_cols)
        self.assertEqual(list(sig_df_2.columns), expected_cols)

    def test_missing_forecast_probabilities_warning(self):
        """3. Verify that a date missing dynamic forecast probabilities shows a warning block instead of crashing."""
        p_data = {
            "events_by_date": {
                "2026-05-20": {
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "forecast_source": "f_20",
                    "signals": self.mock_signals,
                    "dynamic_contract_probabilities": None,  # Missing probabilities
                    "status": "OK",
                    "warnings": []
                }
            }
        }

        # Verify command center doesn't crash and displays warning
        render_command_center(self.app_state, p_data, self.mkts)
        warning_calls = [c[0][0] for c in mock_st.warning.call_args_list]
        self.assertTrue(any("No forecast probabilities available for 2026-05-20" in w for w in warning_calls))

        # Verify active forecasts doesn't crash and displays warning
        mock_st.reset_mock()
        render_active_forecasts(p_data)
        warning_calls_active = [c[0][0] for c in mock_st.warning.call_args_list]
        self.assertTrue(any("No forecast probabilities available for 2026-05-20" in w for w in warning_calls_active))

    def test_no_live_execution_controls_introduced(self):
        """4. Safety check to guarantee that no live order placing or cancel buttons are rendered."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "forecast_source": "f_20",
            "signals": self.mock_signals,
            "dynamic_contract_probabilities": {"88-89": 0.55},
            "status": "OK"
        }

        # Check Active Forecasts
        render_active_forecasts(p_data)
        button_calls = [c[0][0] for c in mock_st.button.call_args_list if len(c[0]) > 0]
        # Any interactive button must not have labels like "Buy", "Place Order", "Cancel"
        for label in button_calls:
            self.assertNotIn("buy", label.lower())
            self.assertNotIn("order", label.lower())
            self.assertNotIn("cancel", label.lower())
            self.assertNotIn("execute", label.lower())

    def test_model_probability_numeric_sorting(self):
        """5. Verify that Model Prob is numeric and configured for correct numeric sorting and percent display formatting in both tables."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "forecast_source": "f_20",
            "dynamic_contract_probabilities": {
                "85-86": 0.15,
                "87-88": 0.21
            },
            "signals": self.mock_signals,
            "status": "OK"
        }

        # Clear mock calls
        mock_st.reset_mock()

        # Run command center rendering
        render_command_center(self.app_state, p_data, self.mkts)

        # Retrieve st.dataframe calls
        df_calls = [c for c in mock_st.dataframe.call_args_list]
        self.assertTrue(len(df_calls) >= 1)

        # Find the dataframe displaying the bins/probabilities
        prob_df = None
        column_config = None
        for call in df_calls:
            df = call[0][0]
            if "Model Prob" in df.columns and len(df.columns) == 2:  # Bins table
                prob_df = df
                column_config = call[1].get("column_config")
                break

        self.assertIsNotNone(prob_df, "Probability dataframe not found in Command Center")

        # Verify underlying values are float/numeric
        model_probs = prob_df["Model Prob"].tolist()
        for p in model_probs:
            self.assertTrue(isinstance(p, (int, float)), f"Value {p} is not numeric")

        # Verify sorting behavior: 15.0 < 21.0 numerically
        self.assertTrue(model_probs[0] < model_probs[1], f"Probabilities do not sort numerically: {model_probs}")

        # Verify display configuration formatting remains as percentage
        self.assertIsNotNone(column_config, "st.dataframe column_config is missing")
        self.assertIn("Model Prob", column_config)

    def test_model_prob_visible_column_sorting(self):
        """6. Verify that Model Prob visible column has numeric dtype and sorts correctly."""
        # 15.7%, 21.0%, 21.2%, 30.3%, 4.5%, 7.3%
        raw_probs = [0.157, 0.210, 0.212, 0.303, 0.045, 0.073]
        signals = []
        for i, p in enumerate(raw_probs):
            signals.append({
                "market_ticker": f"KXHIGHMIA-26MAY20-B{i}",
                "event_ticker": "KXHIGHMIA-26MAY20",
                "contract_range": f"{80+i}-{81+i}",
                "model_probability": p,
                "market_probability": 0.40,
                "raw_edge": 0.15,
                "executable_edge": 0.14,
                "paper_action": "PAPER BUY CANDIDATE"
            })

        p_data = {
            "primary_event_date": "2026-05-20",
            "forecast_source": "f_20",
            "dynamic_contract_probabilities": {},
            "signals": signals,
            "status": "OK"
        }

        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)

        df_calls = [c for c in mock_st.dataframe.call_args_list]
        self.assertTrue(len(df_calls) >= 1)

        # Find signals dataframe (has multiple columns)
        sig_df = None
        column_config = None
        for call in df_calls:
            df = call[0][0]
            if "Model Prob" in df.columns and "Paper Action" in df.columns:
                sig_df = df
                column_config = call[1].get("column_config")
                break

        self.assertIsNotNone(sig_df, "Signals dataframe not found in Command Center")

        # Verify dtype is numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(sig_df["Model Prob"]))

        # Ascending sort: 4.5, 7.3, 15.7, 21.0, 21.2, 30.3
        sorted_asc = sig_df["Model Prob"].sort_values(ascending=True).tolist()
        expected_asc = [4.5, 7.3, 15.7, 21.0, 21.2, 30.3]
        for a, b in zip(sorted_asc, expected_asc):
            self.assertAlmostEqual(a, b, places=4)

        # Descending sort: 30.3, 21.2, 21.0, 15.7, 7.3, 4.5
        sorted_desc = sig_df["Model Prob"].sort_values(ascending=False).tolist()
        expected_desc = [30.3, 21.2, 21.0, 15.7, 7.3, 4.5]
        for a, b in zip(sorted_desc, expected_desc):
            self.assertAlmostEqual(a, b, places=4)

        # Verify column_config contains "Model Prob" with percent format
        self.assertIsNotNone(column_config, "column_config is missing")
        self.assertIn("Model Prob", column_config)
        
        # Verify NumberColumn formatter was configured with correct parameters
        number_column_calls = mock_st.column_config.NumberColumn.call_args_list
        self.assertTrue(any(c[0][0] == "Model Prob" and c[1].get("format") == "%.1f%%" for c in number_column_calls))

if __name__ == "__main__":
    unittest.main()
