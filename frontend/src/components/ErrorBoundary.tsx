import React from "react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary] Unhandled error:", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
          <div className="mb-6 text-5xl font-black tracking-tight text-primary">
            Alertix <span className="text-orange-500">AI</span>
          </div>
          <h1 className="mb-3 text-2xl font-bold text-foreground">Something went wrong</h1>
          <p className="mb-2 max-w-md text-sm text-muted-foreground">
            An unexpected error occurred. Please reload the page. If the problem persists, contact
            support.
          </p>
          {this.state.error && (
            <pre className="mb-6 max-w-xl overflow-x-auto rounded-lg border border-border bg-secondary p-4 text-left text-xs text-muted-foreground">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={this.handleReload}
            className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
