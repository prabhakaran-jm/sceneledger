import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SceneLedger",
  description:
    "Source-linked training scenes with B2-backed provenance and verifiable release evidence",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
