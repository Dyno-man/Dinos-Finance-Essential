import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Receipt Finance Tracker",
  description: "Receipt upload and spending dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
