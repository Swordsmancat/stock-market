import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function IndexCardSkeleton() {
  return (
    <div className="rounded-lg border p-2">
      <div className="flex items-start justify-between gap-1 mb-2">
        <div className="flex-1">
          <Skeleton className="h-3 w-20 mb-1" />
          <Skeleton className="h-2 w-12" />
        </div>
        <Skeleton className="h-4 w-10 shrink-0" />
      </div>
      <Skeleton className="h-8 w-24 mb-1" />
      <Skeleton className="h-3 w-16 mb-2" />
      <Skeleton className="h-16 w-full mb-1" />
      <Skeleton className="h-2 w-full" />
    </div>
  );
}

export function MarketOverviewSkeleton() {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10">
          {Array.from({ length: 10 }).map((_, i) => (
            <IndexCardSkeleton key={i} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
