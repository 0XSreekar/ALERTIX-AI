import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <div className="mb-2 text-7xl font-black text-primary/20">404</div>
      <h1 className="mb-3 text-2xl font-bold text-foreground">Page Not Found</h1>
      <p className="mb-8 max-w-md text-sm text-muted-foreground">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
      >
        Back to Home
      </Link>
    </div>
  );
}
