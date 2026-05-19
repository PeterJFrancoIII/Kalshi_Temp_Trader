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

from test_paper_signal_generator import TestPaperSignalGenerator
from test_update_kalshi_snapshots import TestUpdateKalshiSnapshots
from test_artifact_paths import TestArtifactPaths
from test_feature_flags import TestLLMReviewFlag
from test_jsonl_store import TestJSONLStore
from test_refactor_invariants import (
    test_required_bins_defined_only_in_shared_types,
    test_canonical_bins_match_mvp_lockdown,
    test_no_src_dot_imports_in_backend_src,
    test_no_src_dot_imports_in_backend_tests,
    test_no_sys_path_insert_in_backend_src,
    test_single_kalshi_public_client_definition,
    test_no_paper_trade_ledger_jsonl_reference_in_paper_trading,
    test_single_kalshi_fee_formula_definition,
    test_orm_models_use_record_suffix,
    test_render_functions_live_under_console_pages_only,
)
from test_pipeline_inputs import (
    test_climatological_defaults_match_documented_values,
    test_build_dry_run_features_missing_snapshot_returns_defaults,
    test_build_dry_run_features_with_obs_and_forecast,
    test_build_dry_run_features_no_obs_for_target_date_marks_stale,
    test_thunderstorm_severity_classification,
    test_derive_weather_flags_overcast_partly_cloudy_distinction,
)
from test_calibration_metrics import (
    test_temp_to_bin_logic,
    test_top_bin_logic,
    test_score_prediction_hits,
    test_brier_score_reasonable,
    test_log_loss_finite_and_clipping,
    test_invalid_probabilities_errors,
    test_may_3_2026_specific_case,
    # P2 — reliability diagram, lead-time bucketing, multi-source comparison
    test_reliability_bins_empty,
    test_reliability_bins_basic_structure,
    test_reliability_bins_perfect_calibration,
    test_reliability_bins_total_count_matches_input,
    test_score_prediction_without_lead_time,
    test_score_prediction_with_lead_time,
    test_aggregate_stats_by_lead_time_basic,
    test_aggregate_stats_by_lead_time_unknown_bucket,
    test_score_multi_source_returns_all_sources,
    test_score_multi_source_better_source_has_lower_brier,
    test_score_multi_source_with_lead_time,
    test_score_multi_source_empty_sources,
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
    test_kalshi_updater_logic,
    test_kalshi_config_exists,
    test_kalshi_client_broad_discovery,
    test_kalshi_snapshot_safety_fields,
    test_kalshi_manual_ticker_lookup,
    test_kalshi_manual_series_lookup
)

from test_sync_tooling import (
    test_scripts_contain_safety_disclaimer,
    test_check_sync_status_runs
)

from test_web_console_logic import (
    test_load_latest_forecast_summary_parsing,
    test_load_latest_forecast_summary_missing,
    test_load_latest_forecast_summary_string_path,
    test_extract_best_signal,
    test_aggregate_warnings,
    test_derive_orderbook_prices,
    test_calculate_hypothetical_costs,
    test_extract_market_rows,
    test_format_probability,
    test_format_temp,
    test_format_num,
    test_extract_market_rows_logic,
    test_dataframe_config_logic,
    test_render_weather_nws_formatting_handles_none
)

from test_weather_ingestion import (
    test_weather_status_serialization,
    test_stale_data_flag,
    test_observed_max_so_far,
    test_history_record_count
)

from test_paper_ledger import TestPaperLedger
from test_risk_engine import TestRiskEngine
from test_edge_engine import TestEdgeEngine

from test_health_summary import (
    test_health_summary_script_exists,
    test_health_summary_is_executable,
    test_health_summary_safety_disclaimer,
    test_health_summary_no_dangerous_commands,
    test_health_summary_read_only
)

from test_paper_settlement import TestPaperSettlement
from test_paper_learning import TestPaperLearning

from test_manual_corrections import (
    test_load_manual_corrections,
    test_is_excluded_from_learning,
    test_get_market_open_time_et,
    test_missing_file_fails_safely,
    test_invalid_json_fails_safely,
    test_get_correction_for_date as test_get_correction
)

from test_nws_live_client import (
    test_conversions,
    test_wind_conversions,
    test_compass_conversion,
    test_cloud_parsing,
    test_date_time_formatting,
    test_build_live_nws_snapshot_enhanced,
    test_stale_data_detection,
    test_missing_fields_no_crash
)

from test_kalshi_contract_mapper import TestKalshiContractMapper
from test_kalshi_public_client import TestKalshiPublicClient
from test_paper_signal_enhanced import TestPaperSignalEnhanced
from test_distribution_utils import TestDistributionUtils
from test_weather_providers_page import (
    test_normalize_time_utc_for_merge,
    test_build_matched_table_with_mixed_resolutions,
    test_build_matched_table_empty_input,
    test_extract_nws_observed_rows_finds_recent_observations_table,
    test_extract_nws_forecast_rows_finds_hourly_forecast,
    test_normalize_nws_forecast_returns_nws_forecast_dataframe,
    test_normalize_twc_forecast_returns_twc_forecast_dataframe,
    test_build_matched_table_returns_nearest_forecasts,
    test_build_observed_match_returns_forecast_error_rows
)

from test_contract_probability_mapper import TestContractProbabilityMapper
from test_kmia_distribution_blender import TestKMIADistributionBlender
from test_kmia_observation_bias_corrector import TestKmiaObservationBiasCorrector
from test_twc_daily_max_distribution import TestTWCDailyMaxDistribution
from test_twc_probabilistic_client import TestTWCProbabilisticClient
from test_twc_kmia_client import (
    test_normalize_current_handles_missing_input,
    test_normalize_current_maps_common_twc_fields,
    test_normalize_daily_handles_list_payload,
    test_normalize_hourly_handles_list_payload,
    test_derive_features_returns_expected_fields,
    test_normalize_bundle_preserves_safety_and_missing_hourly_flag,
    test_normalize_current_does_not_use_expire_time_as_observation,
    test_normalize_current_observation_time_from_valid_fields,
)

from test_risk_integration import (
    TestTempSatisfiesBinLabel,
    TestLoadTradesFromLedger,
    TestSettlementWithJsonLedger,
    TestPnLWriteback,
    TestGate2WeatherFreshness,
    TestDynamicBinSettlement,
    TestRiskEndToEnd,
)

from test_backtest_coordinator import (
    test_backtest_coordinator_initialization,
    test_backtest_missing_data_handling,
    test_extract_embedded_timestamp_fetched_at_utc,
    test_extract_embedded_timestamp_generated_at_utc,
    test_extract_embedded_timestamp_timestamp_field,
    test_extract_embedded_timestamp_missing_returns_none,
    test_extract_embedded_timestamp_invalid_value_returns_none,
    test_extract_embedded_timestamp_bad_file_returns_none,
    test_select_snapshot_as_of_basic,
    test_select_snapshot_as_of_all_future_returns_none,
    test_snapshot_selection_uses_embedded_ts_not_mtime,
    test_snapshot_with_missing_embedded_ts_is_excluded,
    test_snapshot_directory_with_only_no_ts_files_returns_none,
    test_settlement_blocked_before_settlement_as_of_time,
    test_settlement_blocked_next_day_before_06_utc,
    test_settlement_proceeds_after_settlement_as_of_time,
    test_record_trade_stores_model_probability_and_forecast_bin,
    test_record_trade_without_optional_fields,
    test_backtest_coordinator_as_of_times_are_premarket,
    # Phase 9 P1 — SnapshotRegistry + replay manifest
    test_snapshot_registry_resolve_basic,
    test_snapshot_registry_resolve_unknown_type_returns_none,
    test_snapshot_registry_caches_results,
    test_snapshot_registry_lookup_log_populated,
    test_backtest_coordinator_has_registry,
    test_replay_manifest_written_after_run_backtest,
    test_replay_manifest_schema,
    test_signal_generator_uses_embedded_ts_not_mtime,
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
    # Phase 9 P2 — calibration metrics: reliability diagram, lead-time, multi-source
    test_reliability_bins_empty,
    test_reliability_bins_basic_structure,
    test_reliability_bins_perfect_calibration,
    test_reliability_bins_total_count_matches_input,
    test_score_prediction_without_lead_time,
    test_score_prediction_with_lead_time,
    test_aggregate_stats_by_lead_time_basic,
    test_aggregate_stats_by_lead_time_unknown_bucket,
    test_score_multi_source_returns_all_sources,
    test_score_multi_source_better_source_has_lower_brier,
    test_score_multi_source_with_lead_time,
    test_score_multi_source_empty_sources,
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
    test_kalshi_config_exists,
    test_kalshi_client_broad_discovery,
    test_kalshi_snapshot_safety_fields,
    test_kalshi_manual_ticker_lookup,
    test_kalshi_manual_series_lookup,
    test_load_latest_forecast_summary_parsing,
    test_load_latest_forecast_summary_missing,
    test_load_latest_forecast_summary_string_path,
    test_extract_best_signal,
    test_aggregate_warnings,
    test_derive_orderbook_prices,
    test_calculate_hypothetical_costs,
    test_extract_market_rows,
    test_format_probability,
    test_format_temp,
    test_format_num,
    test_extract_market_rows_logic,
    test_dataframe_config_logic,
    test_render_weather_nws_formatting_handles_none,
    test_weather_status_serialization,
    test_stale_data_flag,
    test_observed_max_so_far,
    test_history_record_count,
    lambda: run_unittest_class(TestPaperLedger),
    lambda: run_unittest_class(TestRiskEngine),
    lambda: run_unittest_class(TestEdgeEngine),
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
    lambda: run_unittest_class(TestDeploymentAssets),
    lambda: run_unittest_class(TestPaperSettlement),
    lambda: run_unittest_class(TestPaperLearning),
    test_load_manual_corrections,
    test_is_excluded_from_learning,
    test_get_market_open_time_et,
    test_missing_file_fails_safely,
    test_invalid_json_fails_safely,
    test_get_correction,
    test_conversions,
    test_wind_conversions,
    test_compass_conversion,
    test_cloud_parsing,
    test_date_time_formatting,
    test_build_live_nws_snapshot_enhanced,
    test_stale_data_detection,
    test_missing_fields_no_crash,
    lambda: run_unittest_class(TestKalshiContractMapper),
    lambda: run_unittest_class(TestPaperSignalEnhanced),
    test_normalize_time_utc_for_merge,
    test_build_matched_table_with_mixed_resolutions,
    test_build_matched_table_empty_input,
    test_extract_nws_observed_rows_finds_recent_observations_table,
    test_extract_nws_forecast_rows_finds_hourly_forecast,
    test_normalize_nws_forecast_returns_nws_forecast_dataframe,
    test_normalize_twc_forecast_returns_twc_forecast_dataframe,
    test_build_matched_table_returns_nearest_forecasts,
    test_build_observed_match_returns_forecast_error_rows,
    lambda: run_unittest_class(TestKalshiPublicClient),
    lambda: run_unittest_class(TestPaperSignalGenerator),
    lambda: run_unittest_class(TestUpdateKalshiSnapshots),
    lambda: run_unittest_class(TestArtifactPaths),
    # Phase 3 guardrails — feature flags + JSONLStore locking
    lambda: run_unittest_class(TestLLMReviewFlag),
    lambda: run_unittest_class(TestJSONLStore),
    # Phase 9 P0 lookahead-safety tests
    test_backtest_coordinator_initialization,
    test_backtest_missing_data_handling,
    test_extract_embedded_timestamp_fetched_at_utc,
    test_extract_embedded_timestamp_generated_at_utc,
    test_extract_embedded_timestamp_timestamp_field,
    test_extract_embedded_timestamp_missing_returns_none,
    test_extract_embedded_timestamp_invalid_value_returns_none,
    test_extract_embedded_timestamp_bad_file_returns_none,
    test_select_snapshot_as_of_basic,
    test_select_snapshot_as_of_all_future_returns_none,
    test_snapshot_selection_uses_embedded_ts_not_mtime,
    test_snapshot_with_missing_embedded_ts_is_excluded,
    test_snapshot_directory_with_only_no_ts_files_returns_none,
    test_settlement_blocked_before_settlement_as_of_time,
    test_settlement_blocked_next_day_before_06_utc,
    test_settlement_proceeds_after_settlement_as_of_time,
    test_record_trade_stores_model_probability_and_forecast_bin,
    test_record_trade_without_optional_fields,
    test_backtest_coordinator_as_of_times_are_premarket,
    # Phase 9 P1 — SnapshotRegistry + replay manifest
    test_snapshot_registry_resolve_basic,
    test_snapshot_registry_resolve_unknown_type_returns_none,
    test_snapshot_registry_caches_results,
    test_snapshot_registry_lookup_log_populated,
    test_backtest_coordinator_has_registry,
    test_replay_manifest_written_after_run_backtest,
    test_replay_manifest_schema,
    test_signal_generator_uses_embedded_ts_not_mtime,
    # F1-F4/F6 Risk critical defect fixes
    lambda: run_unittest_class(TestTempSatisfiesBinLabel),
    lambda: run_unittest_class(TestLoadTradesFromLedger),
    lambda: run_unittest_class(TestSettlementWithJsonLedger),
    lambda: run_unittest_class(TestPnLWriteback),
    lambda: run_unittest_class(TestGate2WeatherFreshness),
    lambda: run_unittest_class(TestDynamicBinSettlement),
    lambda: run_unittest_class(TestRiskEndToEnd),
    # Phase 2–6 forecast/ingestion pipeline tests (integer distribution layer)
    lambda: run_unittest_class(TestContractProbabilityMapper),
    lambda: run_unittest_class(TestKMIADistributionBlender),
    lambda: run_unittest_class(TestKmiaObservationBiasCorrector),
    lambda: run_unittest_class(TestTWCDailyMaxDistribution),
    lambda: run_unittest_class(TestTWCProbabilisticClient),
    lambda: run_unittest_class(TestDistributionUtils),
    # TWC KMIA client — weather data normalization correctness
    test_normalize_current_handles_missing_input,
    test_normalize_current_maps_common_twc_fields,
    test_normalize_daily_handles_list_payload,
    test_normalize_hourly_handles_list_payload,
    test_derive_features_returns_expected_fields,
    test_normalize_bundle_preserves_safety_and_missing_hourly_flag,
    test_normalize_current_does_not_use_expire_time_as_observation,
    test_normalize_current_observation_time_from_valid_fields,
    # Phase 0 refactor guardrails
    test_required_bins_defined_only_in_shared_types,
    test_canonical_bins_match_mvp_lockdown,
    # Phase 1 refactor guardrails
    test_no_src_dot_imports_in_backend_src,
    test_no_src_dot_imports_in_backend_tests,
    test_no_sys_path_insert_in_backend_src,
    # Phase 2 refactor guardrails
    test_single_kalshi_public_client_definition,
    test_no_paper_trade_ledger_jsonl_reference_in_paper_trading,
    test_single_kalshi_fee_formula_definition,
    test_orm_models_use_record_suffix,
    test_render_functions_live_under_console_pages_only,
    # Phase 2.5 — features.pipeline_inputs extraction characterization
    test_climatological_defaults_match_documented_values,
    test_build_dry_run_features_missing_snapshot_returns_defaults,
    test_build_dry_run_features_with_obs_and_forecast,
    test_build_dry_run_features_no_obs_for_target_date_marks_stale,
    test_thunderstorm_severity_classification,
    test_derive_weather_flags_overcast_partly_cloudy_distinction,
]


def _run_all_tests():
    """Execute every registered test, printing PASS/FAIL per item.

    Lives inside a function so that ``multiprocessing`` workers, which
    re-import this module under the ``spawn`` start method, do not
    re-run the whole suite when a test launches a subprocess. The
    ``if __name__ == "__main__"`` guard below is the matching idiom.
    """
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"FAIL: {test.__name__} - {e}")
            failed += 1

    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    _run_all_tests()
