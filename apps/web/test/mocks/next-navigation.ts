export function useRouter() {
  return {
    push: () => undefined,
    replace: () => undefined,
    refresh: () => undefined,
    back: () => undefined,
    forward: () => undefined,
    prefetch: () => undefined,
  };
}

export function usePathname() {
  return "/";
}

export function useSearchParams() {
  return new URLSearchParams();
}

export function redirect(path: string): never {
  throw new Error(`redirect:${path}`);
}

export function notFound(): never {
  throw new Error("not-found");
}
