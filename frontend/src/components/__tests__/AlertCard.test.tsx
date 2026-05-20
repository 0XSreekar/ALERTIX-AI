import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AlertCard from "../AlertCard";
import type { Alert } from "@/lib/types";

const mockAlert: Alert = {
  id: "test-123",
  hazard_type: "earthquake",
  severity: "warning",
  title: "M5.2 Earthquake near Delhi",
  explanation: "A moderate earthquake was detected 50km NE of Delhi.",
  explanation_lang: "en",
  explanation_status: "done",
  probability: 0.75,
  event_ids: ["ev1"],
  model_version: "v1",
  created_at: "2026-05-20T10:00:00Z",
  expires_at: null,
};

describe("AlertCard", () => {
  it("renders alert title and severity", () => {
    render(<AlertCard alert={mockAlert} />);
    expect(screen.getByText("M5.2 Earthquake near Delhi")).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
  });

  it("renders explanation when available", () => {
    render(<AlertCard alert={mockAlert} />);
    expect(
      screen.getByText(/A moderate earthquake was detected/),
    ).toBeInTheDocument();
  });

  it("shows pending message when no explanation", () => {
    const pending = { ...mockAlert, explanation: null, explanation_status: "pending" as const };
    render(<AlertCard alert={pending} />);
    expect(screen.getByText(/pending/)).toBeInTheDocument();
  });

  it("shows probability", () => {
    render(<AlertCard alert={mockAlert} />);
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(<AlertCard alert={mockAlert} onClick={onClick} />);
    (screen.getByText("M5.2 Earthquake near Delhi").closest("[class]") as HTMLElement | null)?.click();
    expect(onClick).toHaveBeenCalled();
  });
});
