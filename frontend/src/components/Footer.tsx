import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t bg-card px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-8 sm:grid-cols-3">
          <div>
            <h3 className="mb-2 text-sm font-semibold">Alertix AI</h3>
            <p className="text-xs text-muted-foreground">
              Real-time multi-hazard intelligence for India.
            </p>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Links</h3>
            <div className="flex flex-col gap-1 text-xs text-muted-foreground">
              <Link to="/about" className="hover:text-primary">About</Link>
              <Link to="/contact" className="hover:text-primary">Contact</Link>
              <Link to="/dashboard" className="hover:text-primary">Dashboard</Link>
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Legal</h3>
            <p className="text-xs text-muted-foreground">
              Alertix AI provides hazard intelligence for situational awareness. It is{" "}
              <strong>not</strong> a substitute for official warnings from IMD, NCS, NDRF, or
              state authorities. Do not rely on Alertix AI for life-safety decisions.
            </p>
          </div>
        </div>
        <div className="mt-6 border-t pt-4 text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} Alertix AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
