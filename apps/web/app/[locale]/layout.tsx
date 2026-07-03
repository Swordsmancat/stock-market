import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "../globals.css"
import { NextIntlClientProvider } from "next-intl"
import { getMessages } from "next-intl/server"
import { notFound } from "next/navigation"
import { routing } from "@/src/i18n/routing"

import { ThemeProvider } from "@/components/theme-provider"
import { MarketColorsProvider } from "@/context/market-colors-context"
import { ToastProvider } from "@/components/toast-provider"
import { TopNavBar } from "@/components/top-nav-bar"
import { SidebarNavigation } from "@/components/sidebar-navigation"
import { MobileNavigation } from "@/components/mobile-navigation"
import { Breadcrumbs } from "@/components/breadcrumbs"
import { BackendStatusBanner } from "@/components/backend-status-banner"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Stock Analysis Platform",
  description: "AI-powered stock analysis and portfolio management",
}

export default async function RootLayout({
  children,
  params
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={inter.className}>
        <NextIntlClientProvider messages={messages}>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <MarketColorsProvider>
              <ToastProvider />
              <div className="flex h-screen flex-col overflow-hidden">
                <TopNavBar />
                <div className="flex flex-1 overflow-hidden">
                  <SidebarNavigation />
                  <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6 lg:p-8">
                    <Breadcrumbs />
                    <BackendStatusBanner />
                    {children}
                  </main>
                </div>
                <MobileNavigation />
              </div>
            </MarketColorsProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
