"""Money Distribution Engine for active Kalshi bins.

This module implements paper-only position sizing, capital distribution,
and portfolio outcome evaluation based on model probabilities, market prices,
and the system's risk gates.

NO REAL TRADING EXECUTION. DRY-RUN / PAPER EVALUATION ONLY.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from trading.edge_engine import calculate_kalshi_fee, compute_edge
from risk.risk_engine import (
    check_kill_switch,
    check_weather_data_availability,
    check_weather_freshness,
    check_daily_loss_limit,
    check_weekly_drawdown_limit,
    check_market_concentration
)
from market_data.kalshi_contract_mapper import bin_string_to_range

GUARANTEE_PROFIT_FALLBACK_WARNING = (
    "Guaranteed net-positive allocation not available; "
    "showing best risk-adjusted paper allocation."
)


def _resolve_observation_time_iso(
    forecast_data: Optional[Dict[str, Any]],
    weather_gate: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Resolve latest observation time from forecast or weather gate payloads."""
    for source in (forecast_data or {}, weather_gate or {}):
        for key in (
            "latest_observation_time",
            "latest_obs_time_iso",
            "latest_obs_time",
        ):
            value = source.get(key)
            if value:
                return str(value)
    return None


def _is_contract_risk_blocked(sig: Dict[str, Any]) -> bool:
    """True when per-contract gates block paper allocation."""
    action = (sig.get("paper_action") or "").upper()
    if action in ("NO TRADE", "NO SIGNAL"):
        return True
    risk_dec = sig.get("risk_decision")
    if isinstance(risk_dec, dict):
        if risk_dec.get("decision") == "BLOCK":
            return True
        if risk_dec.get("passed") is False:
            return True
    elif risk_dec is not None and str(risk_dec).upper() == "BLOCK":
        return True
    return False


def _cost_per_contract(executable_price: float, slippage_buffer: float) -> float:
    """All-in cost to buy one YES contract (price + Kalshi fee + slippage)."""
    fee = calculate_kalshi_fee(executable_price)
    return executable_price + fee + slippage_buffer


def _fractional_kelly_fraction(
    model_prob: float,
    cost_per_contract: float,
    kelly_fraction: float,
) -> float:
    """Fractional Kelly: f = kelly_fraction * max(0, (b*p - (1-p)) / b).

    For binary Kalshi YES contracts, net odds b = (1 - cost) / cost.
    """
    if cost_per_contract <= 0.0 or cost_per_contract >= 1.0:
        return 0.0
    b = (1.0 - cost_per_contract) / cost_per_contract
    if b <= 0.0:
        return 0.0
    raw_kelly = max(0.0, (b * model_prob - (1.0 - model_prob)) / b)
    return raw_kelly * kelly_fraction


def _contract_expected_profit(
    model_prob: float,
    allocated_dollars: float,
    cost_per_contract: float,
) -> float:
    """E[PnL] = p * profit_if_wins + (1-p) * loss_if_loses."""
    if allocated_dollars <= 0.0 or cost_per_contract <= 0.0:
        return 0.0
    shares = allocated_dollars / cost_per_contract
    profit_if_wins = shares * (1.0 - cost_per_contract)
    loss_if_loses = -allocated_dollars
    return model_prob * profit_if_wins + (1.0 - model_prob) * loss_if_loses


def check_exhaustive_and_exclusive(ranges: List[Tuple[int, int]]) -> bool:
    """Checks if a list of integer ranges partitions the space [-999, 999] without gaps or overlaps."""
    if not ranges:
        return False
    # Sort ranges by low bound
    sorted_ranges = sorted(ranges, key=lambda r: r[0])
    
    # Check if first starts at -999 (or covers the lower end)
    if sorted_ranges[0][0] > -999:
        return False
    # Check if last ends at 999 (or covers the upper end)
    if sorted_ranges[-1][1] < 999:
        return False
    # Check for gaps and overlaps
    for i in range(len(sorted_ranges) - 1):
        if sorted_ranges[i][1] + 1 != sorted_ranges[i+1][0]:
            return False
    return True


def distribute_money(
    bankroll: float,
    active_signals: List[Dict[str, Any]],
    forecast_data: Dict[str, Any],
    weather_gate: Dict[str, Any],
    ledger_summary: Dict[str, Any],
    target_date: str,
    mode: str = "risk_adjusted",
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Distributes paper bankroll across active Kalshi contracts and evaluates outcomes.

    Returns a structured dictionary representing the money distribution report.
    """
    if config is None:
        config = {}

    # Extract configuration parameters with safe defaults
    kelly_fraction = config.get("kelly_fraction", 0.25)
    per_contract_cap_fraction = config.get("per_contract_cap_fraction", 0.20)
    per_market_cap_fraction = config.get("per_market_cap_fraction", 0.50)
    slippage_buffer = config.get("slippage_buffer", 0.01)
    min_executable_edge = config.get("min_executable_edge", 0.05)

    per_contract_cap = bankroll * per_contract_cap_fraction
    per_market_cap = bankroll * per_market_cap_fraction

    warnings = []
    global_blocked = False
    global_block_reason = ""

    # 1. Evaluate Global Risk Gates (Fail-Closed)
    kill_switch_res = check_kill_switch()
    if not kill_switch_res.passed:
        global_blocked = True
        global_block_reason = kill_switch_res.reason
        warnings.append(kill_switch_res.reason)

    if not global_blocked:
        weather_avail_res = check_weather_data_availability(forecast_data)
        if not weather_avail_res.passed:
            global_blocked = True
            global_block_reason = weather_avail_res.reason
            warnings.append(weather_avail_res.reason)

    if not global_blocked:
        latest_obs_time_iso = _resolve_observation_time_iso(forecast_data, weather_gate)
        weather_fresh_res = check_weather_freshness(latest_obs_time_iso)
        if not weather_fresh_res.passed:
            global_blocked = True
            global_block_reason = weather_fresh_res.reason
            warnings.append(weather_fresh_res.reason)

    if not global_blocked:
        if weather_gate and not weather_gate.get("allow_paper_recommendations", False):
            global_blocked = True
            global_block_reason = weather_gate.get("no_trade_reason") or "Blocked by weather gate."
            warnings.append(global_block_reason)

    if not global_blocked:
        daily_loss_res = check_daily_loss_limit(ledger_summary)
        if not daily_loss_res.passed:
            global_blocked = True
            global_block_reason = daily_loss_res.reason
            warnings.append(daily_loss_res.reason)

    if not global_blocked:
        weekly_drawdown_res = check_weekly_drawdown_limit(ledger_summary)
        if not weekly_drawdown_res.passed:
            global_blocked = True
            global_block_reason = weekly_drawdown_res.reason
            warnings.append(weekly_drawdown_res.reason)

    if not global_blocked:
        market_concentration_res = check_market_concentration(ledger_summary, target_date)
        if not market_concentration_res.passed:
            global_blocked = True
            global_block_reason = market_concentration_res.reason
            warnings.append(market_concentration_res.reason)

    # Reconstruct/fetch integer temperature distribution
    integer_dist = {}
    if forecast_data:
        raw_dist = forecast_data.get("integer_distribution", {})
        if raw_dist:
            integer_dist = {int(k): float(v) for k, v in raw_dist.items()}
        elif forecast_data.get("probability_bins"):
            from forecasting.distribution_utils import build_integer_distribution_from_bins
            observed_max = weather_gate.get("observed_max_so_far_f") if weather_gate else None
            res_obj = build_integer_distribution_from_bins(
                probability_bins=forecast_data["probability_bins"],
                observed_max_so_far_f=observed_max,
                station="KMIA",
                target_date=target_date
            )
            raw_int_dist = res_obj.get("integer_distribution", {})
            integer_dist = {int(k): float(v) for k, v in raw_int_dist.items()}

    if not integer_dist:
        global_blocked = True
        global_block_reason = "No forecast integer distribution available."
        warnings.append(global_block_reason)

    # 2. Pre-calculate contract costs and bounds
    costs = {}
    ranges = {}
    valid_contracts = []
    
    for sig in active_signals:
        ticker = sig["market_ticker"]
        ask = sig.get("yes_ask")
        last = sig.get("last_price")
        price = ask if ask is not None else last

        if price is None or price <= 0.0 or price >= 1.0:
            continue

        cost = _cost_per_contract(float(price), slippage_buffer)
        costs[ticker] = cost

        bin_label = sig.get("forecast_bin_label") or sig.get("contract_range")
        if bin_label:
            try:
                low, high = bin_string_to_range(bin_label)
                ranges[ticker] = (low, high)
                valid_contracts.append((ticker, cost, (low, high), sig))
            except Exception:
                pass

    # 3. Check for Dutching (Guaranteed Profit) condition
    guaranteed_profit_possible = False
    dutch_allocations = {}
    
    if not global_blocked and valid_contracts:
        covering_ranges = [r for t, c, r, s in valid_contracts]
        is_partition = check_exhaustive_and_exclusive(covering_ranges)
        sum_cost = sum(c for t, c, r, s in valid_contracts)
        
        # Dutching requires partition cover, sum cost < 1.0, and no contract blocks
        no_contract_blocked = all(
            not _is_contract_risk_blocked(s) for t, c, r, s in valid_contracts
        )
        
        if is_partition and sum_cost < 1.0 and no_contract_blocked:
            guaranteed_profit_possible = True
            # Compute total cash to allocate under caps
            min_cap_ratio = float('inf')
            for t, c, r, s in valid_contracts:
                ratio = per_contract_cap * (sum_cost / c)
                if ratio < min_cap_ratio:
                    min_cap_ratio = ratio
                    
            allocated_budget = min(bankroll, per_market_cap, min_cap_ratio)
            for t, c, r, s in valid_contracts:
                dutch_allocations[t] = allocated_budget * (c / sum_cost)

    # 4. Perform allocations based on selected mode
    allocations = {}
    reasons = {}

    if global_blocked:
        for sig in active_signals:
            allocations[sig["market_ticker"]] = 0.0
            reasons[sig["market_ticker"]] = global_block_reason
    else:
        if mode == "guarantee_profit" and guaranteed_profit_possible:
            allocations = {sig["market_ticker"]: 0.0 for sig in active_signals}
            for t, alloc in dutch_allocations.items():
                allocations[t] = alloc
            for sig in active_signals:
                ticker = sig["market_ticker"]
                if allocations[ticker] == 0.0:
                    reasons[ticker] = "Unused in dutched arbitrage cover"
        else:
            if mode == "guarantee_profit":
                warnings.append(GUARANTEE_PROFIT_FALLBACK_WARNING)

            # Risk Adjusted or Conservative modes
            positive_edge_candidates: List[Tuple[str, float]] = []
            for sig in active_signals:
                ticker = sig["market_ticker"]
                if _is_contract_risk_blocked(sig):
                    allocations[ticker] = 0.0
                    reasons[ticker] = sig.get("no_trade_reason") or "Contract failed risk gates"
                    continue

                model_prob = sig.get("model_probability")
                cost = costs.get(ticker)

                if model_prob is None or cost is None:
                    allocations[ticker] = 0.0
                    reasons[ticker] = "Missing probability or price data"
                    continue

                exec_edge = model_prob - cost
                if exec_edge < min_executable_edge:
                    allocations[ticker] = 0.0
                    reasons[ticker] = (
                        f"Insufficient executable edge ({exec_edge:.4f} < {min_executable_edge:.4f})"
                    )
                    continue

                positive_edge_candidates.append((ticker, exec_edge))

            max_edge = (
                max(e for _, e in positive_edge_candidates)
                if positive_edge_candidates
                else 0.0
            )

            for sig in active_signals:
                ticker = sig["market_ticker"]
                if ticker in reasons or allocations.get(ticker, 0.0) != 0.0:
                    continue
                if ticker not in costs:
                    continue

                model_prob = float(sig.get("model_probability", 0.0))
                cost = costs[ticker]
                exec_edge = model_prob - cost

                if mode == "conservative":
                    if 0.40 <= model_prob <= 0.60:
                        allocations[ticker] = 0.0
                        reasons[ticker] = "High uncertainty under conservative mode"
                        continue
                    if abs(exec_edge - max_edge) > 1e-5:
                        allocations[ticker] = 0.0
                        reasons[ticker] = "Non-optimal edge under conservative mode"
                        continue
                    kelly_alloc = bankroll * _fractional_kelly_fraction(
                        model_prob, cost, kelly_fraction=0.10
                    )
                    allocations[ticker] = min(kelly_alloc, bankroll * 0.10)
                else:
                    kelly_alloc = bankroll * _fractional_kelly_fraction(
                        model_prob, cost, kelly_fraction=kelly_fraction
                    )
                    allocations[ticker] = min(kelly_alloc, per_contract_cap)

            # Enforce total market cap (portfolio-level cap scaling)
            total_alloc = sum(allocations.values())
            if total_alloc > per_market_cap:
                scale = per_market_cap / total_alloc
                for ticker in allocations:
                    allocations[ticker] = round(allocations[ticker] * scale, 4)

    # 5. Evaluate Portfolio PnL by Outcome over integer temperature outcomes
    prob_temps = [t for t in integer_dist if integer_dist[t] > 0]
    contract_temps = []
    for ticker, cost, (low, high), sig in valid_contracts:
        if low != -999:
            contract_temps.append(low)
        if high != 999:
            contract_temps.append(high)

    min_eval = min(prob_temps + contract_temps) - 5 if (prob_temps or contract_temps) else 50
    max_eval = max(prob_temps + contract_temps) + 5 if (prob_temps or contract_temps) else 120

    total_cost_portfolio = sum(allocations.values())
    pnl_by_temp = {}
    
    # Calculate shares for each allocated contract
    shares = {}
    for ticker, cost, (low, high), sig in valid_contracts:
        alloc = allocations.get(ticker, 0.0)
        shares[ticker] = alloc / cost if cost > 0 else 0.0

    # Evaluate outcomes for each integer temperature
    for t in range(min_eval, max_eval + 1):
        payoff = 0.0
        for ticker, cost, (low, high), sig in valid_contracts:
            if low <= t <= high:
                payoff += shares[ticker]
        pnl_by_temp[t] = payoff - total_cost_portfolio

    # Portfolio metrics
    worst_case_profit = min(pnl_by_temp.values()) if pnl_by_temp else 0.0
    best_case_profit = max(pnl_by_temp.values()) if pnl_by_temp else 0.0

    # Confirm dutching guarantee only when every integer outcome is net positive
    if (
        mode == "guarantee_profit"
        and guaranteed_profit_possible
        and pnl_by_temp
    ):
        guaranteed_profit_possible = worst_case_profit > 0.0001
        if not guaranteed_profit_possible:
            warnings.append(GUARANTEE_PROFIT_FALLBACK_WARNING)
    
    portfolio_expected_profit = 0.0
    probability_of_profit = 0.0
    for t, pnl in pnl_by_temp.items():
        prob = integer_dist.get(t, 0.0)
        portfolio_expected_profit += pnl * prob
        if pnl > 0.0001:
            probability_of_profit += prob

    # Format pnl_by_outcome per active contract bin
    pnl_by_outcome = []
    uncovered_temps = []
    
    for ticker, cost, (low, high), sig in valid_contracts:
        bin_label = sig.get("forecast_bin_label") or sig.get("contract_range")
        bin_temps = [t for t in range(low, high + 1) if min_eval <= t <= max_eval]
        bin_prob = sum(integer_dist.get(t, 0.0) for t in bin_temps)
        
        # Calculate expected payout if temperature lands in this bin
        if bin_prob > 0:
            avg_payout = sum((sum(shares[tk] for tk, c_c, (l_l, h_h), s_s in valid_contracts if l_l <= t <= h_h)) * integer_dist.get(t, 0.0) for t in bin_temps) / bin_prob
        else:
            mid = (low + high) // 2 if (low != -999 and high != 999) else (low if low != -999 else high)
            avg_payout = sum(shares[tk] for tk, c_c, (l_l, h_h), s_s in valid_contracts if l_l <= mid <= h_h)
            
        pnl_by_outcome.append({
            "outcome_bin": bin_label,
            "probability": round(bin_prob, 4),
            "payout": round(avg_payout, 4),
            "total_cost": round(total_cost_portfolio, 4),
            "net_pnl": round(avg_payout - total_cost_portfolio, 4)
        })

    # Detect if any temperatures are uncovered
    for t in range(min_eval, max_eval + 1):
        covered = False
        for ticker, cost, (low, high), sig in valid_contracts:
            if low <= t <= high:
                covered = True
                break
        if not covered:
            uncovered_temps.append(t)

    if uncovered_temps:
        uncovered_prob = sum(integer_dist.get(t, 0.0) for t in uncovered_temps)
        pnl_by_outcome.append({
            "outcome_bin": "uncovered",
            "probability": round(uncovered_prob, 4),
            "payout": 0.0,
            "total_cost": round(total_cost_portfolio, 4),
            "net_pnl": round(-total_cost_portfolio, 4)
        })

    # 6. Build the rows payload for each active signal
    rows = []
    for sig in active_signals:
        ticker = sig["market_ticker"]
        alloc = allocations.get(ticker, 0.0)
        cost = costs.get(ticker, 0.0)
        
        model_prob = sig.get("model_probability")
        rows.append({
            "contract_ticker": ticker,
            "bin_range": sig.get("forecast_bin_label") or sig.get("contract_range") or "unknown",
            "model_probability": model_prob,
            "market_probability": sig.get("market_probability"),
            "executable_price": sig.get("executable_price") or sig.get("yes_ask"),
            "executable_edge": (
                (model_prob - cost) if model_prob is not None and cost else sig.get("executable_edge")
            ),
            "recommended_allocation_dollars": round(alloc, 4),
            "estimated_contracts": int(alloc / cost) if cost > 0 else 0,
            "expected_profit": round(
                _contract_expected_profit(float(model_prob or 0.0), alloc, cost), 4
            ) if cost > 0 and model_prob is not None else 0.0,
            "max_loss": round(alloc, 4),
            "no_trade_reason": reasons.get(ticker),
        })

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "market_date": target_date,
        "total_available_dollars": bankroll,
        "allocation_mode": mode if (mode != "guarantee_profit" or guaranteed_profit_possible) else f"{mode}_fallback_risk_adjusted",
        "guaranteed_profit_possible": guaranteed_profit_possible,
        "portfolio_expected_profit": round(portfolio_expected_profit, 4),
        "probability_of_profit": round(probability_of_profit, 4),
        "worst_case_profit": round(worst_case_profit, 4),
        "best_case_profit": round(best_case_profit, 4),
        "total_allocated": round(total_cost_portfolio, 4),
        "cash_unallocated": round(bankroll - total_cost_portfolio, 4),
        "rows": rows,
        "pnl_by_outcome": pnl_by_outcome,
        "warnings": list(set(warnings)),
        "safety": {
            "no_real_trading": True,
            "no_order_execution": True,
            "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY"
        }
    }
