import React from "react";
import { Link } from "react-router-dom";
import { Suspense, lazy } from "react";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";

// Lazy-load Three.js to keep it out of the initial bundle
const ThreeEarth = lazy(() => import("@/components/ThreeEarth"));

const hazards = [
  {
    icon: "🌍",
    title: "Earthquakes",
    desc: "USGS + IRIS live feed. LSTM anomaly detection. Omori aftershock probability. M5+ alerts in under 5 min.",
    color: "from-orange-950/60 to-orange-900/30",
    border: "border-orange-800/40",
  },
  {
    icon: "🌊",
    title: "Floods",
    desc: "CWC river gauges + Open-Meteo rainfall. Official flood bulletins and Sentinel-1 SAR flood extent mapping.",
    color: "from-blue-950/60 to-blue-900/30",
    border: "border-blue-800/40",
  },
  {
    icon: "🌀",
    title: "Cyclones",
    desc: "IMD bulletin parser. Live track extrapolation with impact-radius overlay. Wind + surge alerts.",
    color: "from-teal-950/60 to-teal-900/30",
    border: "border-teal-800/40",
  },
  {
    icon: "🔥",
    title: "Wildfires",
    desc: "NASA FIRMS hotspot ingestion. DBSCAN cluster detection. 24-hr rolling fire-front map.",
    color: "from-red-950/60 to-red-900/30",
    border: "border-red-800/40",
  },
  {
    icon: "⛰️",
    title: "Landslides",
    desc: "GSI hazard zonation overlay. Rainfall intensity-duration threshold rules. District-level risk flags.",
    color: "from-yellow-950/60 to-yellow-900/30",
    border: "border-yellow-800/40",
  },
  {
    icon: "🏚️",
    title: "Damage AI",
    desc: "DeepLabV3 segmentation on uploaded post-disaster imagery. Structure class breakdown + area estimate.",
    color: "from-purple-950/60 to-purple-900/30",
    border: "border-purple-800/40",
  },
];

const stats = [
  { value: "< 5 min", label: "Alert latency" },
  { value: "6", label: "Hazard categories" },
  { value: "Zero", label: "Paid APIs" },
  { value: "100%", label: "Open source" },
];

const stack = [
  "USGS", "IMD", "NASA FIRMS", "CWC",
  "Sentinel-1", "Open-Meteo", "GSI", "Ollama", "FastAPI", "Supabase",
];

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.55, ease: "easeOut" },
  }),
};

export default function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      <Navbar />

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="relative flex min-h-[92vh] items-center justify-center overflow-hidden">
        {/* Volcano background — Three.js is lazy loaded */}
        <div className="absolute inset-0 -z-10">
          <React.Suspense
            fallback={
              <div className="h-full w-full animate-pulse rounded-full bg-slate-800/30" />
            }
          >
            <ThreeEarth className="h-full w-full opacity-55" />
          </React.Suspense>
        </div>

        {/* Gradient overlays */}
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-background/30 via-transparent to-background" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-background/60 via-transparent to-background/60" />

        {/* Animated lava glow on floor */}
        <motion.div
          className="absolute bottom-0 left-1/2 -z-10 h-48 w-96 -translate-x-1/2 rounded-full bg-orange-600/10 blur-3xl"
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />

        <div className="relative z-10 mx-auto max-w-4xl px-6 text-center">
          {/* Badge */}
          <motion.div
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-orange-700/50 bg-orange-950/40 px-4 py-1.5 text-sm text-orange-300 backdrop-blur-sm"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <span className="h-2 w-2 animate-pulse rounded-full bg-orange-400" />
            Live multi-hazard intelligence for India
          </motion.div>

          <motion.h1
            className="mb-5 text-5xl font-extrabold leading-tight tracking-tight text-white sm:text-7xl"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.65 }}
          >
            Know before
            <br />
            <span className="bg-gradient-to-r from-orange-400 via-red-400 to-yellow-400 bg-clip-text text-transparent">
              disaster strikes
            </span>
          </motion.h1>

          <motion.p
            className="mb-10 text-lg leading-relaxed text-slate-300 sm:text-xl"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35, duration: 0.6 }}
          >
            Earthquake · Flood · Cyclone · Wildfire · Landslide · Damage&nbsp;AI
            <br className="hidden sm:block" />
            Open data. Open models. Zero paid APIs. Built for India.
          </motion.p>

          <motion.div
            className="flex flex-wrap justify-center gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            <Link to="/dashboard">
              <Button
                size="lg"
                className="bg-orange-600 px-8 py-6 text-base font-semibold hover:bg-orange-500"
              >
                Open Dashboard →
              </Button>
            </Link>
            <Link to="/about">
              <Button
                size="lg"
                variant="outline"
                className="border-slate-600 px-8 py-6 text-base font-semibold hover:border-orange-500 hover:text-orange-300"
              >
                How it works
              </Button>
            </Link>
          </motion.div>
        </div>

        {/* Scroll hint */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 text-slate-500"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.8, repeat: Infinity }}
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </motion.div>
      </section>

      {/* ── Stats strip ─────────────────────────────────────────── */}
      <section className="border-y border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="mx-auto grid max-w-4xl grid-cols-2 divide-x divide-slate-800 sm:grid-cols-4">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              className="flex flex-col items-center px-6 py-8"
              custom={i}
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              <span className="text-3xl font-bold text-orange-400">{s.value}</span>
              <span className="mt-1 text-sm text-slate-400">{s.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Hazard cards ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <motion.div
          className="mb-14 text-center"
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          custom={0}
          viewport={{ once: true }}
        >
          <h2 className="text-4xl font-bold text-white">Six hazards. One platform.</h2>
          <p className="mt-3 text-slate-400">
            Real-time data pipelines, ML models, and LLM plain-language alerts.
          </p>
        </motion.div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {hazards.map((h, i) => (
            <motion.div
              key={h.title}
              custom={i}
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className={`rounded-xl border bg-gradient-to-br p-6 ${h.color} ${h.border}`}
            >
              <div className="mb-3 text-3xl">{h.icon}</div>
              <h3 className="mb-2 text-lg font-semibold text-white">{h.title}</h3>
              <p className="text-sm leading-relaxed text-slate-300">{h.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Data sources strip ──────────────────────────────────── */}
      <section className="overflow-hidden border-y border-slate-800 bg-slate-900/50 py-6">
        <p className="mb-4 text-center text-xs font-semibold uppercase tracking-widest text-slate-500">
          Powered by open data
        </p>
        <div className="flex animate-[slide_25s_linear_infinite] gap-10 whitespace-nowrap">
          {[...stack, ...stack].map((s, i) => (
            <span key={i} className="text-sm font-medium text-slate-400">
              {s}
            </span>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-6 py-24">
        <motion.h2
          className="mb-14 text-center text-4xl font-bold text-white"
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          custom={0}
          viewport={{ once: true }}
        >
          From raw signal to alert in minutes
        </motion.h2>
        <div className="relative flex flex-col gap-0">
          {[
            {
              step: "01",
              title: "Ingest",
              desc: "GitHub Actions cron jobs pull live data from 8 open sources every 5–15 min and upsert into PostGIS.",
              color: "text-orange-400",
            },
            {
              step: "02",
              title: "Detect",
              desc: "ML models (LSTM autoencoder, DBSCAN, U-Net, XGBoost) score anomalies and generate structured alerts.",
              color: "text-red-400",
            },
            {
              step: "03",
              title: "Explain",
              desc: "Local LLM (Ollama → Groq → Gemini fallback) generates plain-language explanations pushed over WebSocket.",
              color: "text-yellow-400",
            },
            {
              step: "04",
              title: "Act",
              desc: "Dashboard, SOS triage form, and REST API surface everything to citizens, officials, and downstream systems.",
              color: "text-green-400",
            },
          ].map((item, i) => (
            <motion.div
              key={item.step}
              className="flex gap-6 pb-10"
              custom={i}
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="flex flex-col items-center">
                <span className={`text-3xl font-black ${item.color}`}>{item.step}</span>
                {i < 3 && <div className="mt-2 h-full w-px bg-slate-700" />}
              </div>
              <div className="pb-2">
                <h3 className="mb-1 text-xl font-bold text-white">{item.title}</h3>
                <p className="text-slate-400">{item.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-2xl px-6 py-20 text-center">
        <motion.div
          className="rounded-2xl border border-orange-800/40 bg-gradient-to-br from-orange-950/60 to-red-950/40 p-12"
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          custom={0}
          viewport={{ once: true }}
        >
          <div className="mb-4 text-5xl">🌋</div>
          <h2 className="mb-4 text-3xl font-bold text-white">Ready to watch India in real-time?</h2>
          <p className="mb-8 text-slate-300">
            Free, open-source, and running on zero paid infrastructure. Fork it, deploy it, improve it.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/dashboard">
              <Button size="lg" className="bg-orange-600 px-8 hover:bg-orange-500">
                Launch Dashboard
              </Button>
            </Link>
            <Link to="/signup">
              <Button size="lg" variant="outline" className="border-slate-600 px-8">
                Create Account
              </Button>
            </Link>
          </div>
        </motion.div>
      </section>

      <Footer />
    </div>
  );
}
