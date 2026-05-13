"use client";

import { Thermometer, Droplets, Wind, Eye, Clock, AlertTriangle, MapPin } from "lucide-react";
import { useWeather, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp } from "@/lib/utils";

export default function WeatherPage() {
  const { data: weatherData, isLoading: weatherLoading } = useWeather();
  const { data: statusData } = useStatus();

  const weather = weatherData?.data;
  const status = statusData?.data;
  const weatherStatus = status?.weather;

  if (weatherLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading weather data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Weather Data</h1>
          <p className="text-muted-foreground">
            NWS KMIA Station Observations
          </p>
        </div>
        <StatusBadge status={weatherStatus?.status ?? "UNKNOWN"} size="lg" />
      </div>

      {/* Errors/Warnings */}
      {weatherStatus?.errors && weatherStatus.errors.length > 0 && (
        <div className="rounded-lg border border-status-blocked/30 bg-status-blocked/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-blocked" />
            <div>
              <h3 className="font-medium text-status-blocked">Weather Errors</h3>
              <ul className="mt-1 space-y-1">
                {weatherStatus.errors.map((error, i) => (
                  <li key={i} className="text-sm text-status-blocked/80">
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Missing Data Warning */}
      {weatherData?.missing && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Data Unavailable</h3>
              <p className="text-sm text-status-watch/80">
                {weatherData.error || "Weather data file not found. The backend may not have run yet."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Station Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            <CardTitle>Station Information</CardTitle>
          </div>
          <CardDescription>Miami International Airport (KMIA)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Station ID</div>
              <div className="font-medium text-foreground">
                {weather?.station_id ?? "KMIA"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Data Source</div>
              <div className="font-medium text-foreground">
                {weatherStatus?.source ?? "National Weather Service"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Last Update</div>
              <div className="font-medium text-foreground">
                {formatTimestamp(weatherStatus?.last_update ?? weather?.timestamp)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <StatusBadge status={weatherStatus?.status ?? "UNKNOWN"} size="sm" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Current Conditions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Temperature */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Thermometer className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Temperature</div>
                <div className="text-2xl font-bold text-foreground">
                  {weather?.temperature_f != null ? `${weather.temperature_f}°F` : "N/A"}
                </div>
                {weather?.temperature_c != null && (
                  <div className="text-sm text-muted-foreground">
                    {weather.temperature_c}°C
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Humidity */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/10">
                <Droplets className="h-6 w-6 text-blue-500" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Humidity</div>
                <div className="text-2xl font-bold text-foreground">
                  {weather?.humidity_percent != null ? `${weather.humidity_percent}%` : "N/A"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Wind */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-teal-500/10">
                <Wind className="h-6 w-6 text-teal-500" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Wind</div>
                <div className="text-2xl font-bold text-foreground">
                  {weather?.wind_speed_mph != null ? `${weather.wind_speed_mph} mph` : "N/A"}
                </div>
                {weather?.wind_direction && (
                  <div className="text-sm text-muted-foreground">
                    {weather.wind_direction}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Conditions */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-500/10">
                <Eye className="h-6 w-6 text-amber-500" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Conditions</div>
                <div className="text-lg font-bold text-foreground">
                  {weather?.conditions ?? "N/A"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Freshness */}
      <FreshnessCard
        title="Weather Data Freshness"
        description="Time since last NWS observation update"
        timestamp={weatherStatus?.last_update ?? weather?.timestamp}
        thresholds={{ fresh: 30 * 60 * 1000, stale: 60 * 60 * 1000 }} // 30min fresh, 1hr stale
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>Weather data should update every 30-60 minutes from NWS</span>
        </div>
      </FreshnessCard>

      {/* Raw Observation Data */}
      {weather?.raw_observation && Object.keys(weather.raw_observation).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Raw Observation Data</CardTitle>
            <CardDescription>
              Complete observation record from NWS API
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto rounded-lg bg-muted p-4">
              <pre className="font-mono text-xs text-muted-foreground">
                {JSON.stringify(weather.raw_observation, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
