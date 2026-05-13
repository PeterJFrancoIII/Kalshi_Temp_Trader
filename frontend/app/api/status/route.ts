import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const BACKEND_DATA_PATH = process.env.BACKEND_DATA_PATH || path.join(process.cwd(), "..", "backend", "data", "processed");

async function getLatestStatusFile(): Promise<string | null> {
  const statusDir = path.join(BACKEND_DATA_PATH, "status");
  
  try {
    const files = await fs.readdir(statusDir);
    const statusFiles = files
      .filter((f) => f.startsWith("kmia_daily_status_") && f.endsWith(".json"))
      .sort()
      .reverse();
    
    if (statusFiles.length === 0) return null;
    return path.join(statusDir, statusFiles[0]);
  } catch {
    return null;
  }
}

export async function GET() {
  try {
    const statusFile = await getLatestStatusFile();
    
    if (!statusFile) {
      return NextResponse.json({
        data: null,
        error: "No status file found",
        missing: true,
        timestamp: new Date().toISOString(),
      });
    }

    const content = await fs.readFile(statusFile, "utf-8");
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
