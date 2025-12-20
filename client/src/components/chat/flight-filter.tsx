import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
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
  const maxPrice = useMemo(() => {
    const prices = flights
      .map((f) => Number.parseFloat(f.price.total))
      .filter((n) => Number.isFinite(n));
    return prices.length ? Math.ceil(Math.max(...prices)) : 0;
  }, [flights]);

  const [priceRange, setPriceRange] = useState<[number, number]>([0, maxPrice]);
  const [maxStops, setMaxStops] = useState<Set<number>>(new Set());
  const [selectedAirlines, setSelectedAirlines] = useState<Set<string>>(new Set());

  // When the flight list changes (new search / new message), reset defaults.
  useEffect(() => {
    setPriceRange([0, maxPrice]);
    setMaxStops(new Set());
    setSelectedAirlines(new Set());
    const sorted = sortFlights(flights);
    onFilter(sorted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maxPrice, flights]);

  // Extract unique airlines from flights
  const airlines = Array.from(
    new Set(
      flights.flatMap((f) =>
        f.itineraries[0].segments.map((s) => s.carrierName || s.carrierCode)
      )
    )
  ).sort();

  // Sort flights by preference: best > cheapest > fastest > rest
  const sortFlights = (flightsToSort: FlightOffer[]) => {
    return [...flightsToSort].sort((a, b) => {
      const aTagPriority = getTagPriority(a.tags);
      const bTagPriority = getTagPriority(b.tags);
      if (aTagPriority !== bTagPriority) {
        return aTagPriority - bTagPriority;
      }
      return 0;
    });
  };

  const getTagPriority = (tags?: string[]) => {
    if (!tags || tags.length === 0) return 999;
    if (tags.includes("best")) return 1;
    if (tags.includes("cheapest")) return 2;
    if (tags.includes("fastest")) return 3;
    return 999;
  };

  // Apply filters
  const applyFilters = () => {
    let filtered = flights;

    // Filter by price
    filtered = filtered.filter(
      (f) =>
        parseFloat(f.price.total) >= priceRange[0] &&
        parseFloat(f.price.total) <= priceRange[1]
    );

    // Filter by max stops - allow multiple selections
    if (maxStops.size > 0) {
      filtered = filtered.filter((f) => {
        const flightStops = f.itineraries[0].segments.length - 1;
        return Array.from(maxStops).some((selectedStops) => 
          selectedStops === 2 ? flightStops >= 2 : flightStops <= selectedStops
        );
      });
    }

    // Filter by airlines
    if (selectedAirlines.size > 0) {
      filtered = filtered.filter((f) =>
        f.itineraries[0].segments.some((s) =>
          selectedAirlines.has(s.carrierName || s.carrierCode)
        )
      );
    }

    // Sort results
    const sorted = sortFlights(filtered);
    onFilter(sorted);
  };

  const handleStopsToggle = (stops: number) => {
    const newSet = new Set(maxStops);
    if (newSet.has(stops)) {
      newSet.delete(stops);
    } else {
      newSet.add(stops);
    }
    setMaxStops(newSet);
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
    setPriceRange([0, maxPrice]);
    setMaxStops(new Set());
    setSelectedAirlines(new Set());
    const sorted = sortFlights(flights);
    onFilter(sorted);
  };


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
          <div className="flex items-center justify-between mb-3">
            <Label className="text-xs font-semibold">Min: ${priceRange[0]}</Label>
            <Label className="text-xs font-semibold">Max: ${priceRange[1]}</Label>
          </div>
          <div className="space-y-2">
            <Slider
              value={[priceRange[0]]}
              onValueChange={(value) =>
                setPriceRange([Math.min(value[0], priceRange[1]), priceRange[1]])
              }
              min={0}
              max={maxPrice}
              step={50}
              className="w-full"
            />
            <Slider
              value={[priceRange[1]]}
              onValueChange={(value) =>
                setPriceRange([priceRange[0], Math.max(value[0], priceRange[0])])
              }
              min={0}
              max={maxPrice}
              step={50}
              className="w-full"
            />
          </div>
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
                  checked={maxStops.has(option.value)}
                  onCheckedChange={() => handleStopsToggle(option.value)}
                />
                <Label htmlFor={`stops-${option.value}`} className="text-xs cursor-pointer">
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
