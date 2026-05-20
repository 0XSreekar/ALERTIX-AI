import RiskGauge from "@/components/RiskGauge";
import HazardMap from "@/components/Map";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LandslideTab() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Landslide Risk</h2>
      <p className="text-sm text-muted-foreground">
        GSI landslide hazard zonation overlay with intensity-duration rainfall threshold rules.
        Phase 2 will add XGBoost susceptibility model.
      </p>

      <HazardMap events={[]} className="h-[400px] w-full rounded-lg lg:h-[500px]" />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rainfall Threshold Status</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Monitoring cumulative rainfall against published intensity-duration thresholds
              for landslide-prone Indian districts.
            </p>
            <RiskGauge value={0} label="Threshold Exceedance" className="mt-4" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">GSI Hazard Zones</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Static overlay from Geological Survey of India landslide hazard zonation maps.
              GeoJSON overlay will be loaded when GSI data is imported.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
