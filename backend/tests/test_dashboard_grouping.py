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
mock_st.selectbox.return_value = "risk_adjusted_mode"
mock_st.number_input.return_value = 1000.0

# Assign mock streamlit to sys.modules
sys.modules['streamlit'] = mock_st

import pandas as pd
from console.pages.command_center import render_command_center
from console.pages.active_forecasts import render_active_forecasts
from console.market_visibility import (
    build_kalshi_bins_rows,
    partition_market_dates,
    MARKET_STATUS_CLOSED,
    MARKET_STATUS_MISSING_FORECAST,
    MARKET_STATUS_OPEN,
    MARKET_STATUS_STALE_MARKET_DATA,
)

class TestDashboardGrouping(unittest.TestCase):
    def setUp(self):
        # Reset mock after each test
        mock_st.reset_mock()
        mock_expander.reset_mock()
        mock_st.selectbox.return_value = "risk_adjusted_mode"
        mock_st.number_input.return_value = 1000.0
        
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
            "open_market_dates": ["2026-05-20"],
            "forecast_source": "forecast_2026-05-20.json",
            "signals": self.mock_signals,
            "dynamic_contract_probabilities": {
                "88-89": 0.55
            },
            "events_by_date": {
                "2026-05-20": {
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "market_status": MARKET_STATUS_OPEN,
                    "signals": self.mock_signals,
                    "dynamic_contract_probabilities": {"88-89": 0.55},
                    "contracts": [{"forecast_bin_label": "88-89", "ticker": "KX-1"}],
                }
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
        """2. OPEN/STALE primary sections; CLOSED collapsed under historical expander."""
        p_data = {
            "open_market_dates": ["2026-05-21"],
            "events_by_date": {
                "2026-05-20": {
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "market_status": MARKET_STATUS_CLOSED,
                    "forecast_source": "f_20",
                    "signals": self.mock_signals,
                    "dynamic_contract_probabilities": {"88-89": 0.55},
                    "contracts": [{"forecast_bin_label": "88-89"}],
                    "status": "OK",
                    "warnings": []
                },
                "2026-05-21": {
                    "event_ticker": "KXHIGHMIA-26MAY21",
                    "market_status": MARKET_STATUS_STALE_MARKET_DATA,
                    "snapshot_age_minutes": 1545.0,
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
                    "contracts": [{"forecast_bin_label": "90-91"}],
                    "status": "OK",
                    "warnings": []
                }
            }
        }

        render_command_center(self.app_state, p_data, self.mkts)

        expander_titles = [c[0][0] for c in mock_st.expander.call_args_list]
        self.assertTrue(
            any("Closed / historical" in t for t in expander_titles),
            f"Expected closed expander, got: {expander_titles}",
        )
        self.assertFalse(
            any("Market Date: 2026-05-20" in t and "Closed" not in t for t in expander_titles)
        )

        markdown_text = " ".join(c[0][0] for c in mock_st.markdown.call_args_list)
        self.assertIn("STALE_MARKET_DATA", markdown_text)
        self.assertIn("2026-05-21", markdown_text)

        success_msgs = [c[0][0] for c in mock_st.success.call_args_list]
        self.assertTrue(any("Open market dates" in m and "2026-05-21" in m for m in success_msgs))

        mock_st.reset_mock()
        render_active_forecasts(p_data)

        expander_titles_active = [c[0][0] for c in mock_st.expander.call_args_list]
        self.assertTrue(any("Closed / historical" in t for t in expander_titles_active))

        df_calls = [c for c in mock_st.dataframe.call_args_list]
        self.assertGreaterEqual(len(df_calls), 1)

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
        self.assertTrue(
            any(
                "No forecast probabilities" in w
                or "Forecast distribution missing" in w
                or "No contracts" in w
                for w in warning_calls
            )
        )

        # Verify active forecasts doesn't crash and displays warning
        mock_st.reset_mock()
        render_active_forecasts(p_data)
        warning_calls_active = [c[0][0] for c in mock_st.warning.call_args_list]
        self.assertTrue(
            any(
                "Forecast distribution missing" in w
                or "No contracts" in w
                or "No forecast probabilities" in w
                for w in warning_calls_active
            )
        )

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

    def _money_distribution_fixture(self):
        return {
            "generated_at_utc": "2026-05-20T12:00:00+00:00",
            "market_date": "2026-05-20",
            "total_available_dollars": 1000.0,
            "allocation_mode": "risk_adjusted",
            "guaranteed_profit_possible": False,
            "portfolio_expected_profit": 12.5,
            "probability_of_profit": 0.455,
            "worst_case_profit": -103.52,
            "best_case_profit": 85.0,
            "total_allocated": 103.52,
            "cash_unallocated": 896.48,
            "rows": [
                {
                    "contract_ticker": "KXHIGHMIA-26MAY20-B88.5",
                    "bin_range": "88.0-89.0",
                    "model_probability": 0.55,
                    "market_probability": 0.40,
                    "executable_price": 0.42,
                    "executable_edge": 0.13,
                    "recommended_allocation_dollars": 50.0,
                    "estimated_contracts": 119,
                    "expected_profit": 8.2,
                    "max_loss": 50.0,
                    "no_trade_reason": None,
                },
                {
                    "contract_ticker": "KXHIGHMIA-26MAY20-T86",
                    "bin_range": "86.0-87.0",
                    "model_probability": 0.21,
                    "market_probability": 0.25,
                    "executable_price": 0.28,
                    "executable_edge": -0.07,
                    "recommended_allocation_dollars": 0.0,
                    "estimated_contracts": 0,
                    "expected_profit": 0.0,
                    "max_loss": 0.0,
                    "no_trade_reason": "Insufficient executable edge",
                },
            ],
            "pnl_by_outcome": [
                {
                    "outcome_bin": "88.0-89.0",
                    "probability": 0.55,
                    "payout": 120.0,
                    "total_cost": 103.52,
                    "net_pnl": 16.48,
                },
                {
                    "outcome_bin": "uncovered",
                    "probability": 0.10,
                    "payout": 0.0,
                    "total_cost": 103.52,
                    "net_pnl": -103.52,
                },
            ],
            "warnings": [
                "Guaranteed net-positive allocation not available; showing best risk-adjusted paper allocation."
            ],
            "safety": {
                "no_real_trading": True,
                "no_order_execution": True,
                "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY",
            },
        }

    def test_money_distribution_panel_renders(self):
        """Money Distribution panel shows title, inputs, tables, and guarantee-false warning."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "forecast_source": "f_20",
            "signals": self.mock_signals,
            "dynamic_contract_probabilities": {"88-89": 0.55},
            "status": "OK",
            "money_distribution": self._money_distribution_fixture(),
        }

        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)

        subheader_titles = [c[0][0] for c in mock_st.subheader.call_args_list]
        self.assertIn("💰 Paper Money Distribution by Bin", subheader_titles)

        mock_st.number_input.assert_called()
        mock_st.selectbox.assert_called()
        select_labels = [c[1].get("label") for c in mock_st.selectbox.call_args_list if c[1]]
        self.assertTrue(
            any("Allocation Mode" in str(x) for x in select_labels)
            or mock_st.selectbox.called
        )

        warning_msgs = [c[0][0] for c in mock_st.warning.call_args_list]
        self.assertTrue(
            any("Guaranteed net-positive allocation unavailable" in w for w in warning_msgs)
        )

        df_calls = [c for c in mock_st.dataframe.call_args_list]
        alloc_df = None
        outcome_df = None
        bins_df = None
        for call in df_calls:
            df = call[0][0]
            if not isinstance(df, pd.DataFrame):
                continue
            cols = list(df.columns)
            if "Recommended Paper Allocation" in cols:
                alloc_df = df
            elif "Settlement Outcome" in cols:
                outcome_df = df
            elif cols == ["Kalshi Bin (Range)", "Model Prob"]:
                bins_df = df

        self.assertIsNotNone(alloc_df, "Allocation table not rendered")
        self.assertEqual(len(alloc_df), 2)
        self.assertTrue(pd.api.types.is_numeric_dtype(alloc_df["Model Prob"]))
        self.assertTrue(alloc_df["Model Prob"].max() <= 1.0)

        self.assertIsNotNone(outcome_df, "Outcome table not rendered")
        self.assertIn("Portfolio PnL", outcome_df.columns)
        self.assertIn("Profitable?", outcome_df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(outcome_df["Outcome Probability"]))

        self.assertIsNotNone(bins_df, "Kalshi Bins table should remain unchanged")

    def test_money_distribution_primary_date_only_note(self):
        """When events_by_date has multiple dates, show primary-date-only allocation note."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "events_by_date": {
                "2026-05-20": {
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "signals": self.mock_signals,
                    "dynamic_contract_probabilities": {"88-89": 0.55},
                },
                "2026-05-21": {
                    "event_ticker": "KXHIGHMIA-26MAY21",
                    "signals": [],
                    "dynamic_contract_probabilities": {},
                },
            },
            "money_distribution": self._money_distribution_fixture(),
        }

        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)

        info_msgs = [c[0][0] for c in mock_st.info.call_args_list]
        self.assertTrue(
            any("primary date 2026-05-20" in m and "2026-05-21" in m for m in info_msgs)
        )

    def test_money_distribution_no_live_order_buttons(self):
        """Money distribution section must not add order placement controls."""
        p_data = {
            "primary_event_date": "2026-05-20",
            "signals": self.mock_signals,
            "dynamic_contract_probabilities": {"88-89": 0.55},
            "money_distribution": self._money_distribution_fixture(),
        }

        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)

        button_labels = [c[0][0] for c in mock_st.button.call_args_list if c[0]]
        for label in button_labels:
            low = str(label).lower()
            self.assertNotIn("place order", low)
            self.assertNotIn("buy now", low)
            self.assertNotIn("execute", low)


    def test_partition_open_market_dates_ordering(self):
        """open_market_dates drives primary ordering before other visible dates."""
        events = {
            "2026-05-20": {"market_status": MARKET_STATUS_CLOSED},
            "2026-05-21": {"market_status": MARKET_STATUS_STALE_MARKET_DATA},
            "2026-05-22": {"market_status": MARKET_STATUS_OPEN},
        }
        primary, pre_open, closed = partition_market_dates(events, ["2026-05-21", "2026-05-22"])
        self.assertEqual(closed, ["2026-05-20"])
        self.assertEqual(primary[0], "2026-05-21")
        self.assertEqual(primary[1], "2026-05-22")

    def test_build_kalshi_bins_rows_missing_forecast_no_fake_prob(self):
        """MISSING_FORECAST shows contracts with null Model Prob, not fabricated values."""
        rows = build_kalshi_bins_rows(
            {
                "market_status": MARKET_STATUS_MISSING_FORECAST,
                "dynamic_contract_probabilities": {},
                "contracts": [
                    {"forecast_bin_label": "88-89"},
                    {"forecast_bin_label": "90-91"},
                ],
            }
        )
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[0]["Model Prob"])
        self.assertIsNone(rows[1]["Model Prob"])

    def test_stale_market_date_shows_stale_warning_not_tradable(self):
        """STALE_MARKET_DATA date renders stale warning and not-tradable caption."""
        p_data = {
            "open_market_dates": ["2026-05-21"],
            "events_by_date": {
                "2026-05-21": {
                    "market_status": MARKET_STATUS_STALE_MARKET_DATA,
                    "snapshot_age_minutes": 90.0,
                    "contracts": [{"forecast_bin_label": "90-91"}],
                    "dynamic_contract_probabilities": {"90-91": 0.3},
                    "signals": [],
                }
            },
        }
        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)
        error_msgs = [c[0][0] for c in mock_st.error.call_args_list]
        self.assertTrue(any("snapshot stale" in m.lower() for m in error_msgs))
        captions = [c[0][0] for c in mock_st.caption.call_args_list]
        self.assertTrue(any("Not tradable" in c for c in captions))

    def test_closed_date_in_historical_expander(self):
        """CLOSED dates appear under collapsed historical expander, not as open markets."""
        p_data = {
            "open_market_dates": [],
            "events_by_date": {
                "2026-05-20": {
                    "market_status": MARKET_STATUS_CLOSED,
                    "contracts": [{"forecast_bin_label": "88-89"}],
                    "dynamic_contract_probabilities": {"88-89": 0.5},
                    "signals": [],
                }
            },
        }
        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)
        expander_titles = [c[0][0] for c in mock_st.expander.call_args_list]
        self.assertTrue(any("Closed / historical" in t for t in expander_titles))
        info_msgs = [c[0][0] for c in mock_st.info.call_args_list]
        self.assertTrue(any("not used for active allocation" in m.lower() for m in info_msgs))

    def test_missing_forecast_date_still_visible_with_contracts(self):
        """Open date without forecast remains visible with contract rows."""
        p_data = {
            "open_market_dates": ["2026-05-21"],
            "events_by_date": {
                "2026-05-21": {
                    "market_status": MARKET_STATUS_MISSING_FORECAST,
                    "contracts": [
                        {"forecast_bin_label": "90-91"},
                        {"forecast_bin_label": "92-93"},
                    ],
                    "dynamic_contract_probabilities": {},
                    "signals": [],
                }
            },
        }
        mock_st.reset_mock()
        render_command_center(self.app_state, p_data, self.mkts)
        warning_msgs = [c[0][0] for c in mock_st.warning.call_args_list]
        self.assertTrue(any("Forecast distribution missing for 2026-05-21" in w for w in warning_msgs))
        df_calls = [c[0][0] for c in mock_st.dataframe.call_args_list]
        bins_df = next(
            (df for df in df_calls if isinstance(df, pd.DataFrame) and "Kalshi Bin (Range)" in df.columns),
            None,
        )
        self.assertIsNotNone(bins_df)
        self.assertEqual(len(bins_df), 2)
        self.assertTrue(bins_df["Model Prob"].isna().all())


if __name__ == "__main__":
    unittest.main()
