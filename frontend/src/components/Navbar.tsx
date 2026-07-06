import { Link, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { getUser, signOut, verifySession, type LocalUser } from "@/lib/localAuth";
import { Button } from "@/components/ui/button";

export default function Navbar() {
  const [user, setUser] = useState<LocalUser | null>(() => getUser());
  const navigate = useNavigate();

  useEffect(() => {
    void verifySession().then(setUser);
    const onStorage = () => setUser(getUser());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleLogout = async () => {
    await signOut();
    setUser(null);
    navigate("/");
  };

  const isAdmin = user?.role === "admin";
  const isOfficial = user?.role === "official" || user?.role === "admin";

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link to="/" className="text-lg font-bold text-primary">
          Alertix AI
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/about" className="text-sm text-muted-foreground hover:text-foreground">
            About
          </Link>
          <Link to="/contact" className="text-sm text-muted-foreground hover:text-foreground">
            Contact
          </Link>
          {user ? (
            <>
              <Link to="/dashboard">
                <Button size="sm">Dashboard</Button>
              </Link>
              {isOfficial && (
                <Link
                  to="/dashboard/sos"
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  SOS Triage
                </Link>
              )}
              {isAdmin && (
                <Link to="/admin">
                  <Button size="sm" variant="outline" className="border-red-800/50 text-red-400">
                    Admin
                  </Button>
                </Link>
              )}
              <Button size="sm" variant="ghost" onClick={handleLogout}>
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link to="/login">
                <Button size="sm" variant="ghost">Login</Button>
              </Link>
              <Link to="/signup">
                <Button size="sm">Sign Up</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
