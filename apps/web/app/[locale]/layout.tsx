import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "../globals.css"
import { NextIntlClientProvider } from "next-intl"
import { getMessages } from "next-intl/server"
import { notFound } from "next/navigation"
import { routing } from "@/src/i18n/routing"

import { ThemeProvider } from "@/components/theme-provider"
import { TopNavBar } from "@/components/top-nav-bar"
import { SidebarNavigation } from "@/components/sidebar-navigation"
import { Breadcrumbs } from "@/components/breadcrumbs"

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
            <div className="flex h-screen flex-col overflow-hidden">
              <TopNavBar />
              <div className="flex flex-1 overflow-hidden">
                <SidebarNavigation />
                <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
                  <Breadcrumbs />
                  {children}
                </main>
              </div>
            </div>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
