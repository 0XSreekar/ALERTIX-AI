import { Link } from "react-router-dom";
import { Suspense, lazy } from "react";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ThreeEarth = lazy(() => import("@/components/ThreeEarth"));

const features = [
  {
    title: "Earthquake Intelligence",
    description:
      "LSTM autoencoder anomaly detection on USGS seismicity, Omori aftershock probability, and real-time magnitude mapping.",
  },
  {
    title: "Flood Forecasting",
    description:
      "72-hour discharge prediction from CWC gauges and Open-Meteo rainfall, fused with Google Flood Hub, plus Sentinel-1 SAR extent mapping.",
  },
  {
    title: "Multi-Hazard Dashboard",
    description:
      "Cyclone track extrapolation, FIRMS wildfire clustering, landslide rainfall thresholds, and AI damage assessment — all on one live map.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="relative flex min-h-[80vh] items-center justify-center overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <Suspense
            fallback={
              <div className="flex h-full items-center justify-center bg-background">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            }
          >
            <ThreeEarth className="h-full w-full opacity-40" />
          </Suspense>
        </div>

        <div className="relative z-10 mx-auto max-w-3xl px-4 text-center">
          <motion.h1
            className="mb-4 text-4xl font-bold tracking-tight sm:text-6xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            Real-time multi-hazard intelligence for India
          </motion.h1>
          <motion.p
            className="mb-8 text-lg text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            Earthquake, flood, cyclone, wildfire, landslide, and damage assessment — powered by
            open data, open-source AI, and a locally-hosted LLM.
          </motion.p>
          <motion.div
            className="flex justify-center gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            <Link to="/dashboard">
              <Button size="lg">Open Dashboard</Button>
            </Link>
            <Link to="/about">
              <Button size="lg" variant="outline">
                Read the Docs
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-4 py-20">
        <h2 className="mb-12 text-center text-3xl font-bold">What Alertix AI Covers</h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15, duration: 0.5 }}
              viewport={{ once: true }}
            >
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="text-lg">{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{f.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <Footer />
    </div>
  );
}
