import createMiddleware from "next-intl/middleware";
import type { NextRequest } from "next/server";

import { routing } from "./src/i18n/routing";

const intlProxy = createMiddleware(routing);

export function proxy(request: NextRequest) {
  return intlProxy(request);
}

export const config = {
  // Match only internationalized pathnames.
  matcher: ["/", "/(zh|en)/:path*"],
};
