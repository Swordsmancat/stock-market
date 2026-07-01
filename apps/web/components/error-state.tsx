import { AlertCircle } from "lucide-react";

type ErrorStateProps = {
  title: string;
  description?: string;
};

export function ErrorState({ title, description }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
      <AlertCircle className="h-8 w-8 text-destructive" />
      <p className="font-medium text-foreground">{title}</p>
      {description ? <p className="max-w-md text-sm text-muted-foreground">{description}</p> : null}
    </div>
  );
}
