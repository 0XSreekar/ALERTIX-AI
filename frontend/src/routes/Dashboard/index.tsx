import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { getUser, signOut, checkTokenExpiry } from "@/lib/localAuth";
import RegionSelector from "@/components/RegionSelector";
import Footer from "@/components/Footer";
import { cn } from "@/lib/utils";

const tabs = [
  { path: "sentinel", label: "Sentinel", icon: "🛰️", minRole: "citizen" },
  { path: "earthquake", label: "Earthquake", icon: "🔴", minRole: "citizen" },
  { path: "flood", label: "Flood", icon: "🔵", minRole: "citizen" },
  { path: "cyclone", label: "Cyclone", icon: "🟣", minRole: "citizen" },
  { path: "wildfire", label: "Wildfire", icon: "🟠", minRole: "citizen" },
  { path: "landslide", label: "Landslide", icon: "🟤", minRole: "citizen" },
  { path: "damage", label: "Damage", icon: "⬜", minRole: "citizen" },
  { path: "sos", label: "SOS", icon: "🆘", minRole: "citizen" },
  { path: "alerts", label: "Alerts", icon: "🔔", minRole: "citizen" },
] as const;

const ROLE_LEVEL: Record<string, number> = {
  citizen: 0,
  official: 1,
  admin: 2,
};

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();

  // Auth check (backup – ProtectedRoute handles the primary redirect)
  checkTokenExpiry();
  const user = getUser();
  if (!user) {
    navigate("/login");
    return null;
  }

  const userLevel = ROLE_LEVEL[user.role] ?? 0;
  const visibleTabs = tabs.filter((t) => userLevel >= (ROLE_LEVEL[t.minRole] ?? 0));

  const handleLogout = () => {
    signOut();
    navigate("/");
  };

  const activeTab = location.pathname.split("/").pop() || "earthquake";

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-4">
          <Link to="/" className="text-lg font-bold text-primary">
            Alertix AI
          </Link>
          <div className="flex items-center gap-3">
            <RegionSelector />
            {user.role === "admin" && (
              <Link
                to="/admin"
                className="rounded-md border border-red-800/50 px-2.5 py-1 text-xs font-semibold text-red-400 hover:bg-red-950/30"
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={handleLogout}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="hidden w-52 shrink-0 border-r bg-card p-4 lg:block">
          <nav className="flex flex-col gap-1">
            {visibleTabs.map((tab) => (
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
          {visibleTabs.map((tab) => (
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
