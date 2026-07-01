import { getTranslations } from "next-intl/server";
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
import { EmptyState } from "@/components/empty-state";

type AlertTrigger = {
  symbol: string;
  market: string;
  rule_key: string;
  threshold: number;
  triggered_at: string;
};

type AlertTriggersPayload = {
  items: AlertTrigger[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchAlertTriggers(): Promise<AlertTriggersPayload> {
  const response = await fetch(`${apiBaseUrl}/alerts/triggers/recent?limit=50`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return { items: [] };
  }
  return response.json() as Promise<AlertTriggersPayload>;
}

function formatRuleKey(ruleKey: string): string {
  return ruleKey.replace(/_/g, " ");
}

export default async function AlertsPage() {
  const payload = await fetchAlertTriggers();
  const t = await getTranslations("Alerts");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("triggerHistory")}</CardTitle>
          <CardDescription>{t("triggerHistoryDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("symbol")}</TableHead>
                <TableHead>{t("market")}</TableHead>
                <TableHead>{t("rule")}</TableHead>
                <TableHead>{t("threshold")}</TableHead>
                <TableHead>{t("triggeredAt")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                    <EmptyState title={t("noTriggers")} description={t("emptyHint")} />
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((trigger) => (
                  <TableRow key={`${trigger.symbol}-${trigger.rule_key}-${trigger.triggered_at}`}>
                    <TableCell className="font-medium">
                      <Link href={`/instruments/${trigger.symbol}` as any} className="hover:underline">
                        {trigger.symbol}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{trigger.market}</Badge>
                    </TableCell>
                    <TableCell className="capitalize">{formatRuleKey(trigger.rule_key)}</TableCell>
                    <TableCell>{trigger.threshold}</TableCell>
                    <TableCell>{new Date(trigger.triggered_at).toLocaleString()}</TableCell>
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
