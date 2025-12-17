import { Plane, LogOut, X, RefreshCw, Loader2, Menu } from "lucide-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/hooks/use-auth";
import { useMemory } from "@/hooks/use-memory";
import { useState, useEffect } from "react";
import { usePreferences } from "@/hooks/use-preferences";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import type { CurrentPreferences } from "@/hooks/use-chat";

// Helper function to clean preference text
const cleanPreferenceText = (text: string): string => {
  return text.replace(" for general", "").trim();
};

interface ChatHeaderProps {
  onPreferencesRefresh?: () => void;
  externalRefreshTrigger?: number;
  onPreferencesChange?: (preferences: CurrentPreferences) => void;
}

export function ChatHeader({ onPreferencesRefresh, externalRefreshTrigger = 0, onPreferencesChange }: ChatHeaderProps) {
  const { user, logout } = useAuth();
  const { token } = useAuth();
  const [, navigate] = useLocation();
  const { preferences, setPreferences } = usePreferences(user?.id);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  // Use externalRefreshTrigger if provided, otherwise use internal state
  const effectiveRefreshTrigger = externalRefreshTrigger !== 0 ? externalRefreshTrigger : refreshTrigger;
  const { preferences: memoryPreferences, refreshPreferences, isLoadingPreferences, removePreference, isRemovingPreference } = useMemory(user?.id, effectiveRefreshTrigger);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [travelHistoryOpen, setTravelHistoryOpen] = useState(false);
  const [directFlightsOnly, setDirectFlightsOnly] = useState(false);
  const [avoidRedEye, setAvoidRedEye] = useState(false);
  const [preferredTime, setPreferredTime] = useState<string>("");
  const [cabinClass, setCabinClass] = useState<string>("");
  const [tripType, setTripType] = useState<string>("");
  const [isSavingCabinClass, setIsSavingCabinClass] = useState(false);
  const [isSavingAllPreferences, setIsSavingAllPreferences] = useState(false);

  // Listen for preference refresh events
  useEffect(() => {
    if (onPreferencesRefresh) {
      onPreferencesRefresh();
    }
  }, []);

  // Auto-refresh preferences when sheet opens
  useEffect(() => {
    if (preferencesOpen) {
      // Force refetch fresh data
      setTimeout(() => refreshPreferences(), 100);
    }
  }, [preferencesOpen, refreshPreferences]);

  // Notify parent when preferences change
  useEffect(() => {
    if (onPreferencesChange) {
      onPreferencesChange({
        directFlightsOnly,
        avoidRedEye,
        cabinClass,
        preferredTime,
        tripType,
      });
    }
  }, [directFlightsOnly, avoidRedEye, cabinClass, preferredTime, tripType, onPreferencesChange]);

  const handleRefreshPreferences = () => {
    setRefreshTrigger(prev => prev + 1);
    refreshPreferences();
  };

  const handleSaveAllPreferences = async () => {
    setIsSavingAllPreferences(true);
    try {
      // Delete old preferences in parallel
      const oldPrefsToDelete = [
        "Morning departures",
        "Afternoon departures",
        "Evening departures",
        "I prefer Business class flights",
        "I prefer Premium Economy class flights",
        "I prefer First Class class flights",
        "I prefer Economy class flights"
      ];

      await Promise.all(
        oldPrefsToDelete.map(oldPref =>
          fetch(`/api/memory/preferences/${encodeURIComponent(oldPref)}`, {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }).catch(() => {})
        )
      );

      // Build array of preferences to save
      const prefsToSave = [];

      if (directFlightsOnly) {
        prefsToSave.push(
          fetch("/api/memory/add-preference", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              category: "preference",
              type: "flight_type",
              content: "Direct flights only",
            }),
          })
        );
      }

      if (avoidRedEye) {
        prefsToSave.push(
          fetch("/api/memory/add-preference", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              category: "preference",
              type: "red_eye",
              content: "Avoid red-eye flights",
            }),
          })
        );
      }

      if (preferredTime) {
        const timeText = `${preferredTime} departures`;
        prefsToSave.push(
          fetch("/api/memory/add-preference", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              category: "preference",
              type: "departure_time",
              content: timeText,
            }),
          })
        );
      }

      if (cabinClass) {
        prefsToSave.push(
          fetch("/api/memory/add-preference", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              category: "preference",
              type: "cabin_class",
              content: `I prefer ${cabinClass} class flights`,
            }),
          })
        );
      }

      if (tripType) {
        prefsToSave.push(
          fetch("/api/memory/add-preference", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              category: "preference",
              type: "trip_type",
              content: `I prefer ${tripType} trips`,
            }),
          })
        );
      }

      // Save all preferences in parallel
      await Promise.all(prefsToSave);

      // Refresh preferences
      setRefreshTrigger(prev => prev + 1);
      refreshPreferences();
    } catch (error) {
      console.error("Error saving preferences:", error);
    } finally {
      setIsSavingAllPreferences(false);
    }
  };

  const handleDirectFlightsToggle = (checked: boolean) => {
    // Just update local state - Save button will handle actual saving
    setDirectFlightsOnly(checked);
  };

  const handleAvoidRedEyeToggle = (checked: boolean) => {
    // Just update local state - Save button will handle actual saving
    setAvoidRedEye(checked);
  };

  const handlePreferredTimeChange = (value: string) => {
    // Just update local state - Save button will handle actual saving
    setPreferredTime(value);
  };

  const handleCabinClassChange = (value: string) => {
    // Just update local state - Save button will handle actual saving
    setCabinClass(value);
  };

  const handleTripTypeChange = (value: string) => {
    // Just update local state - Save button will handle actual saving
    setTripType(value);
  };

  const handleRemovePreference = (preference: any) => {
    const prefText = typeof preference === "string" ? preference : preference.text || preference.memory;
    removePreference(prefText);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initials = user?.fullName
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase() || user?.username[0].toUpperCase() || "U";

  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <Plane className="h-5 w-5 text-primary-foreground" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold leading-tight">SkyMate</h1>
          <p className="text-xs text-muted-foreground">AI Travel Assistant</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        {/* Travel Preferences Sheet */}
        <Sheet open={preferencesOpen} onOpenChange={(open) => {
          setPreferencesOpen(open);
          // Refresh preferences when sheet opens
          if (open) {
            setTimeout(() => refreshPreferences(), 100);
          }
        }}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPreferencesOpen(true)}
            title="Travel Preferences"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Travel Preferences</span>
          </Button>
          
          <SheetContent side="right" className="w-full sm:w-[500px] overflow-y-auto">
            <SheetHeader>
              <SheetTitle className="text-2xl font-bold">✈️ Travel Preferences</SheetTitle>
            </SheetHeader>
            
            <div className="space-y-6 py-6">
              {/* Flight Preferences Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  🛫 Flight Preferences
                </h3>
                
                {/* Direct Flights Toggle */}
                <div className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
                  <Label htmlFor="direct-flights" className="cursor-pointer font-medium">
                    Direct Flights Only
                  </Label>
                  <Switch
                    id="direct-flights"
                    checked={directFlightsOnly}
                    onCheckedChange={handleDirectFlightsToggle}
                  />
                </div>

                {/* Avoid Red-Eye Toggle */}
                <div className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
                  <Label htmlFor="avoid-red-eye" className="cursor-pointer font-medium">
                    Avoid Red-Eye Flights
                  </Label>
                  <Switch
                    id="avoid-red-eye"
                    checked={avoidRedEye}
                    onCheckedChange={handleAvoidRedEyeToggle}
                  />
                </div>
              </div>

              {/* Cabin Class Section */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  🪑 Cabin Class
                </h3>
                <div className="flex items-center gap-2">
                  <select
                    value={cabinClass}
                    onChange={(e) => handleCabinClassChange(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-background text-sm"
                  >
                    <option value="">Select cabin class</option>
                    <option value="Economy">Economy</option>
                    <option value="Premium Economy">Premium Economy</option>
                    <option value="Business">Business</option>
                    <option value="First Class">First Class</option>
                  </select>
                </div>
              </div>

              {/* Preferred Time Section */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  🕐 Preferred Departure Time
                </h3>
                <select
                  value={preferredTime}
                  onChange={(e) => handlePreferredTimeChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-sm"
                >
                  <option value="">Select preferred time</option>
                  <option value="Morning">Morning (6AM - 12PM)</option>
                  <option value="Afternoon">Afternoon (12PM - 6PM)</option>
                  <option value="Evening">Evening (6PM - 11PM)</option>
                </select>
              </div>

              {/* Trip Type Section */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  ✈️ Trip Type
                </h3>
                <select
                  value={tripType}
                  onChange={(e) => handleTripTypeChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-sm"
                >
                  <option value="">Select trip type</option>
                  <option value="One-way">One-way</option>
                  <option value="Round trip">Round trip</option>
                </select>
              </div>

              {/* Save All Preferences Button */}
              <div className="border-t pt-4 mt-4">
                <Button
                  onClick={handleSaveAllPreferences}
                  disabled={isSavingAllPreferences || (!directFlightsOnly && !avoidRedEye && !preferredTime && !cabinClass && !tripType)}
                  className="w-full bg-primary hover:bg-primary/90"
                >
                  {isSavingAllPreferences ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      💾 Save All Preferences
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  Click to save all selections to memory
                </p>
              </div>

              {/* Saved Preferences Section - Show ALL current selections */}
              <div className="space-y-3 border-t pt-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    💾 Active Preferences
                  </h3>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleRefreshPreferences}
                    disabled={isLoadingPreferences}
                    className="h-6 w-6 p-0"
                    title="Refresh preferences"
                  >
                    <RefreshCw className={`h-3 w-3 ${isLoadingPreferences ? "animate-spin" : ""}`} />
                  </Button>
                </div>
                
                <div className="space-y-2">
                  {/* Show message if no stored preferences */}
                  {!(memoryPreferences && Object.values(memoryPreferences).some((cat: any) => cat?.length > 0)) && (
                    <p className="text-xs text-muted-foreground italic py-2">No stored preferences yet. Save your preferences above to see them here.</p>
                  )}
                  
                  {/* All mem0 preferences combined */}
                  {memoryPreferences?.seat && memoryPreferences.seat.length > 0 && memoryPreferences.seat.map((pref, i) => (
                    <div key={`seat-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>💺 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.flight_type && memoryPreferences.flight_type.length > 0 && memoryPreferences.flight_type.map((pref, i) => (
                    <div key={`flight-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🛫 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.cabin_class && memoryPreferences.cabin_class.length > 0 && memoryPreferences.cabin_class.map((pref, i) => (
                    <div key={`cabin-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🎫 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.departure_time && memoryPreferences.departure_time.length > 0 && memoryPreferences.departure_time.map((pref, i) => (
                    <div key={`time-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🕐 {cleanPreferenceText(typeof pref === "string" ? pref : pref.text || pref.memory)}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.red_eye && memoryPreferences.red_eye.length > 0 && memoryPreferences.red_eye.map((pref, i) => (
                    <div key={`red-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🌙 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.airline && memoryPreferences.airline.length > 0 && memoryPreferences.airline.map((pref, i) => (
                    <div key={`airline-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🏢 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.baggage && memoryPreferences.baggage.length > 0 && memoryPreferences.baggage.map((pref, i) => (
                    <div key={`bag-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🎒 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  
                  {memoryPreferences?.general && memoryPreferences.general.length > 0 && memoryPreferences.general.map((pref, i) => (
                    <div key={`gen-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>📌 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>                  ))}

                  {memoryPreferences?.passenger && memoryPreferences.passenger.length > 0 && memoryPreferences.passenger.map((pref, i) => (
                    <div key={`pax-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>👥 {cleanPreferenceText(typeof pref === "string" ? pref : pref.text || pref.memory)}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  {memoryPreferences?.trip_type && memoryPreferences.trip_type.length > 0 && memoryPreferences.trip_type.map((pref, i) => (
                    <div key={`trip-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🔄 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  {memoryPreferences?.budget && memoryPreferences.budget.length > 0 && memoryPreferences.budget.map((pref, i) => (
                    <div key={`budget-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>💰 {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  {memoryPreferences?.routes && memoryPreferences.routes.length > 0 && memoryPreferences.routes.map((pref, i) => (
                    <div key={`route-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>🗺️ {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  {memoryPreferences?.other && memoryPreferences.other.length > 0 && memoryPreferences.other.map((pref, i) => (
                    <div key={`other-${i}`} className="text-sm bg-green-50 dark:bg-green-950 p-3 rounded flex items-center justify-between group hover:bg-green-100 dark:hover:bg-green-900 transition-colors border border-green-200 dark:border-green-800">
                      <span>✨ {typeof pref === "string" ? pref : pref.text || pref.memory}</span>
                      <button
                        onClick={() => handleRemovePreference(pref)}
                        disabled={isRemovingPreference}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        title="Remove preference"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>                  ))}
                </div>
              </div>
            </div>
          </SheetContent>
        </Sheet>

        {/* Travel History Sheet */}
        <Sheet open={travelHistoryOpen} onOpenChange={setTravelHistoryOpen}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTravelHistoryOpen(true)}
            title="Travel History"
          >
            📚
            <span className="sr-only">Travel History</span>
          </Button>
          <SheetContent side="right" className="w-full sm:w-[500px] overflow-y-auto">
            <SheetHeader>
              <SheetTitle className="text-2xl font-bold">📚 Travel History</SheetTitle>
            </SheetHeader>
            
            <div className="space-y-6 py-6">
              <div className="space-y-3">
                <h3 className="text-lg font-semibold">📍 Frequently Used Routes</h3>
                <p className="text-sm text-muted-foreground">Your most traveled routes will appear here</p>
              </div>

              <div className="space-y-3">
                <h3 className="text-lg font-semibold">🎫 Previously Booked Flights</h3>
                <p className="text-sm text-muted-foreground">Your booking history will appear here</p>
              </div>

              <div className="space-y-3">
                <h3 className="text-lg font-semibold">⏱️ Duration Preferences</h3>
                <p className="text-sm text-muted-foreground">Your preferred trip durations will appear here</p>
              </div>
            </div>
          </SheetContent>
        </Sheet>

        <ThemeToggle />
        
        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user.avatar} />
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="flex items-center justify-start gap-2 p-2">
                <div className="flex flex-col space-y-1 leading-none">
                  <p className="font-medium">{user.username}</p>
                  <p className="w-200 truncate text-sm text-muted-foreground">
                    {user.email}
                  </p>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/profile")}>
                My Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}
