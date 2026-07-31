import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  damageImageBlob,
  fetchDamageReports,
  uploadDamageImage,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DAMAGE_COLORS,
  DAMAGE_LABELS,
  type DamageClass,
  type DamageResult,
  type DamageReportSummary,
} from "@/lib/types";
import HazardDisclaimer from "@/components/HazardDisclaimer";

const DAMAGE_ORDER: DamageClass[] = ["no_damage", "minor", "major", "destroyed"];

function ClassBadge({ cls, big = false }: { cls: DamageClass; big?: boolean }) {
  const color = DAMAGE_COLORS[cls];
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold uppercase tracking-wide ${
        big ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"
      }`}
      style={{ backgroundColor: color + "22", color }}
    >
      {DAMAGE_LABELS[cls]}
    </span>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct > 75 ? "#22c55e" : pct > 50 ? "#facc15" : "#f97316";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
        <span>Confidence</span>
        <span className="font-mono font-semibold" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function ProbabilityBars({ probs }: { probs: Record<DamageClass, number> }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">
        Per-class probability
      </p>
      {DAMAGE_ORDER.map((cls) => {
        const v = probs[cls] ?? 0;
        const pct = Math.round(v * 100);
        return (
          <div key={cls}>
            <div className="mb-0.5 flex items-center justify-between text-xs">
              <span style={{ color: DAMAGE_COLORS[cls] }}>{DAMAGE_LABELS[cls]}</span>
              <span className="font-mono text-muted-foreground">{pct}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full"
                style={{ width: `${pct}%`, backgroundColor: DAMAGE_COLORS[cls] }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MaskedImage({
  imageUrl,
  maskOverlay,
  showMask,
}: {
  imageUrl: string;
  maskOverlay: string;
  showMask: boolean;
}) {
  return (
    <div className="relative w-full overflow-hidden rounded-lg border border-border bg-black">
      <img src={imageUrl} alt="Uploaded damage scene" className="block w-full" />
      {showMask && maskOverlay && (
        <img
          src={maskOverlay}
          alt="Damage mask overlay"
          className="pointer-events-none absolute inset-0 h-full w-full mix-blend-screen"
          style={{ imageRendering: "pixelated" }}
        />
      )}
    </div>
  );
}

function HistoryItem({
  report,
  onSelect,
}: {
  report: DamageReportSummary;
  onSelect: () => void;
}) {
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    damageImageBlob(report.id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setThumbUrl(objectUrl);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [report.id]);

  return (
    <button
      onClick={onSelect}
      className="flex w-full items-center gap-3 rounded-md border border-border p-2 text-left hover:bg-accent/40"
    >
      <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded bg-secondary">
        {thumbUrl && <img src={thumbUrl} alt="" className="h-full w-full object-cover" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex items-center gap-2">
          <ClassBadge cls={report.class_label} />
          <span className="text-xs text-muted-foreground">
            {Math.round(report.confidence * 100)}%
          </span>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {report.created_at ? new Date(report.created_at).toLocaleString() : "—"}
        </p>
      </div>
    </button>
  );
}

export default function DamageTab() {
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [latitude, setLatitude] = useState<string>("");
  const [longitude, setLongitude] = useState<string>("");
  const [result, setResult] = useState<DamageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMask, setShowMask] = useState(true);

  // Local preview URL for the uploaded file (used before server returns)
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Authenticated server image (after upload succeeds)
  const [serverImageUrl, setServerImageUrl] = useState<string | null>(null);
  const serverImageRef = useRef<string | null>(null);
  useEffect(() => {
    if (!result) return;
    let cancelled = false;
    damageImageBlob(result.report_id)
      .then((blob) => {
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        if (serverImageRef.current) URL.revokeObjectURL(serverImageRef.current);
        serverImageRef.current = url;
        setServerImageUrl(url);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [result]);
  useEffect(() => {
    return () => {
      if (serverImageRef.current) URL.revokeObjectURL(serverImageRef.current);
    };
  }, []);

  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ["damage", "reports"],
    queryFn: () => fetchDamageReports(20),
    refetchInterval: 60_000,
  });

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const res = await uploadDamageImage(file, {
        latitude: latitude ? Number(latitude) : undefined,
        longitude: longitude ? Number(longitude) : undefined,
        notes: notes || undefined,
      });
      setResult(res);
      void refetchHistory();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const fillCurrentLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(5));
        setLongitude(pos.coords.longitude.toFixed(5));
      },
      () => setError("Location permission denied"),
      { timeout: 10_000 },
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Damage Assessment</h2>
      <HazardDisclaimer hazard="damage" />
      <p className="text-sm text-muted-foreground">
        Upload drone or smartphone images for AI-powered damage segmentation.
        Phase 2 will use DeepLabV3 for building/road/water/vegetation detection.
      </p>

      <div className="grid gap-6 lg:grid-cols-[1fr,360px]">
        <div className="space-y-6">
          {/* Upload card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Upload Image</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setResult(null);
                }}
                className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
              />

              <div className="grid gap-2 sm:grid-cols-3">
                <input
                  type="number"
                  placeholder="Latitude (optional)"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="Longitude (optional)"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                />
                <Button variant="outline" type="button" onClick={fillCurrentLocation}>
                  📍 Use my location
                </Button>
              </div>

              <input
                type="text"
                placeholder="Notes (optional — e.g. 'flooded ground floor, structural cracks')"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              />

              <div className="flex items-center gap-3">
                <Button onClick={handleUpload} disabled={!file || loading}>
                  {loading ? "Analyzing…" : "Analyze Damage"}
                </Button>
                {result && (
                  <Button
                    variant="outline"
                    onClick={() => setShowMask((s) => !s)}
                  >
                    {showMask ? "Hide overlay" : "Show overlay"}
                  </Button>
                )}
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
            </CardContent>
          </Card>

          {/* Result panel */}
          {(previewUrl || result) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  <span>Result</span>
                  {result && <ClassBadge cls={result.class_label} big />}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <MaskedImage
                    imageUrl={serverImageUrl ?? previewUrl ?? ""}
                    maskOverlay={result?.mask_overlay ?? ""}
                    showMask={showMask && !!result}
                  />
                  <div className="space-y-4">
                    {result ? (
                      <>
                        <ConfidenceMeter value={result.confidence} />
                        <ProbabilityBars probs={result.class_probs} />
                        {result.description && (
                          <div className="rounded-md border border-blue-700/40 bg-blue-950/20 p-3 text-sm text-blue-100">
                            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-blue-300">
                              AI description
                            </p>
                            <p>{result.description}</p>
                            {result.visible_hazards.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {result.visible_hazards.map((h) => (
                                  <span
                                    key={h}
                                    className="rounded-full bg-blue-700/30 px-2 py-0.5 text-xs"
                                  >
                                    {h.replace(/_/g, " ")}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        <div className="space-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
                          <p>
                            <span className="text-foreground">Provider:</span>{" "}
                            <span
                              className={
                                result.provider === "gemini-vision"
                                  ? "font-mono font-semibold text-blue-400"
                                  : "font-mono text-yellow-400"
                              }
                            >
                              {result.provider}
                            </span>
                            {result.provider === "cnn-synthetic" && (
                              <span className="ml-1 text-yellow-500">
                                (demo model — synthetic training)
                              </span>
                            )}
                          </p>
                          <p>
                            <span className="text-foreground">Model:</span>{" "}
                            <span className="font-mono">{result.model_version}</span>
                          </p>
                          <p>
                            <span className="text-foreground">Latency:</span>{" "}
                            {result.latency_ms.toFixed(1)} ms
                          </p>
                          <p>
                            <span className="text-foreground">Image hash:</span>{" "}
                            <span className="font-mono">
                              {result.sha256.slice(0, 12)}…
                            </span>
                            {result.deduplicated && (
                              <span className="ml-1 text-green-400">(deduplicated)</span>
                            )}
                          </p>
                          {result.nearest_event && (
                            <p className="rounded-md border border-orange-700/40 bg-orange-950/20 p-2 text-orange-300">
                              📍 Nearest hazard:{" "}
                              <span className="font-semibold">
                                {result.nearest_event.hazard_type}
                              </span>{" "}
                              · {result.nearest_event.distance_km} km away
                              {result.nearest_event.title && (
                                <>
                                  <br />
                                  <span className="text-xs">{result.nearest_event.title}</span>
                                </>
                              )}
                            </p>
                          )}
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Click <span className="font-medium">Analyze Damage</span> to classify
                        and segment this image.
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* History sidebar */}
        <div className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Reports</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {history?.reports.length ? (
                history.reports.map((r) => (
                  <HistoryItem
                    key={r.id}
                    report={r}
                    onSelect={() => {
                      // Bring report into the result panel as a read-only summary
                      setResult({
                        status: "history",
                        report_id: r.id,
                        filename: "",
                        sha256: "",
                        image_url: r.image_url,
                        deduplicated: false,
                        class_label: r.class_label,
                        confidence: r.confidence,
                        class_probs: r.class_probs,
                        bounding_boxes: [],
                        mask_overlay: "",
                        mask_shape: [0, 0],
                        model_version: r.model_version,
                        provider: r.model_version.includes("gemini")
                          ? "gemini-vision"
                          : "cnn-synthetic",
                        description: r.notes?.startsWith("[gemini] ")
                          ? r.notes.slice("[gemini] ".length).split("\n")[0]
                          : "",
                        visible_hazards: [],
                        latency_ms: 0,
                        nearest_event: null,
                      });
                      setFile(null);
                    }}
                  />
                ))
              ) : (
                <p className="text-xs text-muted-foreground">
                  No reports yet. Upload an image to get started.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
