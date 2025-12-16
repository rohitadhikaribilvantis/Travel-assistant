import { Plane, Settings, LogOut, X } from "lucide-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/hooks/use-auth";
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

interface ChatHeaderProps {
  // No longer needed
}

export function ChatHeader({ }: ChatHeaderProps) {
  const { user, logout } = useAuth();
  const [, navigate] = useLocation();
  const { preferences, setPreferences, removeCustomPreference, addMultiplePreferences } = usePreferences(user?.id);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [directFlightsOnly, setDirectFlightsOnly] = useState(false);
  const [avoidRedEye, setAvoidRedEye] = useState(false);
  const [preferredAirlines, setPreferredAirlines] = useState<string>("");

  // Watch for new extracted preferences from chat
  useEffect(() => {
    if (user?.id) {
      const checkInterval = setInterval(() => {
        const newPrefs = localStorage.getItem(`new_preferences_${user.id}`);
        if (newPrefs) {
          try {
            const prefs = JSON.parse(newPrefs);
            addMultiplePreferences(prefs);
            localStorage.removeItem(`new_preferences_${user.id}`);
          } catch (e) {
            console.error("Failed to parse new preferences:", e);
          }
        }
      }, 500);

      return () => clearInterval(checkInterval);
    }
  }, [user?.id, addMultiplePreferences]);

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
        <DropdownMenu open={preferencesOpen} onOpenChange={setPreferencesOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              data-testid="button-preferences"
              title="Preferences"
            >
              <Settings className="h-5 w-5" />
              <span className="sr-only">Preferences</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-64">
            <div className="px-2 py-1.5">
              <h3 className="font-semibold text-sm">Preferences</h3>
            </div>
            <DropdownMenuSeparator />
            
            <div className="px-3 py-2">
              <label className="text-xs font-medium">Currency</label>
              <select
                value={preferences.currency}
                onChange={(e) =>
                  setPreferences({ ...preferences, currency: e.target.value })
                }
                className="w-full mt-1 px-2 py-1 text-sm border rounded bg-background"
              >
                <option>USD</option>
                <option>EUR</option>
                <option>GBP</option>
                <option>INR</option>
                <option>JPY</option>
              </select>
            </div>
            
            <div className="px-3 py-2">
              <label className="text-xs font-medium">Distance Units</label>
              <select
                value={preferences.distanceUnits}
                onChange={(e) =>
                  setPreferences({ ...preferences, distanceUnits: e.target.value })
                }
                className="w-full mt-1 px-2 py-1 text-sm border rounded bg-background"
              >
                <option>Miles</option>
                <option>Kilometers</option>
              </select>
            </div>
            
            <div className="px-3 py-2">
              <label className="text-xs font-medium">Cabin Class</label>
              <select
                value={preferences.cabinClass}
                onChange={(e) =>
                  setPreferences({ ...preferences, cabinClass: e.target.value })
                }
                className="w-full mt-1 px-2 py-1 text-sm border rounded bg-background"
              >
                <option>Economy</option>
                <option>Premium Economy</option>
                <option>Business</option>
                <option>First Class</option>
              </select>
            </div>
            
            {preferences.customPreferences.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <div className="px-3 py-2">
                  <p className="text-xs font-medium mb-3">Your Preferences</p>
                  
                  {preferences.seatPreferences.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-muted-foreground mb-1">💺 Seating</p>
                      <div className="space-y-1">
                        {preferences.seatPreferences.map((pref, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-muted p-1.5 rounded gap-2">
                            <span>{pref}</span>
                            <button
                              onClick={() => removeCustomPreference(preferences.customPreferences.indexOf(pref))}
                              className="hover:text-red-600"
                              title="Remove"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {preferences.timePreferences.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-muted-foreground mb-1">🕐 Departure Time</p>
                      <div className="space-y-1">
                        {preferences.timePreferences.map((pref, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-muted p-1.5 rounded gap-2">
                            <span>{pref}</span>
                            <button
                              onClick={() => removeCustomPreference(preferences.customPreferences.indexOf(pref))}
                              className="hover:text-red-600"
                              title="Remove"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {preferences.airlinePreferences.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-muted-foreground mb-1">✈️ Airlines</p>
                      <div className="space-y-1">
                        {preferences.airlinePreferences.map((pref, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-muted p-1.5 rounded gap-2">
                            <span>{pref}</span>
                            <button
                              onClick={() => removeCustomPreference(preferences.customPreferences.indexOf(pref))}
                              className="hover:text-red-600"
                              title="Remove"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {preferences.flightTypePreferences.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-muted-foreground mb-1">🛫 Flight Type</p>
                      <div className="space-y-1">
                        {preferences.flightTypePreferences.map((pref, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-muted p-1.5 rounded gap-2">
                            <span>{pref}</span>
                            <button
                              onClick={() => removeCustomPreference(preferences.customPreferences.indexOf(pref))}
                              className="hover:text-red-600"
                              title="Remove"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {preferences.otherPreferences.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">📋 Other</p>
                      <div className="space-y-1">
                        {preferences.otherPreferences.map((pref, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-muted p-1.5 rounded gap-2">
                            <span>{pref}</span>
                            <button
                              onClick={() => removeCustomPreference(preferences.customPreferences.indexOf(pref))}
                              className="hover:text-red-600"
                              title="Remove"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}

            <DropdownMenuSeparator />
            <div className="px-3 py-2">
              <p className="text-xs font-medium mb-3">Flight Preferences</p>
              
              <div className="space-y-3">
                {/* Direct Flights Only */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="direct-flights" className="text-xs cursor-pointer">
                    Direct Flights Only
                  </Label>
                  <Switch
                    id="direct-flights"
                    checked={directFlightsOnly}
                    onCheckedChange={setDirectFlightsOnly}
                  />
                </div>

                {/* Avoid Red-Eye */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="avoid-red-eye" className="text-xs cursor-pointer">
                    Avoid Red-Eye
                  </Label>
                  <Switch
                    id="avoid-red-eye"
                    checked={avoidRedEye}
                    onCheckedChange={setAvoidRedEye}
                  />
                </div>

                {/* Preferred Airlines */}
                <div>
                  <Label htmlFor="preferred-airlines" className="text-xs">
                    Preferred Airlines
                  </Label>
                  <input
                    id="preferred-airlines"
                    type="text"
                    value={preferredAirlines}
                    onChange={(e) => setPreferredAirlines(e.target.value)}
                    placeholder="e.g., United, Delta"
                    className="w-full mt-1 px-2 py-1 text-xs border rounded bg-background"
                  />
                </div>
              </div>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

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
