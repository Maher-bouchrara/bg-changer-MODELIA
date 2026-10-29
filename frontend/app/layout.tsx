// The frame around every page: fonts, title, language.
//
// next/font downloads the two Google fonts at build time and serves them from
// this site, so visitors' browsers never contact Google.
//   Unbounded: wide uppercase headings (a free look-alike of Modelia's Monument Extended)
//   Inter:     body text

import type { Metadata } from "next";
import { Inter, Unbounded } from "next/font/google";
import "./globals.css";

const unbounded = Unbounded({ subsets: ["latin"], weight: ["400"], variable: "--font-unbounded" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "bgchange: new background, same shadow",
  description: "Put a person or product photo on any background colour, with clean edges and its shadow.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${unbounded.variable} ${inter.variable}`}>
      <body>{children}</body>
    </html>
  );
}
