import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return "N/A";
  try {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return timestamp;
  }
}

export function getTimestampAge(timestamp: string | null | undefined): number | null {
  if (!timestamp) return null;
  try {
    const date = new Date(timestamp);
    return Date.now() - date.getTime();
  } catch {
    return null;
  }
}

export function getFreshnessStatus(
  ageMs: number | null,
  thresholds: { fresh: number; stale: number }
): "fresh" | "warning" | "stale" | "unknown" {
  if (ageMs === null) return "unknown";
  if (ageMs < thresholds.fresh) return "fresh";
  if (ageMs < thresholds.stale) return "warning";
  return "stale";
}

export function formatCurrency(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}
