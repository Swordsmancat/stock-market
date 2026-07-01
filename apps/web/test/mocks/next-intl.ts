import messages from "../../messages/en.json";
import type * as React from "react";

type MessageNamespace = keyof typeof messages;

function translate(namespace?: string) {
  return (key: string, values?: Record<string, string | number>) => {
    const namespaceMessages = namespace
      ? (messages[namespace as MessageNamespace] as Record<string, string> | undefined)
      : undefined;
    let message = namespaceMessages?.[key] ?? key;
    for (const [name, value] of Object.entries(values ?? {})) {
      message = message.replace(`{${name}}`, String(value));
    }
    return message;
  };
}

export function useTranslations(namespace?: string) {
  return translate(namespace);
}

export function useLocale() {
  return "en";
}

export const NextIntlClientProvider = ({ children }: { children: React.ReactNode }) => children;
