import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OmniNode Cyber-Physical War Room",
  description: "Live interactive operating system for infrastructure.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Force dark mode on html tag
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} font-sans antialiased h-screen w-screen overflow-hidden bg-background`}
      >
        {children}
      </body>
    </html>
  );
}
