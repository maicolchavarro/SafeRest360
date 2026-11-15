"use client";

import { useRef, useState, useEffect, useCallback, type MouseEvent } from "react";
import type { PolygonPoint } from "@/lib/types";
import { TONE_COLORS, type ZoneBadge } from "@/lib/zone-state";

function drawLabel(ctx: CanvasRenderingContext2D, cx: number, cy: number, title: string, detail: string | undefined, accent: string) {
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "bold 13px sans-serif";
  const titleW = ctx.measureText(title).width;
  ctx.font = "12px sans-serif";
  const detailW = detail ? ctx.measureText(detail).width : 0;
  const w = Math.max(titleW, detailW) + 20;
  const h = detail ? 40 : 24;
  const x = cx - w / 2;
  const y = cy - h / 2;

  ctx.fillStyle = "rgba(17, 24, 39, 0.82)";
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 6);
  ctx.fill();
  ctx.fillStyle = accent;
  ctx.fillRect(x, y + 4, 3, h - 8);

  ctx.fillStyle = "#fff";
  ctx.font = "bold 13px sans-serif";
  ctx.fillText(title, cx, detail ? y + 13 : cy);
  if (detail) {
    ctx.fillStyle = "#e5e7eb";
    ctx.font = "12px sans-serif";
    ctx.fillText(detail, cx, y + 29);
  }
  ctx.textBaseline = "alphabetic";
}

interface ZoneCanvasProps {
  width: number;
  height: number;
  zones: { id: string; name: string; color: string; polygon_points: PolygonPoint[] }[];
  activeZoneId?: string;
  drawing?: boolean;
  onDrawComplete?: (points: PolygonPoint[]) => void;
  background?: ImageBitmap | null;
  placeholder?: string;
  badges?: Record<string, ZoneBadge>;
}

export function ZoneCanvas({
  width, height, zones, activeZoneId, drawing, onDrawComplete, background, placeholder = "Vista de cámara (sin imagen)", badges,
}: ZoneCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawPoints, setDrawPoints] = useState<PolygonPoint[]>([]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    if (background) {
      ctx.drawImage(background, 0, 0, width, height);
    } else {
      ctx.fillStyle = "#1f2937";
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "#6b7280";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(placeholder, width / 2, height / 2);
    }

    // Draw existing zones
    for (const zone of zones) {
      const pts = zone.polygon_points;
      if (pts.length < 3) continue;

      ctx.beginPath();
      ctx.moveTo(pts[0].x * width, pts[0].y * height);
      for (let i = 1; i < pts.length; i++) {
        ctx.lineTo(pts[i].x * width, pts[i].y * height);
      }
      ctx.closePath();

      const isActive = zone.id === activeZoneId;
      const badge = badges?.[zone.id];
      const color = badge && badge.tone !== "idle" ? TONE_COLORS[badge.tone] : zone.color;
      const alpha = badge?.tone === "alert" ? "55" : badge?.tone === "warn" ? "40" : isActive ? "40" : "20";
      ctx.fillStyle = color + alpha;
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isActive || (badge && badge.tone !== "idle" && badge.tone !== "ok") ? 3 : 2;
      ctx.stroke();

      const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length * width;
      const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length * height;
      drawLabel(ctx, cx, cy, badge ? `${zone.name} · ${badge.title}` : zone.name, badge?.detail, color);
    }

    // Draw in-progress polygon
    if (drawPoints.length > 0) {
      ctx.beginPath();
      ctx.moveTo(drawPoints[0].x * width, drawPoints[0].y * height);
      for (let i = 1; i < drawPoints.length; i++) {
        ctx.lineTo(drawPoints[i].x * width, drawPoints[i].y * height);
      }
      ctx.strokeStyle = "#3b82f6";
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.stroke();
      ctx.setLineDash([]);

      for (const p of drawPoints) {
        ctx.beginPath();
        ctx.arc(p.x * width, p.y * height, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#3b82f6";
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }, [width, height, zones, activeZoneId, drawPoints, background, placeholder, badges]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e: MouseEvent<HTMLCanvasElement>) => {
    if (!drawing) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    const newPoints = [...drawPoints, { x: +x.toFixed(4), y: +y.toFixed(4) }];
    setDrawPoints(newPoints);
  };

  const handleDoubleClick = () => {
    if (!drawing || drawPoints.length < 3) return;
    onDrawComplete?.(drawPoints);
    setDrawPoints([]);
  };

  const handleRightClick = (e: MouseEvent) => {
    e.preventDefault();
    if (drawPoints.length > 0) {
      setDrawPoints(drawPoints.slice(0, -1));
    }
  };

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleRightClick}
      className={`rounded-lg border max-w-full h-auto ${drawing ? "cursor-crosshair" : "cursor-default"}`}
    />
  );
}
