import { Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";

const Landing = lazy(() => import("@/routes/Landing"));
const About = lazy(() => import("@/routes/About"));
const Contact = lazy(() => import("@/routes/Contact"));
const Login = lazy(() => import("@/routes/Login"));
const Signup = lazy(() => import("@/routes/Signup"));
const Dashboard = lazy(() => import("@/routes/Dashboard"));
const EarthquakeTab = lazy(() => import("@/routes/Dashboard/EarthquakeTab"));
const FloodTab = lazy(() => import("@/routes/Dashboard/FloodTab"));
const CycloneTab = lazy(() => import("@/routes/Dashboard/CycloneTab"));
const WildfireTab = lazy(() => import("@/routes/Dashboard/WildfireTab"));
const LandslideTab = lazy(() => import("@/routes/Dashboard/LandslideTab"));
const DamageTab = lazy(() => import("@/routes/Dashboard/DamageTab"));
const SosTab = lazy(() => import("@/routes/Dashboard/SosTab"));
const AlertsTab = lazy(() => import("@/routes/Dashboard/AlertsTab"));
const SentinelTab = lazy(() => import("@/routes/Dashboard/SentinelTab"));
const AdminDashboard = lazy(() => import("@/routes/AdminDashboard"));
const Unauthorized = lazy(() => import("@/routes/Unauthorized"));
const NotFound = lazy(() => import("@/routes/NotFound"));

function LoadingFallback() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        {/* Protected citizen+ routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute requiredRole="citizen">
              <Dashboard />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="sentinel" replace />} />
          <Route path="sentinel" element={<SentinelTab />} />
          <Route path="earthquake" element={<EarthquakeTab />} />
          <Route path="flood" element={<FloodTab />} />
          <Route path="cyclone" element={<CycloneTab />} />
          <Route path="wildfire" element={<WildfireTab />} />
          <Route path="landslide" element={<LandslideTab />} />
          <Route path="damage" element={<DamageTab />} />
          <Route path="sos" element={<SosTab />} />
          <Route path="alerts" element={<AlertsTab />} />
        </Route>

        {/* Protected admin-only routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AdminDashboard />
            </ProtectedRoute>
          }
        />

        {/* 404 catch-all */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
