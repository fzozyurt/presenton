import { NextResponse } from "next/server";
import { getFastApiBaseUrl } from "@/lib/fastapi-internal";

export async function POST(request: Request) {
  try {
    const { filePath } = await request.json();
    if (!filePath || typeof filePath !== "string") {
      return NextResponse.json({ error: "Missing filePath" }, { status: 400 });
    }

    const base = getFastApiBaseUrl();
    const res = await fetch(
      `${base}/api/v1/ppt/files/read?path=${encodeURIComponent(filePath)}`,
      { method: "GET", cache: "no-store" },
    );

    if (!res.ok) {
      const detail = await res.text();
      return NextResponse.json({ error: detail || "Failed to read file" }, { status: res.status });
    }

    const content = await res.text();
    return NextResponse.json({ content });
  } catch (error) {
    console.error("Error reading file:", error);
    return NextResponse.json({ error: "Failed to read file" }, { status: 500 });
  }
}