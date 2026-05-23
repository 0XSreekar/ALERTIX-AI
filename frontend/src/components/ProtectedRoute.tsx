import { Navigate } from "react-router-dom";
import { getUser } from "@/lib/localAuth";
import { checkTokenExpiry } from "@/lib/localAuth";

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
  // Check and clear expired token before reading user
  checkTokenExpiry();

  const user = getUser();

  if (!user) {
    return <Navigate to="/login" replace />;
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
