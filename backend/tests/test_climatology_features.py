from features.climatology_features import (
    temp_to_required_bin,
    bin_distribution,
    same_day_history,
    prior_bin_distribution_for_date,
    rolling_high_average,
    normal_like_high_for_date
)

def get_mock_records():
    return [
        {"station": "USW00012839", "date": "2023-05-01", "tmax_f": 82},
        {"station": "USW00012839", "date": "2023-05-02", "tmax_f": 84},
        {"station": "USW00012839", "date": "2023-05-03", "tmax_f": 85},
        {"station": "USW00012839", "date": "2022-05-01", "tmax_f": 81},
        {"station": "USW00012839", "date": "2022-05-02", "tmax_f": 83},
        {"station": "USW00012839", "date": "2022-05-03", "tmax_f": 84},
        {"station": "USW00012839", "date": "2023-04-30", "tmax_f": 80},
        {"station": "USW00012839", "date": "2023-05-04", "tmax_f": 86},
        {"station": "USW00012839", "date": "2024-05-01", "tmax_f": 90}, # Target year record
    ]

def test_bin_mapping():
    assert temp_to_required_bin(82) == "81-82"
    assert temp_to_required_bin(78) == "<=78"
    assert temp_to_required_bin(87) == ">=87"
    print("test_bin_mapping PASSED")

def test_bin_distribution():
    records = [{"tmax_f": 82}, {"tmax_f": 84}, {"tmax_f": 85}]
    dist = bin_distribution(records)
    assert dist["81-82"] == 0.3333
    assert dist["83-84"] == 0.3333
    assert dist["85-86"] == 0.3333
    assert sum(dist.values()) == 0.9999
    print("test_bin_distribution PASSED")

def test_same_day_history():
    records = get_mock_records()
    results = same_day_history(records, "2024-05-01")
    # Should match May 1 for 2023 and 2022. 2024 is same year but handled by > target.year logic in function?
    # Wait, my function does year < target.year
    assert len(results) == 2
    assert results[0]["date"] == "2023-05-01"
    assert results[1]["date"] == "2022-05-01"
    print("test_same_day_history PASSED")

def test_prior_bin_distribution_for_date():
    records = get_mock_records()
    # Exact date, no window
    dist = prior_bin_distribution_for_date(records, "2024-05-01", window_days=0)
    # Matches: 2023-05-01 (82), 2022-05-01 (81) -> Both are 81-82
    assert dist["81-82"] == 1.0
    
    # With window ±1 day
    # Target: May 1. Window: Apr 30, May 1, May 2
    # Records: 2023-04-30 (80), 2023-05-01 (82), 2023-05-02 (84), 2022-05-01 (81), 2022-05-02 (83)
    # Bins: 79-80 (1), 81-82 (2), 83-84 (2) -> Total 5
    dist_w = prior_bin_distribution_for_date(records, "2024-05-01", window_days=1)
    assert dist_w["79-80"] == 0.2
    assert dist_w["81-82"] == 0.4
    assert dist_w["83-84"] == 0.4
    print("test_prior_bin_distribution_for_date PASSED")

def test_rolling_high_average():
    records = get_mock_records()
    # Rolling avg for 2023-05-03 with window 2 days (matches May 1, May 2 2023)
    avg = rolling_high_average(records, "2023-05-03", window_days=2)
    assert avg == (82 + 84) / 2
    print("test_rolling_high_average PASSED")

def test_normal_like_high():
    records = get_mock_records()
    # Normal high for May 1, window 1 day, years_back=2
    # Records: 2023-04-30, 2023-05-01, 2023-05-02, 2022-05-01, 2022-05-02
    # Temps: 80, 82, 84, 81, 83
    # Avg: (80+82+84+81+83)/5 = 410/5 = 82
    norm = normal_like_high_for_date(records, "2024-05-01", window_days=1, years_back=2)
    assert norm == 82.0
    print("test_normal_like_high PASSED")

if __name__ == "__main__":
    test_bin_mapping()
    test_bin_distribution()
    test_same_day_history()
    test_prior_bin_distribution_for_date()
    test_rolling_high_average()
    test_normal_like_high()
