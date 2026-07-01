import { useTranslations } from "next-intl";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";
import { WatchlistAddForm, WatchlistRemoveButton } from "@/components/watchlist-actions";

type WatchlistItem = {
  symbol: string;
  market: string;
  name: string;
  is_active: boolean;
};

type WatchlistPayload = {
  name: string;
  source: string;
  items: WatchlistItem[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchWatchlist(): Promise<WatchlistPayload> {
  const response = await fetch(`${apiBaseUrl}/watchlist`, { cache: "no-store" });
  if (!response.ok) {
    return { name: "default", source: "error", items: [] };
  }
  return response.json() as Promise<WatchlistPayload>;
}

export default async function WatchlistPage() {
  const payload = await fetchWatchlist();
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("Watchlist");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <WatchlistAddForm className="w-full md:w-auto" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>
            {payload.items.length} items in your watchlist.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("symbol")}</TableHead>
                <TableHead>{t("name")}</TableHead>
                <TableHead>{t("market")}</TableHead>
                <TableHead>{t("price")}</TableHead>
                <TableHead className="text-right">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    {t("noData")}
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((item) => (
                  <TableRow key={`${item.market}-${item.symbol}`}>
                    <TableCell className="font-medium">
                      <Link href={`/instruments/${item.symbol}` as any} className="hover:underline">
                        {item.symbol}
                      </Link>
                    </TableCell>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{item.market}</Badge>
                    </TableCell>
                    <TableCell>
                      {/* Placeholder for real-time price */}
                      <span className="text-muted-foreground">--</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/instruments/${item.symbol}` as any} title={t("viewDetails")}>
                            <ExternalLink className="h-4 w-4" />
                            <span className="sr-only">{t("viewDetails")}</span>
                          </Link>
                        </Button>
                        <WatchlistRemoveButton symbol={item.symbol} market={item.market} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
