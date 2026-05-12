import "./globals.css";

export const metadata = {
  title: "Receipt Finance Tracker",
  description: "Receipt upload and spending dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
