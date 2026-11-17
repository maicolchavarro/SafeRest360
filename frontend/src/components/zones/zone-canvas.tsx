"use client";

import { useRef, useState, useEffect, useCallback, type MouseEvent, type PointerEvent } from "react";
import type { PolygonPoint } from "@/lib/types";
import { TONE_COLORS, type ZoneBadge } from "@/lib/zone-state";

const HANDLE_RADIUS = 7;
const HIT_RADIUS = 12;

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

function insidePolygon(p: PolygonPoint, pts: PolygonPoint[]): boolean {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const a = pts[i], b = pts[j];
    if ((a.y > p.y) !== (b.y > p.y) && p.x < ((b.x - a.x) * (p.y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
  }
  return inside;
}

const clamp = (v: number) => Math.min(1, Math.max(0, +v.toFixed(4)));

/** Drop the duplicate vertices a double click adds at the end of a drawing */
function dedupe(points: PolygonPoint[]): PolygonPoint[] {
  return points.filter((p, i) => i === 0 || Math.hypot(p.x - points[i - 1].x, p.y - points[i - 1].y) > 0.005);
}

type Drag =
  | { kind: "vertex"; index: number }
  | { kind: "move"; start: PolygonPoint; original: PolygonPoint[] };

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
  /** Zone being edited: its shape comes from editPoints instead of the saved polygon */
  editZoneId?: string;
  editPoints?: PolygonPoint[];
  onEditPointsChange?: (points: PolygonPoint[]) => void;
}

export function ZoneCanvas({
  width, height, zones, activeZoneId, drawing, onDrawComplete, background,
  placeholder = "Vista de cámara (sin imagen)", badges, editZoneId, editPoints, onEditPointsChange,
}: ZoneCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawPoints, setDrawPoints] = useState<PolygonPoint[]>([]);
  const dragRef = useRef<Drag | null>(null);
  const editing = !!editZoneId && !!editPoints;

  useEffect(() => {
    if (!drawing) setDrawPoints([]);
  }, [drawing]);

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

    for (const zone of zones) {
      const isEdited = editing && zone.id === editZoneId;
      const pts = isEdited ? editPoints! : zone.polygon_points;
      if (pts.length < 3) continue;

      ctx.beginPath();
      ctx.moveTo(pts[0].x * width, pts[0].y * height);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x * width, pts[i].y * height);
      ctx.closePath();

      if (isEdited) {
        ctx.fillStyle = "#3b82f633";
        ctx.fill();
        ctx.strokeStyle = "#3b82f6";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
        continue;
      }

      const isActive = zone.id === activeZoneId;
      const badge = badges?.[zone.id];
      const color = badge && badge.tone !== "idle" ? TONE_COLORS[badge.tone] : zone.color;
      const alpha = badge?.tone === "alert" ? "55" : badge?.tone === "warn" ? "40" : isActive ? "40" : "20";
      ctx.globalAlpha = editing ? 0.45 : 1;
      ctx.fillStyle = color + alpha;
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isActive || (badge && badge.tone !== "idle" && badge.tone !== "ok") ? 3 : 2;
      ctx.stroke();

      const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length * width;
      const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length * height;
      drawLabel(ctx, cx, cy, badge ? `${zone.name} · ${badge.title}` : zone.name, badge?.detail, color);
      ctx.globalAlpha = 1;
    }

    if (editing) {
      const pts = editPoints!;
      // midpoints: drag one to add a corner
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        ctx.beginPath();
        ctx.arc(((a.x + b.x) / 2) * width, ((a.y + b.y) / 2) * height, 4, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(59, 130, 246, 0.6)";
        ctx.fill();
      }
      for (const p of pts) {
        ctx.beginPath();
        ctx.arc(p.x * width, p.y * height, HANDLE_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = "#fff";
        ctx.fill();
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    }

    if (drawPoints.length > 0) {
      ctx.beginPath();
      ctx.moveTo(drawPoints[0].x * width, drawPoints[0].y * height);
      for (let i = 1; i < drawPoints.length; i++) ctx.lineTo(drawPoints[i].x * width, drawPoints[i].y * height);
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
  }, [width, height, zones, activeZoneId, drawPoints, background, placeholder, badges, editing, editZoneId, editPoints]);

  useEffect(() => { draw(); }, [draw]);

  const toNormalized = (e: { clientX: number; clientY: number }): PolygonPoint => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: clamp((e.clientX - rect.left) / rect.width), y: clamp((e.clientY - rect.top) / rect.height) };
  };

  /** distance in canvas pixels between a normalized point and the pointer */
  const pixelDistance = (a: PolygonPoint, b: PolygonPoint) => Math.hypot((a.x - b.x) * width, (a.y - b.y) * height);

  const handleClick = (e: MouseEvent<HTMLCanvasElement>) => {
    if (!drawing) return;
    setDrawPoints([...drawPoints, toNormalized(e)]);
  };

  const handleDoubleClick = () => {
    if (!drawing) return;
    const points = dedupe(drawPoints);
    if (points.length < 3) return;
    onDrawComplete?.(points);
    setDrawPoints([]);
  };

  const handleRightClick = (e: MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (editing) {
      const p = toNormalized(e);
      const index = editPoints!.findIndex((v) => pixelDistance(v, p) <= HIT_RADIUS);
      if (index >= 0 && editPoints!.length > 3) onEditPointsChange?.(editPoints!.filter((_, i) => i !== index));
      return;
    }
    if (drawPoints.length > 0) setDrawPoints(drawPoints.slice(0, -1));
  };

  const handlePointerDown = (e: PointerEvent<HTMLCanvasElement>) => {
    if (!editing || e.button !== 0) return;
    const p = toNormalized(e);
    const pts = editPoints!;
    const vertex = pts.findIndex((v) => pixelDistance(v, p) <= HIT_RADIUS);
    if (vertex >= 0) {
      dragRef.current = { kind: "vertex", index: vertex };
    } else {
      const mid = pts.findIndex((a, i) => {
        const b = pts[(i + 1) % pts.length];
        return pixelDistance({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, p) <= HIT_RADIUS;
      });
      if (mid >= 0) {
        const next = [...pts.slice(0, mid + 1), p, ...pts.slice(mid + 1)];
        onEditPointsChange?.(next);
        dragRef.current = { kind: "vertex", index: mid + 1 };
      } else if (insidePolygon(p, pts)) {
        dragRef.current = { kind: "move", start: p, original: pts };
      } else {
        return;
      }
    }
    canvasRef.current?.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!editing || !drag) return;
    const p = toNormalized(e);
    if (drag.kind === "vertex") {
      onEditPointsChange?.(editPoints!.map((v, i) => (i === drag.index ? p : v)));
    } else {
      const xs = drag.original.map((v) => v.x), ys = drag.original.map((v) => v.y);
      // keep the whole shape inside the image
      const dx = Math.min(Math.max(p.x - drag.start.x, -Math.min(...xs)), 1 - Math.max(...xs));
      const dy = Math.min(Math.max(p.y - drag.start.y, -Math.min(...ys)), 1 - Math.max(...ys));
      onEditPointsChange?.(drag.original.map((v) => ({ x: clamp(v.x + dx), y: clamp(v.y + dy) })));
    }
  };

  const endDrag = () => { dragRef.current = null; };

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleRightClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      className={`block mx-auto rounded-lg border max-w-full max-h-[60vh] w-auto h-auto ${editing ? "touch-none " : ""}${
        drawing ? "cursor-crosshair" : editing ? "cursor-move" : "cursor-default"
      }`}
    />
  );
}
