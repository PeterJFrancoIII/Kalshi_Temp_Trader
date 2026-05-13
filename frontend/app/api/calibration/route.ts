import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const BACKEND_DATA_PATH = process.env.BACKEND_DATA_PATH || path.join(process.cwd(), "..", "backend", "data", "processed");

export async function GET() {
  try {
    const calibrationFile = path.join(BACKEND_DATA_PATH, "aggregate_calibration", "aggregate_calibration.json");
    
    try {
      await fs.access(calibrationFile);
    } catch {
      return NextResponse.json({
        data: null,
        error: "Calibration file not found",
        missing: true,
        timestamp: new Date().toISOString(),
      });
    }

    const content = await fs.readFile(calibrationFile, "utf-8");
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
