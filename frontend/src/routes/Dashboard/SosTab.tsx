import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { submitSos, fetchMySos } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SosTab() {
  const [text, setText] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const { data: myReports, refetch } = useQuery({
    queryKey: ["sos", "mine"],
    queryFn: fetchMySos,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;
    setStatus("sending");
    try {
      await submitSos({
        raw_text: text,
        latitude: lat ? parseFloat(lat) : undefined,
        longitude: lon ? parseFloat(lon) : undefined,
        consent_given: true,
      });
      setStatus("sent");
      setText("");
      setLat("");
      setLon("");
      setConsent(false);
      refetch();
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
            <Button type="submit" disabled={!consent || status === "sending"}>
              {status === "sending" ? "Submitting..." : "Submit SOS"}
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
