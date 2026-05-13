import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const BACKEND_DATA_PATH = process.env.BACKEND_DATA_PATH || path.join(process.cwd(), "..", "backend", "data", "processed");

async function getLatestForecastFile(): Promise<string | null> {
  const forecastDir = path.join(BACKEND_DATA_PATH, "forecasts");
  
  try {
    const files = await fs.readdir(forecastDir);
    const forecastFiles = files
      .filter((f) => f.startsWith("kmia_forecast_") && f.endsWith(".json"))
      .sort()
      .reverse();
    
    if (forecastFiles.length === 0) return null;
    return path.join(forecastDir, forecastFiles[0]);
  } catch {
    return null;
  }
}

export async function GET() {
  try {
    const forecastFile = await getLatestForecastFile();
    
    if (!forecastFile) {
      return NextResponse.json({
        data: null,
        error: "No forecast file found",
        missing: true,
        timestamp: new Date().toISOString(),
      });
    }

    const content = await fs.readFile(forecastFile, "utf-8");
    const data = JSON.parse(content);

    return NextResponse.json({
      data,
      error: null,
      missing: false,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json({
      data: null,
      error: error instanceof Error ? error.message : "Unknown error",
      missing: true,
      timestamp: new Date().toISOString(),
    });
  }
}
