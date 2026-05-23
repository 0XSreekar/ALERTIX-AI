import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMySos } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getAuthToken(): string | null {
  return localStorage.getItem("alertix_token");
}

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

  const uploadFileWithProgress = (f: File): Promise<string | null> => {
    return new Promise((resolve, reject) => {
      const token = getAuthToken();
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
          try {
            const res = JSON.parse(xhr.responseText) as { url?: string };
            resolve(res.url ?? null);
          } catch {
            resolve(null);
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error("Upload network error"));

      xhr.open("POST", `${BASE}/api/sos/upload`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.send(form);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;

    setStatus("idle");
    setUploadProgress(0);

    let mediaUrl: string | null = null;

    try {
      if (file) {
        setStatus("uploading");
        mediaUrl = await uploadFileWithProgress(file);
        setUploadProgress(100);
      }

      setStatus("sending");

      const token = getAuthToken();
      const body = {
        raw_text: text,
        latitude: lat ? parseFloat(lat) : undefined,
        longitude: lon ? parseFloat(lon) : undefined,
        consent_given: true,
        ...(mediaUrl ? { media_url: mediaUrl } : {}),
      };

      const res = await fetch(`${BASE}/api/sos`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`SOS submit failed: ${res.status}`);

      setStatus("sent");
      setText("");
      setLat("");
      setLon("");
      setConsent(false);
      setFile(null);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
      void refetch();
    } catch {
      setStatus("error");
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
              <p className="text-sm text-red-400">Failed to submit. Try again.</p>
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
