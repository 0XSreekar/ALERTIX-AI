import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as Tabs from "@radix-ui/react-tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  fetchAdminUsers,
  fetchAdminAlerts,
  fetchAuditLog,
  fetchSystemStatus,
  updateUserRole,
  deactivateUser,
  acknowledgeAlert,
  dismissAlert,
  type AdminUser,
  type AdminAlert,
  type AuditLogEntry,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { Link } from "react-router-dom";
import { signOut } from "@/lib/localAuth";
import { useNavigate } from "react-router-dom";

// ─── Overview ──────────────────────────────────────────────────────────────

function OverviewTab() {
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: queryKeys.admin.users(0),
    queryFn: () => fetchAdminUsers(0, 1),
  });
  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: queryKeys.admin.alerts(0),
    queryFn: () => fetchAdminAlerts(0, 1),
  });
  const { data: systemData, isLoading: systemLoading } = useQuery({
    queryKey: [...queryKeys.admin.systemStatus],
    queryFn: fetchSystemStatus,
  });

  const stats = [
    { label: "Total Users", value: usersData?.total ?? "—", loading: usersLoading },
    { label: "Total Alerts", value: alertsData?.total ?? "—", loading: alertsLoading },
    {
      label: "DB Status",
      value: systemData?.db_status ?? "—",
      loading: systemLoading,
      highlight: systemData?.db_status === "ok" ? "text-green-400" : "text-red-400",
    },
    {
      label: "Redis Status",
      value: systemData?.redis_status ?? "—",
      loading: systemLoading,
      highlight: systemData?.redis_status === "ok" ? "text-green-400" : "text-red-400",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-6">
              {s.loading ? (
                <Skeleton className="mb-2 h-8 w-20" />
              ) : (
                <p className={`text-3xl font-bold ${s.highlight ?? "text-foreground"}`}>
                  {String(s.value)}
                </p>
              )}
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {systemData && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Backend Version</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-sm">{systemData.backend_version}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Users ─────────────────────────────────────────────────────────────────

function UsersTab() {
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.admin.users(page),
    queryFn: () => fetchAdminUsers(page, PAGE_SIZE),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      updateUserRole(userId, role),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => deactivateUser(userId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-800/40 bg-red-950/20 p-6 text-center">
        <p className="text-sm text-red-400">Failed to load users.</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="p-3 text-left text-xs text-muted-foreground">ID</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Email</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Role</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Created</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data?.users ?? []).map((u: AdminUser) => (
              <tr key={u.user_id} className="border-b border-border/50 hover:bg-muted/30">
                <td className="p-3 font-mono text-xs text-muted-foreground">
                  {u.user_id.slice(0, 8)}…
                </td>
                <td className="p-3">{u.email}</td>
                <td className="p-3">
                  <select
                    defaultValue={u.role}
                    className="rounded border border-input bg-background px-2 py-1 text-xs"
                    onChange={(e) =>
                      roleMutation.mutate({ userId: u.user_id, role: e.target.value })
                    }
                  >
                    <option value="citizen">citizen</option>
                    <option value="official">official</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td className="p-3 text-xs text-muted-foreground">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="p-3">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-red-800/50 text-xs text-red-400 hover:bg-red-950/40"
                    onClick={() => deactivateMutation.mutate(u.user_id)}
                    disabled={!u.is_active}
                  >
                    {u.is_active ? "Deactivate" : "Inactive"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {page + 1} of {totalPages} ({data?.total ?? 0} total)
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Prev
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Alerts ────────────────────────────────────────────────────────────────

function AlertsAdminTab() {
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.admin.alerts(page),
    queryFn: () => fetchAdminAlerts(page, PAGE_SIZE),
  });

  const ackMutation = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "alerts"] }),
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => dismissAlert(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "alerts"] }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-800/40 bg-red-950/20 p-6 text-center">
        <p className="text-sm text-red-400">Failed to load alerts.</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="p-3 text-left text-xs text-muted-foreground">Type</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Severity</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Title</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Created</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Status</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data?.alerts ?? []).map((a: AdminAlert) => (
              <tr key={a.id} className="border-b border-border/50 hover:bg-muted/30">
                <td className="p-3 text-xs">{a.hazard_type}</td>
                <td className="p-3">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-xs font-semibold ${
                      a.severity === "emergency"
                        ? "bg-red-900/40 text-red-400"
                        : a.severity === "warning"
                          ? "bg-orange-900/40 text-orange-400"
                          : a.severity === "watch"
                            ? "bg-yellow-900/40 text-yellow-400"
                            : "bg-blue-900/40 text-blue-400"
                    }`}
                  >
                    {a.severity}
                  </span>
                </td>
                <td className="max-w-xs truncate p-3 text-xs">{a.title}</td>
                <td className="p-3 text-xs text-muted-foreground">
                  {new Date(a.created_at).toLocaleString()}
                </td>
                <td className="p-3 text-xs">{a.status}</td>
                <td className="flex gap-1 p-3">
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs"
                    onClick={() => ackMutation.mutate(a.id)}
                  >
                    Ack
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-red-800/50 text-xs text-red-400 hover:bg-red-950/40"
                    onClick={() => dismissMutation.mutate(a.id)}
                  >
                    Dismiss
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {page + 1} of {totalPages} ({data?.total ?? 0} total)
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Prev
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Audit Log ─────────────────────────────────────────────────────────────

function AuditLogTab() {
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.admin.auditLog(page),
    queryFn: () => fetchAuditLog(page, PAGE_SIZE),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-800/40 bg-red-950/20 p-6 text-center">
        <p className="text-sm text-red-400">Failed to load audit log.</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="p-3 text-left text-xs text-muted-foreground">Timestamp</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Action</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Entity Type</th>
              <th className="p-3 text-left text-xs text-muted-foreground">User ID</th>
              <th className="p-3 text-left text-xs text-muted-foreground">Details</th>
            </tr>
          </thead>
          <tbody>
            {(data?.entries ?? []).map((entry: AuditLogEntry) => (
              <tr key={entry.id} className="border-b border-border/50 hover:bg-muted/30">
                <td className="p-3 text-xs text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleString()}
                </td>
                <td className="p-3 text-xs font-medium">{entry.action}</td>
                <td className="p-3 text-xs">{entry.entity_type}</td>
                <td className="p-3 font-mono text-xs text-muted-foreground">
                  {entry.user_id ? `${entry.user_id.slice(0, 8)}…` : "—"}
                </td>
                <td className="max-w-xs truncate p-3 text-xs text-muted-foreground">
                  {entry.details ? JSON.stringify(entry.details) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {page + 1} of {totalPages} ({data?.total ?? 0} total)
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Prev
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── System Config ─────────────────────────────────────────────────────────

function SystemConfigTab() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [...queryKeys.admin.systemStatus],
    queryFn: fetchSystemStatus,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-800/40 bg-red-950/20 p-6 text-center">
        <p className="text-sm text-red-400">Failed to load system config.</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-lg font-bold">{data?.backend_version ?? "—"}</p>
            <p className="text-xs text-muted-foreground">Backend Version</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p
              className={`text-lg font-bold ${data?.db_status === "ok" ? "text-green-400" : "text-red-400"}`}
            >
              {data?.db_status ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">Database</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p
              className={`text-lg font-bold ${data?.redis_status === "ok" ? "text-green-400" : "text-red-400"}`}
            >
              {data?.redis_status ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">Redis</p>
          </CardContent>
        </Card>
      </div>

      {data?.env_config && Object.keys(data.env_config).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Environment Config (non-secret)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="p-3 text-left text-xs text-muted-foreground">Key</th>
                    <th className="p-3 text-left text-xs text-muted-foreground">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.env_config).map(([k, v]) => (
                    <tr key={k} className="border-b border-border/50">
                      <td className="p-3 font-mono text-xs">{k}</td>
                      <td className="p-3 font-mono text-xs text-muted-foreground">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Root ──────────────────────────────────────────────────────────────────

const TAB_ITEMS = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "Users" },
  { id: "alerts", label: "Alerts" },
  { id: "audit", label: "Audit Log" },
  { id: "system", label: "System Config" },
];

export default function AdminDashboard() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-lg font-bold text-primary">
              Alertix AI
            </Link>
            <span className="rounded bg-red-900/40 px-2 py-0.5 text-xs font-semibold text-red-400">
              ADMIN
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/dashboard"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Dashboard
            </Link>
            <Button size="sm" variant="ghost" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-[1400px] px-4 py-6">
        <h1 className="mb-6 text-2xl font-bold">Admin Panel</h1>

        <Tabs.Root defaultValue="overview">
          <Tabs.List className="mb-6 flex gap-1 border-b">
            {TAB_ITEMS.map((tab) => (
              <Tabs.Trigger
                key={tab.id}
                value={tab.id}
                className="rounded-t-md px-4 py-2 text-sm text-muted-foreground transition-colors data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:font-medium data-[state=active]:text-foreground"
              >
                {tab.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <Tabs.Content value="overview">
            <OverviewTab />
          </Tabs.Content>
          <Tabs.Content value="users">
            <UsersTab />
          </Tabs.Content>
          <Tabs.Content value="alerts">
            <AlertsAdminTab />
          </Tabs.Content>
          <Tabs.Content value="audit">
            <AuditLogTab />
          </Tabs.Content>
          <Tabs.Content value="system">
            <SystemConfigTab />
          </Tabs.Content>
        </Tabs.Root>
      </main>
    </div>
  );
}
