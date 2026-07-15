import { useTranslations } from "./next-intl";

export async function getTranslations(namespace?: string) {
  return useTranslations(namespace);
}

export async function getMessages() {
  return {};
}

export async function getLocale() {
  return "en";
}
