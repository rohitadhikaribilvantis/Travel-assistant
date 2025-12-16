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

interface ChatHeaderProps {
  onPreferencesRefresh?: () => void;
}

export function ChatHeader({ onPreferencesRefresh }: ChatHeaderProps) {
  const { user, logout } = useAuth();
  const { token } = useAuth();
  const [, navigate] = useLocation();
  const { preferences, setPreferences } = usePreferences(user?.id);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const { preferences: memoryPreferences, refreshPreferences, isLoadingPreferences, removePreference, isRemovingPreference } = useMemory(user?.id, refreshTrigger);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [directFlightsOnly, setDirectFlightsOnly] = useState(false);
  const [avoidRedEye, setAvoidRedEye] = useState(false);
  const [preferredTime, setPreferredTime] = useState<string>("");
  const [cabinClass, setCabinClass] = useState<string>("Economy");
  const [isSavingCabinClass, setIsSavingCabinClass] = useState(false);

  // Listen for preference refresh events
  useEffect(() => {
    if (onPreferencesRefresh) {
      onPreferencesRefresh();
    }
  }, []);

  const handleRefreshPreferences = () => {
    setRefreshTrigger(prev => prev + 1);
    refreshPreferences();
  };

  const handleDirectFlightsToggle = async (checked: boolean) => {
    setDirectFlightsOnly(checked);
    try {
      if (checked) {
        await fetch("/api/memory/add-preference", {
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
        });
      } else {
        await fetch("/api/memory/preferences/Direct%20flights%20only", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
      }
      setRefreshTrigger(prev => prev + 1);
      refreshPreferences();
    } catch (error) {
      console.error("Error saving direct flights preference:", error);
    }
  };

  const handleAvoidRedEyeToggle = async (checked: boolean) => {
    setAvoidRedEye(checked);
    try {
      if (checked) {
        await fetch("/api/memory/add-preference", {
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
        });
      } else {
        await fetch("/api/memory/preferences/Avoid%20red-eye%20flights", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
      }
      setRefreshTrigger(prev => prev + 1);
      refreshPreferences();
    } catch (error) {
      console.error("Error saving red-eye preference:", error);
    }
  };

  const handlePreferredTimeChange = async (value: string) => {
    setPreferredTime(value);
    try {
      if (value) {
        const timeText = `${value} departures`;
        await fetch("/api/memory/add-preference", {
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
        });
      } else {
        // Try to delete any existing time preferences
        await fetch(`/api/memory/preferences/${encodeURIComponent("Morning departures")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
        await fetch(`/api/memory/preferences/${encodeURIComponent("Afternoon departures")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
        await fetch(`/api/memory/preferences/${encodeURIComponent("Evening departures")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
      }
      setRefreshTrigger(prev => prev + 1);
      refreshPreferences();
    } catch (error) {
      console.error("Error saving time preference:", error);
    }
  };

  const handleCabinClassChange = async (value: string) => {
    setCabinClass(value);
    setIsSavingCabinClass(true);
    try {
      if (value && value !== "Economy") {
        await fetch("/api/memory/add-preference", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            category: "preference",
            type: "cabin_class",
            content: `I prefer ${value} class flights`,
          }),
        });
      } else if (value === "Economy") {
        // Delete premium cabin preferences
        await fetch(`/api/memory/preferences/${encodeURIComponent("I prefer Business class flights")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
        await fetch(`/api/memory/preferences/${encodeURIComponent("I prefer Premium Economy class flights")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
        await fetch(`/api/memory/preferences/${encodeURIComponent("I prefer First Class class flights")}`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {});
      }
      setRefreshTrigger(prev => prev + 1);
      refreshPreferences();
    } catch (error) {
      console.error("Error saving cabin class preference:", error);
    } finally {
      setIsSavingCabinClass(false);
    }
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
        <Sheet open={preferencesOpen} onOpenChange={setPreferencesOpen}>
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
                    disabled={isSavingCabinClass}
                    className="w-full px-3 py-2 border rounded-lg bg-background text-sm disabled:opacity-50"
                  >
                    <option>Economy</option>
                    <option>Premium Economy</option>
                    <option>Business</option>
                    <option>First Class</option>
                  </select>
                  {isSavingCabinClass && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
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

              {/* Saved Preferences Section */}
              {(directFlightsOnly || avoidRedEye || memoryPreferences && Object.values(memoryPreferences).some((cat: any) => cat?.length > 0)) && (
                <div className="space-y-3 border-t pt-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      💾 Saved Preferences
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
                    {/* Direct Flights Toggle Preference */}
                    {directFlightsOnly && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🛫 Flight Type</p>
                        <div className="space-y-1">
                          <div className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                            <span>Direct flights only</span>
                            <button
                              onClick={() => setDirectFlightsOnly(false)}
                              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                              title="Remove preference"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Avoid Red-Eye Toggle Preference */}
                    {avoidRedEye && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🌙 Red-eye</p>
                        <div className="space-y-1">
                          <div className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                            <span>Avoid red-eye flights</span>
                            <button
                              onClick={() => setAvoidRedEye(false)}
                              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                              title="Remove preference"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Cabin Class Preference */}
                    {cabinClass && cabinClass !== "Economy" && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🪑 Cabin Class</p>
                        <div className="space-y-1">
                          <div className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                            <span>{cabinClass}</span>
                            <button
                              onClick={() => setCabinClass("Economy")}
                              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                              title="Remove preference"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Departure Time Preference */}
                    {preferredTime && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🕐 Departure Time</p>
                        <div className="space-y-1">
                          <div className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                            <span>{preferredTime} departures</span>
                            <button
                              onClick={() => setPreferredTime("")}
                              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                              title="Remove preference"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Seat Preferences */}
                    {memoryPreferences?.seat && memoryPreferences.seat.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">💺 Seating</p>
                        <div className="space-y-1">
                          {memoryPreferences.seat.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Flight Type */}
                    {memoryPreferences?.flight_type && memoryPreferences.flight_type.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🛫 Flight Type</p>
                        <div className="space-y-1">
                          {memoryPreferences.flight_type.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Cabin Class */}
                    {memoryPreferences?.cabin_class && memoryPreferences.cabin_class.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🎫 Cabin Class</p>
                        <div className="space-y-1">
                          {memoryPreferences.cabin_class.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Departure Time */}
                    {memoryPreferences?.departure_time && memoryPreferences.departure_time.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🕐 Departure Time</p>
                        <div className="space-y-1">
                          {memoryPreferences.departure_time.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Red-eye preferences */}
                    {memoryPreferences?.red_eye && memoryPreferences.red_eye.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🌙 Red-eye</p>
                        <div className="space-y-1">
                          {memoryPreferences.red_eye.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Airline Preferences */}
                    {memoryPreferences?.airline && memoryPreferences.airline.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">✈️ Airlines</p>
                        <div className="space-y-1">
                          {memoryPreferences.airline.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* Baggage preferences */}
                    {memoryPreferences?.baggage && memoryPreferences.baggage.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">🎒 Baggage</p>
                        <div className="space-y-1">
                          {memoryPreferences.baggage.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                    
                    {/* General preferences */}
                    {memoryPreferences?.general && memoryPreferences.general.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">📋 Other</p>
                        <div className="space-y-1">
                          {memoryPreferences.general.map((pref, i) => (
                            <div key={i} className="text-sm bg-primary/10 p-2 rounded flex items-center justify-between group hover:bg-primary/20 transition-colors">
                              <span>{typeof pref === "string" ? pref : pref.text || pref.memory}</span>
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
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
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
