/**
 * Per-hazard disclaimer banner shown at the top of each dashboard tab.
 *
 * The global Footer carries the platform-wide language ("not a substitute
 * for official warnings — IMD/NDMA take precedence"); this component adds
 * hazard-specific caveats so users see them above the fold next to the data
 * they're interpreting, not at the bottom of the page.
 */

export type HazardKind =
  | "earthquake"
  | "flood"
  | "cyclone"
  | "wildfire"
  | "landslide"
  | "damage"
  | "sos";

const COPY: Record<HazardKind, { authority: string; body: string }> = {
  earthquake: {
    authority: "NCS and IMD",
    body:
      "Alertix AI does not perform deterministic earthquake prediction. Values shown represent " +
      "statistical anomaly scores and aftershock probabilities derived from recent seismicity.",
  },
  flood: {
    authority: "CWC and the State Disaster Management Authority",
    body:
      "Gauge levels are scraped from CWC's flood-forecasting dashboard and may lag the live " +
      "station feed. Severity is inferred from warning/danger thresholds — not a forecast.",
  },
  cyclone: {
    authority: "IMD and RSMC New Delhi",
    body:
      "Cyclone tracks shown here are advisories from IMD/JTWC, replayed for visualisation. " +
      "Landfall timing, intensity, and track can change rapidly; always check the latest bulletin.",
  },
  wildfire: {
    authority: "the State Forest Department and Forest Survey of India",
    body:
      "Hotspots come from NASA FIRMS (VIIRS/MODIS) and indicate thermal anomalies — not " +
      "confirmed fires. Clouds, sun glint, and industrial heat sources can produce false positives.",
  },
  landslide: {
    authority: "GSI and the State Disaster Management Authority",
    body:
      "Risk scoring blends rainfall thresholds with GSI susceptibility zones. It is not a " +
      "real-time slope-stability model — local geology, drainage, and human activity dominate risk.",
  },
  damage: {
    authority: "the assessing agency on the ground",
    body:
      "Damage classifications are derived from Sentinel-1 SAR change detection. Cloud-free " +
      "optical verification and field assessment are required before publishing official figures.",
  },
  sos: {
    authority: "112 (India Emergency Response) and your local disaster control room",
    body:
      "Alertix SOS triage is decision support for responders, not a dispatch system. " +
      "It does not replace calling emergency services and may misclassify ambiguous messages.",
  },
};

interface Props {
  hazard: HazardKind;
  className?: string;
}

export default function HazardDisclaimer({ hazard, className = "" }: Props) {
  const { authority, body } = COPY[hazard];
  return (
    <div
      role="note"
      aria-label={`${hazard} data disclaimer`}
      className={
        "rounded-lg border border-yellow-600/30 bg-yellow-600/5 p-3 text-xs text-yellow-300 " +
        className
      }
    >
      {body} Always follow official warnings from {authority}.
    </div>
  );
}
