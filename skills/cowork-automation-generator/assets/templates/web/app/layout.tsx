// Root layout — global styles only. No providers, no client context.

import "./globals.css";
import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Automation Data — Local CRUD",
  description:
    "Local dashboard over the shared on-disk datastore (.data/ + output/). No database, no API keys.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
