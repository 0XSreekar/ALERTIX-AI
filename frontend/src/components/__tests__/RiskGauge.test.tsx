import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RiskGauge from "../RiskGauge";

describe("RiskGauge", () => {
  it("renders label and value", () => {
    render(<RiskGauge value={45} label="Anomaly Score" />);
    expect(screen.getByText("Anomaly Score")).toBeInTheDocument();
    expect(screen.getByText(/45/)).toBeInTheDocument();
    expect(screen.getByText(/MODERATE/)).toBeInTheDocument();
  });

  it("shows LOW for low values", () => {
    render(<RiskGauge value={10} label="Test" />);
    expect(screen.getByText(/LOW/)).toBeInTheDocument();
  });

  it("shows HIGH for high values", () => {
    render(<RiskGauge value={85} label="Test" />);
    expect(screen.getByText(/HIGH/)).toBeInTheDocument();
  });

  it("clamps value to 0-100 range", () => {
    render(<RiskGauge value={150} label="Test" />);
    expect(screen.getByText(/100/)).toBeInTheDocument();
  });

  it("respects custom thresholds", () => {
    render(<RiskGauge value={45} label="Test" thresholds={{ low: 50, moderate: 80 }} />);
    expect(screen.getByText(/LOW/)).toBeInTheDocument();
  });
});
