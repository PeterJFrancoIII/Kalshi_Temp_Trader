"use client";

import useSWR from "swr";
import type {
  ApiResponse,
  DailyStatus,
  WeatherData,
  MarketSnapshot,
  OrderbooksSnapshot,
  PaperSignal,
  PaperLedger,
  ForecastDistribution,
  CalibrationData,
} from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const DEFAULT_REFRESH_INTERVAL = 30000; // 30 seconds

export function useStatus() {
  return useSWR<ApiResponse<DailyStatus>>("/api/status", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useWeather() {
  return useSWR<ApiResponse<WeatherData>>("/api/weather", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useMarkets() {
  return useSWR<ApiResponse<MarketSnapshot>>("/api/markets", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useOrderbooks() {
  return useSWR<ApiResponse<OrderbooksSnapshot>>("/api/orderbooks", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useSignals() {
  return useSWR<ApiResponse<PaperSignal>>("/api/signals", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useLedger() {
  return useSWR<ApiResponse<PaperLedger>>("/api/ledger", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useForecast() {
  return useSWR<ApiResponse<ForecastDistribution>>("/api/forecast", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}

export function useCalibration() {
  return useSWR<ApiResponse<CalibrationData>>("/api/calibration", fetcher, {
    refreshInterval: DEFAULT_REFRESH_INTERVAL,
  });
}
