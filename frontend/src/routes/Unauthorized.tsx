import { Link } from "react-router-dom";

export default function Unauthorized() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <div className="mb-2 text-7xl font-black text-primary/20">403</div>
      <h1 className="mb-3 text-2xl font-bold text-foreground">Access Denied</h1>
      <p className="mb-8 max-w-md text-sm text-muted-foreground">
        You do not have permission to view this page. Please contact your administrator if you
        believe this is a mistake.
      </p>
      <Link
        to="/dashboard"
        className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
