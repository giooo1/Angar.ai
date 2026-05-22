import type { Metadata } from "next";
import {
  Fraunces,
  Inter,
  JetBrains_Mono,
  Noto_Sans_Georgian,
  Noto_Serif_Georgian,
} from "next/font/google";
import "./globals.css";

// Editorial body font.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

// Display serif for headlines.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
});

// Code / labels / numeric data.
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

// Georgian Mkhedruli, sans variant for body.
const notoSansGeorgian = Noto_Sans_Georgian({
  variable: "--font-noto-sans-georgian",
  subsets: ["georgian"],
  display: "swap",
});

// Georgian Mkhedruli, serif variant for headlines.
const notoSerifGeorgian = Noto_Serif_Georgian({
  variable: "--font-noto-serif-georgian",
  subsets: ["georgian"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Angar.ai — Document extraction",
  description:
    "AI-powered extraction for Georgian invoices, waybills, and tax documents.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={[
        inter.variable,
        fraunces.variable,
        jetbrainsMono.variable,
        notoSansGeorgian.variable,
        notoSerifGeorgian.variable,
      ].join(" ")}
    >
      <body>{children}</body>
    </html>
  );
}
