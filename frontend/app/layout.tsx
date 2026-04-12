import type { Metadata } from "next";
import SiteNav from "@/components/site-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AirPro Service Command",
    template: "%s | AirPro Service Command",
  },
  description: "Live HVAC voice-agent console and appointment calendar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <div className="relative isolate min-h-full overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.22),transparent_32%),radial-gradient(circle_at_85%_15%,rgba(34,197,94,0.12),transparent_22%),linear-gradient(180deg,rgba(15,23,42,0.94),rgba(3,7,18,1))]" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-amber-300/60 to-transparent" />
          <div className="relative mx-auto flex min-h-full max-w-7xl flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8">
            <SiteNav />
            <main className="flex-1 py-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
