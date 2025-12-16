import { MapPin, Calendar, Users, Briefcase } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface JourneySummary {
  origin?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
  passengers?: number;
  cabinClass?: string;
  preferences?: string[];
}

interface JourneySummaryProps {
  summary: JourneySummary;
}

export function JourneySummary({ summary }: JourneySummaryProps) {
  const hasInfo = summary.origin || summary.destination || summary.departureDate;

  if (!hasInfo) {
    return null;
  }

  return (
    <Card className="p-3 bg-gradient-to-r from-primary/5 to-accent/5 border-primary/20">
      <div className="space-y-2">
        {/* Route */}
        {(summary.origin || summary.destination) && (
          <div className="flex items-center gap-2 text-sm">
            <MapPin className="h-4 w-4 text-primary" />
            <span className="font-medium">
              {summary.origin || "TBD"} → {summary.destination || "TBD"}
            </span>
          </div>
        )}

        {/* Dates */}
        {summary.departureDate && (
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-primary" />
            <span>
              {summary.departureDate}
              {summary.returnDate ? ` → ${summary.returnDate}` : " (One-way)"}
            </span>
          </div>
        )}

        {/* Passengers & Class */}
        <div className="flex gap-4 text-sm">
          {summary.passengers && (
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              <span>{summary.passengers} passenger{summary.passengers > 1 ? "s" : ""}</span>
            </div>
          )}
          {summary.cabinClass && (
            <div className="flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-primary" />
              <span>{summary.cabinClass}</span>
            </div>
          )}
        </div>

        {/* Preferences */}
        {summary.preferences && summary.preferences.length > 0 && (
          <div className="pt-2 border-t border-primary/10">
            <div className="text-xs font-semibold mb-1 text-muted-foreground">Your Preferences:</div>
            <div className="flex flex-wrap gap-1">
              {summary.preferences.map((pref, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs">
                  {pref}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
