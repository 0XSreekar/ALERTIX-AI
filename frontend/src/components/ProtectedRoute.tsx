import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getUser, verifySession, type LocalUser } from "@/lib/localAuth";

type Role = "citizen" | "official" | "admin";

const ROLE_HIERARCHY: Record<Role, number> = {
  citizen: 0,
  official: 1,
  admin: 2,
};

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: Role;
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  // Optimistic render from cached user metadata; verify against backend in the
  // background so a stale cookie/JWT triggers a redirect on the next tick.
  const [user, setUser] = useState<LocalUser | null>(() => getUser());
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void verifySession().then((fresh) => {
      if (cancelled) return;
      setUser(fresh);
      setVerified(true);
    });
    return () => { cancelled = true; };
  }, []);

  if (!user && verified) {
    return <Navigate to="/login" replace />;
  }
  if (!user) {
    // Pre-verification: avoid flashing the login redirect if cookie is valid.
    return null;
  }

  if (requiredRole) {
    const userLevel = ROLE_HIERARCHY[user.role as Role] ?? 0;
    const requiredLevel = ROLE_HIERARCHY[requiredRole];
    if (userLevel < requiredLevel) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
}
