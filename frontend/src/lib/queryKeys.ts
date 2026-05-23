/**
 * Centralised TanStack Query key factory.
 * Import `queryKeys` everywhere instead of using raw string literals.
 */
export const queryKeys = {
  // Events
  events: {
    all: ["events"] as const,
    recent: (hazardType: string, hours: number) =>
      ["events", hazardType, "recent", hours] as const,
    byId: (id: string) => ["events", id] as const,
  },

  // Alerts
  alerts: {
    all: ["alerts"] as const,
    byId: (id: string) => ["alerts", id] as const,
  },

  // SOS
  sos: {
    mine: ["sos", "mine"] as const,
    feed: (minUrgency: number) => ["sos", "feed", minUrgency] as const,
  },

  // Predictions
  predict: {
    earthquake: (lat: number, lon: number, radiusKm: number) =>
      ["predict", "earthquake", lat, lon, radiusKm] as const,
    flood: (basinId: string) => ["predict", "flood", basinId] as const,
    wildfire: (bbox: string) => ["predict", "wildfire", bbox] as const,
    landslide: (lat: number, lon: number) => ["predict", "landslide", lat, lon] as const,
  },

  // Admin
  admin: {
    users: (page: number) => ["admin", "users", page] as const,
    alerts: (page: number) => ["admin", "alerts", page] as const,
    auditLog: (page: number) => ["admin", "audit-log", page] as const,
    systemStatus: ["admin", "system-status"] as const,
    overview: ["admin", "overview"] as const,
  },
} as const;
