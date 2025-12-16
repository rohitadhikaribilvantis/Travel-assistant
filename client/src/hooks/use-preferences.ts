import { useState, useCallback, useEffect } from "react";

interface Preferences {
  // Basic settings
  currency: string;
  distanceUnits: string;
  cabinClass: string;
  
  // Travel preferences
  customPreferences: string[]; // All learned preferences (seats, airlines, times, etc.)
  
  // Categorized preferences (for easier access)
  seatPreferences: string[];
  timePreferences: string[];
  airlinePreferences: string[];
  flightTypePreferences: string[];
  otherPreferences: string[];
}

const DEFAULT_PREFERENCES: Preferences = {
  currency: "USD",
  distanceUnits: "Miles",
  cabinClass: "Economy",
  customPreferences: [],
  seatPreferences: [],
  timePreferences: [],
  airlinePreferences: [],
  flightTypePreferences: [],
  otherPreferences: [],
};

function categorizePreference(pref: string): keyof Omit<Preferences, 'currency' | 'distanceUnits' | 'cabinClass' | 'customPreferences'> {
  const lower = pref.toLowerCase();
  
  if (lower.includes("seat") || lower.includes("window") || lower.includes("aisle") || lower.includes("middle")) {
    return "seatPreferences";
  } else if (lower.includes("morning") || lower.includes("evening") || lower.includes("afternoon") || lower.includes("departure")) {
    return "timePreferences";
  } else if (lower.includes("airline") || lower.includes("united") || lower.includes("delta") || lower.includes("american") || lower.includes("southwest") || lower.includes("jetblue")) {
    return "airlinePreferences";
  } else if (lower.includes("direct") || lower.includes("layover") || lower.includes("stop") || lower.includes("non-stop")) {
    return "flightTypePreferences";
  }
  
  return "otherPreferences";
}

export function usePreferences(userId?: string) {
  const [preferences, setPreferencesState] = useState<Preferences>(DEFAULT_PREFERENCES);

  // Load preferences from localStorage
  useEffect(() => {
    if (userId) {
      const saved = localStorage.getItem(`preferences_${userId}`);
      if (saved) {
        try {
          setPreferencesState(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse preferences:", e);
        }
      }
    }
  }, [userId]);

  const setPreferences = useCallback(
    (newPrefs: Preferences) => {
      setPreferencesState(newPrefs);
      if (userId) {
        localStorage.setItem(`preferences_${userId}`, JSON.stringify(newPrefs));
      }
    },
    [userId]
  );

  const addCustomPreference = useCallback(
    (pref: string) => {
      const category = categorizePreference(pref);
      setPreferences({
        ...preferences,
        customPreferences: [...new Set([...preferences.customPreferences, pref])],
        [category]: [...new Set([...preferences[category], pref])],
      });
    },
    [preferences, setPreferences]
  );

  const removeCustomPreference = useCallback(
    (index: number) => {
      const prefToRemove = preferences.customPreferences[index];
      const category = categorizePreference(prefToRemove);
      
      setPreferences({
        ...preferences,
        customPreferences: preferences.customPreferences.filter((_, i) => i !== index),
        [category]: preferences[category].filter((p) => p !== prefToRemove),
      });
    },
    [preferences, setPreferences]
  );

  const addMultiplePreferences = useCallback(
    (prefs: string[]) => {
      const newCustom = [...preferences.customPreferences];
      const newSeat = [...preferences.seatPreferences];
      const newTime = [...preferences.timePreferences];
      const newAirline = [...preferences.airlinePreferences];
      const newFlightType = [...preferences.flightTypePreferences];
      const newOther = [...preferences.otherPreferences];
      
      prefs.forEach((pref) => {
        if (!newCustom.includes(pref)) {
          newCustom.push(pref);
          const category = categorizePreference(pref);
          
          if (category === "seatPreferences") newSeat.push(pref);
          else if (category === "timePreferences") newTime.push(pref);
          else if (category === "airlinePreferences") newAirline.push(pref);
          else if (category === "flightTypePreferences") newFlightType.push(pref);
          else newOther.push(pref);
        }
      });
      
      setPreferences({
        ...preferences,
        customPreferences: newCustom,
        seatPreferences: newSeat,
        timePreferences: newTime,
        airlinePreferences: newAirline,
        flightTypePreferences: newFlightType,
        otherPreferences: newOther,
      });
    },
    [preferences, setPreferences]
  );

  return {
    preferences,
    setPreferences,
    addCustomPreference,
    removeCustomPreference,
    addMultiplePreferences,
  };
}
