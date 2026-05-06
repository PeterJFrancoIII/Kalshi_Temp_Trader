import sys
import os
import unittest

# Add backend and src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
# Add tests to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Hard dependency check — no mocks allowed in this test suite.
# If any required package is missing, fail loudly with setup instructions.
_REQUIRED = {
    "pydantic": "pydantic",
    "bs4": "beautifulsoup4",
    "requests": "requests",
    "sqlalchemy": "sqlalchemy",
    "dateutil": "python-dateutil",
}
_MISSING = []
for _mod, _pkg in _REQUIRED.items():
    try:
        __import__(_mod)
    except ImportError:
        _MISSING.append(_pkg)

if _MISSING:
    missing_str = ", ".join(_MISSING)
    print(
        f"\n[FATAL] Missing required test dependencies: {missing_str}\n"
        "Run:\n"
        "  python3 -m venv backend/venv && "
        "source backend/venv/bin/activate && "
        "pip install -r backend/requirements.txt\n"
    )
    sys.exit(1)

from test_calibration_metrics import (
    test_temp_to_bin_logic,
    test_top_bin_logic,
    test_score_prediction_hits,
    test_brier_score_reasonable,
    test_log_loss_finite_and_clipping,
    test_invalid_probabilities_errors,
    test_may_3_2026_specific_case
)

from test_kalshi_market_mapping import (
    test_map_kalshi_subtitle_to_bin,
    test_map_markets_to_bins,
    test_map_markets_to_bins_uncertain,
    test_calculate_orderbook_metrics,
    test_calculate_orderbook_metrics_empty,
    test_read_only_constraint
)

from test_kmia_live_parser import (
    test_parse_wrh_timeseries_empty,
    test_parse_wrh_timeseries_valid,
    test_parse_obhistory_html,
    test_compute_live_features_max_so_far,
    test_stale_data_flag,
    test_missing_temp,
    test_timezone_boundary,
    test_parse_obhistory_discovery,
    test_parse_obhistory_missing_table,
    test_parse_obhistory_malformed_temp,
    test_parse_obhistory_month_rollover,
    test_parse_obhistory_year_rollover
)

from test_climia_parser import (
    test_parse_normal,
    test_parse_missing,
    test_parse_trace_and_record,
    test_parse_incomplete
)

from test_temperature_bins import (
    test_temp_to_bin_logic as test_bin_logic,
    test_zeroing_82,
    test_zeroing_85,
    test_temp_82_maps,
    test_sum_to_one,
    test_all_bins_present,
    test_warning_missing_forecast,
    test_warning_stale_data,
    test_validate_probability_bins_logic
)

from test_daily_prediction_loop import (
    test_dry_run_v1_workflow,
    test_dry_run_v2_workflow,
    test_missing_history_v2_handling,
    test_compare_models_mode,
    test_no_trading_logic_called
)

from test_settlement_check import (
    test_settle_normal_82,
    test_settle_incomplete
)

from test_full_pipeline_readonly import (
    test_full_pipeline_dry_run,
    test_unit_consistency,
    test_safety_rejections,
    test_settlement_consistency,
    test_full_pipeline_with_paper_trading
)

from test_paper_trading import (
    test_save_load_record,
    test_simulate_yes_paper_fill,
    test_simulate_no_paper_fill,
    test_settle_final_high_82,
    test_settle_no_on_bin,
    test_invalid_records_rejected,
    test_compute_simulated_pnl
)

from test_climia_backfill import (
    test_load_canonical_history,
    test_historical_record_mapping
)

from test_local_climatology_loader import (
    test_load_local_climatology_file,
    test_write_history_jsonl
)

from test_climatology_features import (
    test_bin_mapping,
    test_bin_distribution,
    test_same_day_history,
    test_prior_bin_distribution_for_date,
    test_rolling_high_average,
    test_normal_like_high
)

from test_model_comparison import (
    test_score_model_comparison_enhanced_fields,
    test_winner_and_delta_logic,
    test_tie_behavior,
    test_summary_string,
    test_report_writers,
    test_legacy_save_comparison_report,
    test_comparison_markdown_nonzero_probabilities
)

from test_db_models import (
    test_daily_prediction_has_model_version,
    test_daily_prediction_model_version_default,
    test_daily_prediction_model_version_v2
)

from test_aggregate_calibration import (
    test_empty_comparison_list,
    test_basic_aggregation,
    test_missing_optional_fields,
    test_write_aggregate_json,
    test_write_aggregate_markdown,
    test_writers_handle_empty_report
)

from test_rules_model_v2 import TestRulesModelV2
from test_generate_aggregate_report import TestGenerateAggregateReport
from test_operational_scripts import TestOperationalScripts
from test_daily_status_cli import TestDailyStatusCLI
from test_daily_status import TestDailyStatus
from test_deployment_assets import TestDeploymentAssets
from test_daily_status_builder import (
    test_empty_directories,
    test_valid_aggregate_json,
    test_log_error_status,
    test_log_warning_status,
    test_normal_ok_status,
    test_safety_trading_disabled
)

from test_kalshi_public_market_data import (
    test_kalshi_client_no_auth_references,
    test_kalshi_client_mocked_discovery,
    test_kalshi_updater_logic
)

from test_sync_tooling import (
    test_scripts_contain_safety_disclaimer,
    test_check_sync_status_runs
)

from test_health_summary import (
    test_health_summary_script_exists,
    test_health_summary_is_executable,
    test_health_summary_safety_disclaimer,
    test_health_summary_no_dangerous_commands,
    test_health_summary_read_only
)


# Helper to run unittest classes in this runner
def run_unittest_class(cls):
    suite = unittest.TestLoader().loadTestsFromTestCase(cls)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise Exception(f"Unittest class {cls.__name__} failed")

tests = [
    test_temp_to_bin_logic,
    test_top_bin_logic,
    test_score_prediction_hits,
    test_brier_score_reasonable,
    test_log_loss_finite_and_clipping,
    test_invalid_probabilities_errors,
    test_may_3_2026_specific_case,
    test_map_kalshi_subtitle_to_bin,
    test_map_markets_to_bins,
    test_map_markets_to_bins_uncertain,
    test_calculate_orderbook_metrics,
    test_calculate_orderbook_metrics_empty,
    test_read_only_constraint,
    test_parse_wrh_timeseries_empty,
    test_parse_wrh_timeseries_valid,
    test_parse_obhistory_html,
    test_compute_live_features_max_so_far,
    test_stale_data_flag,
    test_missing_temp,
    test_timezone_boundary,
    test_parse_obhistory_discovery,
    test_parse_obhistory_missing_table,
    test_parse_obhistory_malformed_temp,
    test_parse_obhistory_month_rollover,
    test_parse_obhistory_year_rollover,
    test_parse_normal,
    test_parse_missing,
    test_parse_trace_and_record,
    test_parse_incomplete,
    test_bin_logic,
    test_zeroing_82,
    test_zeroing_85,
    test_temp_82_maps,
    test_sum_to_one,
    test_all_bins_present,
    test_warning_missing_forecast,
    test_warning_stale_data,
    test_validate_probability_bins_logic,
    test_dry_run_v1_workflow,
    test_dry_run_v2_workflow,
    test_missing_history_v2_handling,
    test_compare_models_mode,
    test_no_trading_logic_called,
    test_settle_normal_82,
    test_settle_incomplete,
    test_full_pipeline_dry_run,
    test_unit_consistency,
    test_safety_rejections,
    test_settlement_consistency,
    test_full_pipeline_with_paper_trading,
    test_save_load_record,
    test_simulate_yes_paper_fill,
    test_simulate_no_paper_fill,
    test_settle_final_high_82,
    test_settle_no_on_bin,
    test_invalid_records_rejected,
    test_compute_simulated_pnl,
    test_load_canonical_history,
    test_historical_record_mapping,
    test_load_local_climatology_file,
    test_write_history_jsonl,
    test_bin_mapping,
    test_bin_distribution,
    test_same_day_history,
    test_prior_bin_distribution_for_date,
    test_rolling_high_average,
    test_normal_like_high,
    test_score_model_comparison_enhanced_fields,
    test_winner_and_delta_logic,
    test_tie_behavior,
    test_summary_string,
    test_report_writers,
    test_legacy_save_comparison_report,
    test_comparison_markdown_nonzero_probabilities,
    test_daily_prediction_has_model_version,
    test_daily_prediction_model_version_default,
    test_daily_prediction_model_version_v2,
    test_empty_comparison_list,
    test_basic_aggregation,
    test_missing_optional_fields,
    test_write_aggregate_json,
    test_write_aggregate_markdown,
    test_writers_handle_empty_report,
    test_empty_directories,
    test_valid_aggregate_json,
    test_log_error_status,
    test_log_warning_status,
    test_normal_ok_status,
    test_safety_trading_disabled,
    test_kalshi_client_no_auth_references,
    test_kalshi_client_mocked_discovery,
    test_kalshi_updater_logic,
    test_scripts_contain_safety_disclaimer,
    test_check_sync_status_runs,
    test_health_summary_script_exists,
    test_health_summary_is_executable,
    test_health_summary_safety_disclaimer,
    test_health_summary_no_dangerous_commands,
    test_health_summary_read_only,
    lambda: run_unittest_class(TestRulesModelV2),
    lambda: run_unittest_class(TestGenerateAggregateReport),
    lambda: run_unittest_class(TestOperationalScripts),
    lambda: run_unittest_class(TestDailyStatusCLI),
    lambda: run_unittest_class(TestDailyStatus),
    lambda: run_unittest_class(TestDeploymentAssets)
]


failed = 0
for test in tests:
    try:
        test()
        print(f"PASS: {test.__name__}")
    except Exception as e:
        print(f"FAIL: {test.__name__} - {e}")
        failed += 1

if failed > 0:
    sys.exit(1)
else:
    print("ALL TESTS PASSED.")
    sys.exit(0)
