import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useAuth } from "./use-auth";
import type { CurrentPreferences } from "./use-chat";

export interface StoredPreference {
  type: string;
  value: string;
  category: "seat" | "airline" | "departure_time" | "flight_type" | "cabin_class" | "red_eye" | "baggage" | "general";
  timestamp?: string;
}

export interface PreferenceSummary {
  seat: string[];
  airline: string[];
  departure_time: string[];
  flight_type: string[];
  cabin_class: string[];
  red_eye: string[];
  baggage: string[];
  general: string[];
  [key: string]: string[];
}

export function useMemory(userId?: string, refreshTrigger?: number) {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Fetch preferences summary
  const { data: preferences, isLoading: isLoadingPreferences, refetch: refetchPreferences } = useQuery({
    queryKey: ["memory", "preferences", userId, refreshTrigger],
    queryFn: async () => {
      if (!userId || !token) return null;

      const response = await fetch("/api/memory/preferences", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch preferences");
      }

      const data = await response.json();
      // API returns { userId, preferences, count } - extract the preferences object
      return data.preferences as PreferenceSummary;
    },
    enabled: !!userId && !!token,
    staleTime: 0, // Always consider data stale so refetch() will always fetch fresh data
  });

  // Fetch user profile with full memory
  const { data: profile, isLoading: isLoadingProfile, refetch: refetchProfile } = useQuery({
    queryKey: ["memory", "profile", userId],
    enabled: !!userId && !!token,
    queryFn: async () => {
      const response = await fetch("/api/memory/profile", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch profile");
      }

      return response.json();
    },
    staleTime: 60000, // 1 minute
  });

  // Fetch travel history
  const { data: travelHistory, isLoading: isLoadingHistory } = useQuery({
    queryKey: ["memory", "travel-history", userId],
    enabled: !!userId && !!token,
    queryFn: async () => {
      const response = await fetch("/api/memory/travel-history", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch travel history");
      }

      return response.json();
    },
    staleTime: 60000,
  });

  // Refresh preferences after chat
  const refreshPreferences = () => {
    refetchPreferences();
  };

  // Remove a specific preference
  const removePreferenceMutation = useMutation({
    mutationFn: async (preferenceText: string) => {
      const encodedText = encodeURIComponent(preferenceText);
      const response = await fetch(`/api/memory/preferences/${encodedText}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete preference");
      }

      return response.json();
    },
    onSuccess: () => {
      // Refetch preferences after deletion
      refetchPreferences();
      queryClient.invalidateQueries({ queryKey: ["memory", "preferences", userId] });
    },
  });

  const removePreference = (preferenceText: string) => {
    removePreferenceMutation.mutate(preferenceText);
  };

  // Format preferences for display
  const getFormattedPreferences = (): PreferenceSummary | null => {
    return preferences || null;
  };

  // Get all preferences as flat list
  const getAllPreferences = (): StoredPreference[] => {
    if (!preferences) return [];

    const allPrefs: StoredPreference[] = [];
    const categories = ["seat", "airline", "departure_time", "flight_type", "cabin_class", "red_eye", "baggage", "general"] as const;

    categories.forEach((category) => {
      const values = preferences[category] || [];
      values.forEach((value) => {
        allPrefs.push({
          type: value,
          value,
          category,
        });
      });
    });

    return allPrefs;
  };

  // Get merged preferences (stored + current UI state) - shows what the AI actually uses
  const getMergedPreferences = async (currentPreferences: CurrentPreferences): Promise<PreferenceSummary | null> => {
    if (!userId || !token) return null;
    
    try {
      const response = await fetch("/api/memory/preferences/merged", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ currentPreferences }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to fetch merged preferences");
      }
      
      const data = await response.json();
      return data.merged;
    } catch (error) {
      console.error("Error getting merged preferences:", error);
      return null;
    }
  };

  return {
    preferences: getFormattedPreferences(),
    profile,
    travelHistory,
    isLoading: isLoadingPreferences || isLoadingProfile || isLoadingHistory,
    isLoadingPreferences,
    isLoadingProfile,
    isLoadingHistory,
    refreshPreferences,
    removePreference,
    isRemovingPreference: removePreferenceMutation.isPending,
    getAllPreferences,
    getMergedPreferences,
    refetch: refetchPreferences,
  };
}
