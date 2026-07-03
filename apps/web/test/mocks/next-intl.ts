import englishMessages from "../../messages/en.json";
import chineseMessages from "../../messages/zh.json";
import * as React from "react";

type MessageCatalog = Record<string, Record<string, string>>;

const DEFAULT_LOCALE = "en";
const messagesByLocale: Record<string, MessageCatalog> = {
  en: englishMessages as MessageCatalog,
  zh: chineseMessages as MessageCatalog,
};

const defaultIntlContextValue = {
  locale: DEFAULT_LOCALE,
  messages: messagesByLocale[DEFAULT_LOCALE],
};

let activeIntlContextValue = defaultIntlContextValue;

function translate(namespace?: string, activeMessages: MessageCatalog = defaultIntlContextValue.messages) {
  return (key: string, values?: Record<string, string | number>) => {
    const namespaceMessages = namespace
      ? activeMessages[namespace]
      : undefined;
    let message = namespaceMessages?.[key] ?? key;
    for (const [name, value] of Object.entries(values ?? {})) {
      message = message.replace(`{${name}}`, String(value));
    }
    return message;
  };
}

export function useTranslations(namespace?: string) {
  return translate(namespace, activeIntlContextValue.messages);
}

export function useLocale() {
  return activeIntlContextValue.locale;
}

export function NextIntlClientProvider({
  children,
  locale = DEFAULT_LOCALE,
  messages,
}: {
  children: React.ReactNode;
  locale?: string;
  messages?: MessageCatalog;
}) {
  const previousIntlContextValueRef = React.useRef(activeIntlContextValue);
  const intlContextValue = React.useMemo(
    () => ({
      locale,
      messages: messages ?? messagesByLocale[locale] ?? defaultIntlContextValue.messages,
    }),
    [locale, messages],
  );

  activeIntlContextValue = intlContextValue;

  React.useEffect(() => {
    return () => {
      activeIntlContextValue = previousIntlContextValueRef.current;
    };
  }, []);

  return React.createElement(React.Fragment, null, children);
}
