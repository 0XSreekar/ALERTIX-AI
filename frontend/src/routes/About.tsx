import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const hazards = [
  { name: "Earthquake", status: "Real AI (proprietary)", tech: "LSTM autoencoder + Omori law + LLM characterization" },
  { name: "Flood", status: "Real AI (proprietary)", tech: "CWC river gauges + Open-Meteo rainfall + U-Net extent" },
  { name: "Cyclone", status: "Live data integration", tech: "IMD bulletins + Open-Meteo wind fields" },
  { name: "Wildfire", status: "Live data integration", tech: "NASA FIRMS VIIRS/MODIS hotspot detection" },
  { name: "Landslide", status: "Static + rule-based", tech: "GSI hazard zonation + rainfall threshold rules" },
  { name: "Damage", status: "Pretrained model", tech: "DeepLabV3 segmentation on uploaded imagery" },
];

export default function About() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-16">
        <h1 className="mb-6 text-4xl font-bold">About Alertix AI</h1>

        <section className="mb-12">
          <h2 className="mb-4 text-2xl font-semibold">What We Do</h2>
          <ul className="list-inside list-disc space-y-2 text-muted-foreground">
            <li>Ingest real-time hazard data from 6+ public sources every 1-5 minutes</li>
            <li>Store every event with full provenance in PostGIS</li>
            <li>Run proprietary models for seismic anomaly detection and flood discharge forecasting</li>
            <li>Surface all hazards on a unified live map with severity, probability, and explanation layers</li>
            <li>Generate LLM-written alert explanations in English and Hindi</li>
            <li>Accept citizen SOS submissions with location extraction and urgency scoring</li>
            <li>Issue alerts within 90 seconds of source publish</li>
          </ul>
        </section>

        <section className="mb-12">
          <h2 className="mb-4 text-2xl font-semibold">What We Do NOT Do (v1)</h2>
          <ul className="list-inside list-disc space-y-2 text-muted-foreground">
            <li>Does not bypass or replace national early-warning systems (IMD, NCS, NDRF)</li>
            <li>Does not provide tactical evacuation routing in production</li>
            <li>Does not perform automated cross-agency coordination</li>
            <li>Does not filter misinformation at scale</li>
            <li>Does not guarantee uptime suitable for life-safety reliance</li>
          </ul>
        </section>

        <section className="mb-12">
          <h2 className="mb-4 text-2xl font-semibold">Hazard Coverage</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {hazards.map((h) => (
              <Card key={h.name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{h.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs font-medium text-primary">{h.status}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{h.tech}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-2xl font-semibold">Technology</h2>
          <p className="text-muted-foreground">
            Python 3.11 + FastAPI backend with bcrypt + HS256 JWT auth, React + TypeScript +
            Vite frontend, Postgres + PostGIS database, Upstash Redis for cache and real-time
            messaging, Cloudflare R2 for object storage. ML powered by PyTorch, scikit-learn,
            and XGBoost. Local LLM: Qwen2.5-7B-Instruct via Ollama with Groq and Gemini fallbacks.
          </p>
        </section>
      </main>
      <Footer />
    </div>
  );
}
