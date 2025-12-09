import { Plane, Globe, Sparkles, Clock } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="relative mb-8">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10">
          <Plane className="h-12 w-12 text-primary" />
        </div>
        <div className="absolute -right-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-chart-3/20">
          <Globe className="h-4 w-4 text-chart-3" />
        </div>
      </div>

      <h2 className="mb-2 text-2xl font-semibold">Welcome to SkyMate</h2>
      <p className="mb-8 max-w-md text-center text-muted-foreground">
        Your AI-powered travel assistant. Search flights, get personalized
        recommendations, and plan your perfect trip.
      </p>

      <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <FeatureCard
          icon={<Plane className="h-5 w-5" />}
          title="Flight Search"
          description="Find flights with natural language queries"
        />
        <FeatureCard
          icon={<Sparkles className="h-5 w-5" />}
          title="Smart Suggestions"
          description="Get personalized recommendations"
        />
        <FeatureCard
          icon={<Clock className="h-5 w-5" />}
          title="Memory"
          description="I remember your travel preferences"
        />
      </div>
    </div>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border bg-card p-4 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="font-medium">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}
