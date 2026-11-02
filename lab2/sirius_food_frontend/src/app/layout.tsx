import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";


export const metadata: Metadata = {
  title: {
    default: "Сириус Еда",
    template: "%s | Сириус Еда",
  },
  description: "Витрина блюд проекта Сириус Еда",
};


export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <header className="border-b border-orange-100 bg-white/80 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
            <Link href="/" className="text-xl font-black tracking-tight text-orange-700">
              Сириус Еда
            </Link>
            <div className="flex gap-5 text-sm font-semibold text-stone-700">
              <Link href="/menu">SSR меню</Link>
              <Link href="/menu-csr">CSR меню</Link>
            </div>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
