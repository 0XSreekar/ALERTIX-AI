import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import RegionSelector from "@/components/RegionSelector";
import Footer from "@/components/Footer";
import { cn } from "@/lib/utils";

const tabs = [
  { path: "earthquake", label: "Earthquake", icon: "🔴" },
  { path: "flood", label: "Flood", icon: "🔵" },
  { path: "cyclone", label: "Cyclone", icon: "🟣" },
  { path: "wildfire", label: "Wildfire", icon: "🟠" },
  { path: "landslide", label: "Landslide", icon: "🟤" },
  { path: "damage", label: "Damage", icon: "⬜" },
  { path: "sos", label: "SOS", icon: "🆘" },
  { path: "alerts", label: "Alerts", icon: "🔔" },
];

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        navigate("/login");
      }
      setLoading(false);
    });
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const activeTab = location.pathname.split("/").pop() || "earthquake";

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-4">
          <Link to="/" className="text-lg font-bold text-primary">
            Alertix AI
          </Link>
          <RegionSelector />
          <button
            onClick={() => supabase.auth.signOut().then(() => navigate("/"))}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="hidden w-52 shrink-0 border-r bg-card p-4 lg:block">
          <nav className="flex flex-col gap-1">
            {tabs.map((tab) => (
              <Link
                key={tab.path}
                to={`/dashboard/${tab.path}`}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  activeTab === tab.path
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground",
                )}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Mobile tab bar */}
        <div className="flex overflow-x-auto border-b lg:hidden">
          {tabs.map((tab) => (
            <Link
              key={tab.path}
              to={`/dashboard/${tab.path}`}
              className={cn(
                "whitespace-nowrap px-4 py-3 text-xs",
                activeTab === tab.path
                  ? "border-b-2 border-primary font-medium text-primary"
                  : "text-muted-foreground",
              )}
            >
              {tab.icon} {tab.label}
            </Link>
          ))}
        </div>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      <Footer />
    </div>
  );
}
