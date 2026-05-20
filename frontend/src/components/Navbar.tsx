import { Link, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { getUser, signOut, type LocalUser } from "@/lib/localAuth";
import { Button } from "@/components/ui/button";

export default function Navbar() {
  const [user, setUser] = useState<LocalUser | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setUser(getUser());
    const onStorage = () => setUser(getUser());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleLogout = () => {
    signOut();
    setUser(null);
    navigate("/");
  };

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
