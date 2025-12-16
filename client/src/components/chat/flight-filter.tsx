import { useState } from "react";
import { X, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { FlightOffer } from "@shared/schema";

interface FlightFilterProps {
  flights: FlightOffer[];
  onFilter: (filtered: FlightOffer[]) => void;
  onClose?: () => void;
}

export function FlightFilter({ flights, onFilter, onClose }: FlightFilterProps) {
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 5000]);
  const [maxStops, setMaxStops] = useState<number | null>(null);
  const [selectedAirlines, setSelectedAirlines] = useState<Set<string>>(new Set());
  const [departureTime, setDepartureTime] = useState<string | null>(null);

  // Extract unique airlines from flights
  const airlines = Array.from(
    new Set(
      flights.flatMap((f) =>
        f.itineraries[0].segments.map((s) => s.carrierName || s.carrierCode)
      )
    )
  ).sort();

  // Apply filters
  const applyFilters = () => {
    let filtered = flights;

    // Filter by price
    filtered = filtered.filter(
      (f) =>
        parseFloat(f.price.total) >= priceRange[0] &&
        parseFloat(f.price.total) <= priceRange[1]
    );

    // Filter by max stops
    if (maxStops !== null) {
      filtered = filtered.filter((f) =>
        f.itineraries.every((itin) => itin.segments.length - 1 <= maxStops)
      );
    }

    // Filter by airlines
    if (selectedAirlines.size > 0) {
      filtered = filtered.filter((f) =>
        f.itineraries[0].segments.some((s) =>
          selectedAirlines.has(s.carrierName || s.carrierCode)
        )
      );
    }

    // Filter by departure time
    if (departureTime) {
      const [minHour, maxHour] = getDepartureTimeRange(departureTime);
      filtered = filtered.filter((f) => {
        const firstSegment = f.itineraries[0].segments[0];
        const departTime = new Date(firstSegment.departure.at);
        const hour = departTime.getHours();
        return hour >= minHour && hour < maxHour;
      });
    }

    onFilter(filtered);
  };

  const getDepartureTimeRange = (
    time: string
  ): [number, number] => {
    switch (time) {
      case "early-morning":
        return [5, 9];
      case "morning":
        return [9, 12];
      case "afternoon":
        return [12, 17];
      case "evening":
        return [17, 21];
      case "night":
        return [21, 5];
      default:
        return [0, 24];
    }
  };

  const handleAirlineToggle = (airline: string) => {
    const newSet = new Set(selectedAirlines);
    if (newSet.has(airline)) {
      newSet.delete(airline);
    } else {
      newSet.add(airline);
    }
    setSelectedAirlines(newSet);
  };

  const resetFilters = () => {
    setPriceRange([0, 5000]);
    setMaxStops(null);
    setSelectedAirlines(new Set());
    setDepartureTime(null);
    onFilter(flights);
  };

  const maxPrice = Math.max(...flights.map((f) => parseFloat(f.price.total)));

  return (
    <Card className="w-full border-l bg-card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm">Refine Results</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="space-y-4 max-h-[600px] overflow-y-auto">
        {/* Price Filter */}
        <div>
          <Label className="text-xs font-semibold mb-2 block">
            Price Range: ${priceRange[0]} - ${priceRange[1]}
          </Label>
          <Slider
            value={priceRange}
            onValueChange={setPriceRange}
            min={0}
            max={maxPrice}
            step={100}
            className="w-full"
          />
        </div>

        {/* Stops Filter */}
        <div>
          <Label className="text-xs font-semibold mb-2 block">Max Stops</Label>
          <div className="space-y-2">
            {[
              { value: 0, label: "Non-stop" },
              { value: 1, label: "1 Stop" },
              { value: 2, label: "2+ Stops" },
            ].map((option) => (
              <div key={option.value} className="flex items-center gap-2">
                <Checkbox
                  id={`stops-${option.value}`}
                  checked={maxStops === option.value}
                  onCheckedChange={() =>
                    setMaxStops(maxStops === option.value ? null : option.value)
                  }
                />
                <Label htmlFor={`stops-${option.value}`} className="text-xs cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </div>
        </div>

        {/* Departure Time */}
        <div>
          <Label className="text-xs font-semibold mb-2 block">
            Departure Time
          </Label>
          <div className="space-y-2">
            {[
              { value: "early-morning", label: "Early Morning (5am-9am)" },
              { value: "morning", label: "Morning (9am-12pm)" },
              { value: "afternoon", label: "Afternoon (12pm-5pm)" },
              { value: "evening", label: "Evening (5pm-9pm)" },
              { value: "night", label: "Night (9pm-5am)" },
            ].map((option) => (
              <div key={option.value} className="flex items-center gap-2">
                <Checkbox
                  id={`time-${option.value}`}
                  checked={departureTime === option.value}
                  onCheckedChange={() =>
                    setDepartureTime(
                      departureTime === option.value ? null : option.value
                    )
                  }
                />
                <Label htmlFor={`time-${option.value}`} className="text-xs cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </div>
        </div>

        {/* Airlines Filter */}
        {airlines.length > 0 && (
          <div>
            <Label className="text-xs font-semibold mb-2 block">Airlines</Label>
            <div className="space-y-2">
              {airlines.map((airline) => (
                <div key={airline} className="flex items-center gap-2">
                  <Checkbox
                    id={`airline-${airline}`}
                    checked={selectedAirlines.has(airline)}
                    onCheckedChange={() => handleAirlineToggle(airline)}
                  />
                  <Label
                    htmlFor={`airline-${airline}`}
                    className="text-xs cursor-pointer"
                  >
                    {airline}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2 mt-4">
        <Button
          size="sm"
          onClick={applyFilters}
          className="flex-1"
        >
          Apply Filters
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={resetFilters}
          className="flex-1"
        >
          Reset
        </Button>
      </div>
    </Card>
  );
}
