import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMySos } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import HazardDisclaimer from "@/components/HazardDisclaimer";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function SosTab() {
  const [text, setText] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [consent, setConsent] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [status, setStatus] = useState<"idle" | "uploading" | "sending" | "sent" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: myReports, refetch } = useQuery({
    queryKey: queryKeys.sos.mine,
    queryFn: fetchMySos,
  });

  const [errorDetail, setErrorDetail] = useState("");

  /** Upload file against an existing SOS report (post-create). */
  const uploadAttachmentWithProgress = (sosId: string, f: File): Promise<void> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const form = new FormData();
      form.append("file", f);

      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          setUploadProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
        } else {
          reject(new Error(`HTTP ${xhr.status}: ${xhr.responseText.slice(0, 200)}`));
        }
      };

      xhr.onerror = () => reject(new Error("Upload network error"));

      xhr.withCredentials = true; // send HttpOnly auth cookie
      xhr.open("POST", `${BASE}/api/sos/mine/${sosId}/attachment`);
      xhr.send(form);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;

    setStatus("idle");
    setErrorDetail("");
    setUploadProgress(0);

    try {
      setStatus("sending");

      const body = {
        raw_text: text,
        latitude: lat ? parseFloat(lat) : undefined,
        longitude: lon ? parseFloat(lon) : undefined,
        consent_given: true,
      };

      const res = await fetch(`${BASE}/api/sos`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errText = await res.text();
        let detail = `HTTP ${res.status}`;
        try {
          const j = JSON.parse(errText) as { detail?: string };
          if (j.detail) detail = j.detail;
        } catch {
          if (errText) detail += `: ${errText.slice(0, 200)}`;
        }
        throw new Error(detail);
      }

      const created = (await res.json()) as { id: string };

      // If there's a file attached, upload it as an attachment against the new report.
      // We deliberately don't fail the whole submission if attachment fails.
      if (file && created.id) {
        try {
          setStatus("uploading");
          await uploadAttachmentWithProgress(created.id, file);
          setUploadProgress(100);
        } catch (attachErr) {
          setErrorDetail(`Report saved, but attachment failed: ${attachErr}`);
        }
      }

      setStatus("sent");
      setText("");
      setLat("");
      setLon("");
      setConsent(false);
      setFile(null);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
      void refetch();
    } catch (err) {
      setStatus("error");
      setErrorDetail(String(err instanceof Error ? err.message : err));
    }
  };

  const getLocation = () => {
    navigator.geolocation?.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6));
      setLon(pos.coords.longitude.toFixed(6));
    });
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">SOS Reports</h2>
      <HazardDisclaimer hazard="sos" />

      <div className="rounded-md border border-cyan-700/30 bg-cyan-950/20 p-3 text-xs text-cyan-100">
        <p className="mb-1 font-semibold uppercase tracking-wider text-cyan-300">
          Where does this report go?
        </p>
        <ul className="ml-4 list-disc space-y-0.5 text-cyan-50/80">
          <li>Saved to the secure <code className="rounded bg-cyan-900/40 px-1">sos_reports</code> table with your user ID, GPS (if shared), and consent timestamp.</li>
          <li>Auto-enriched within seconds: language detected → translated → place names extracted → geocoded → urgency triaged (1–5) via LLM.</li>
          <li>Officials/admins see urgency-ranked submissions on the <strong>Triaged Feed</strong> (this dashboard, role-gated).</li>
          <li>You will see your own submissions below under <strong>My Reports</strong>, including triage status and AI summary.</li>
        </ul>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Submit Distress Report</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Describe the situation</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                required
                minLength={10}
                rows={4}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Describe the emergency, location, and number of people affected..."
              />
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Latitude</label>
                <Input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="Optional" />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Longitude</label>
                <Input value={lon} onChange={(e) => setLon(e.target.value)} placeholder="Optional" />
              </div>
              <div className="flex items-end">
                <Button type="button" variant="outline" size="sm" onClick={getLocation}>
                  Use GPS
                </Button>
              </div>
            </div>

            {/* File upload with progress */}
            <div>
              <label className="mb-1 block text-sm font-medium">
                Attach media <span className="text-xs text-muted-foreground">(optional)</span>
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
              />
              {status === "uploading" && (
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Uploading…</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="consent"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="rounded"
              />
              <label htmlFor="consent" className="text-xs text-muted-foreground">
                I consent to the processing of this report per DPDPA 2023.
              </label>
            </div>
            <Button
              type="submit"
              disabled={!consent || status === "uploading" || status === "sending"}
            >
              {status === "uploading"
                ? "Uploading…"
                : status === "sending"
                  ? "Submitting…"
                  : "Submit SOS"}
            </Button>
            {status === "sent" && (
              <p className="text-sm text-green-400">Report submitted. Stay safe.</p>
            )}
            {status === "error" && (
              <div className="rounded-md border border-red-800/50 bg-red-950/30 p-2 text-sm text-red-300">
                <p className="font-medium">Failed to submit.</p>
                {errorDetail && (
                  <p className="mt-1 break-words font-mono text-[11px] opacity-80">
                    {errorDetail}
                  </p>
                )}
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">My Reports</CardTitle>
        </CardHeader>
        <CardContent>
          {!myReports?.reports.length ? (
            <p className="text-sm text-muted-foreground">No reports submitted yet.</p>
          ) : (
            <div className="space-y-3">
              {myReports.reports.map((r) => (
                <div key={r.id} className="rounded border p-3">
                  <p className="text-sm">{r.raw_text}</p>
                  <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                    <span>{new Date(r.created_at).toLocaleString()}</span>
                    {r.urgency_score != null && (
                      <span>Urgency: {r.urgency_score.toFixed(1)}/5</span>
                    )}
                    <span>{r.triaged ? "Triaged" : "Pending triage"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
