// Purpose: root layout — global styles and the Convex/session providers.

import "./globals.css";
import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Automation — BYOK",
  description:
    "Browser front-end for the automation agent. Bring your own Anthropic API key.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
