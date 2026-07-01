import * as React from "react";

type LinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
};

export function Link({ href, children, ...props }: LinkProps) {
  return (
    <a href={href} {...props}>
      {children}
    </a>
  );
}

export function useRouter() {
  return {
    push: () => undefined,
    replace: () => undefined,
    refresh: () => undefined,
  };
}

export function usePathname() {
  return "/";
}

export const routing = {
  locales: ["en", "zh"],
  defaultLocale: "en",
};

export function redirect(path: string): never {
  throw new Error(`redirect:${path}`);
}

export function getPathname({ href }: { href: string }) {
  return href;
}
