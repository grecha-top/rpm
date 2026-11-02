"use client";

import { useEffect, useState } from "react";

import { DishCard } from "@/components/DishCard";
import type { MenuItem } from "@/lib/api";


const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";


export default function MenuCsrPage() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/menu/items`, { cache: "no-store", signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Menu API returned ${response.status}`);
        return response.json();
      })
      .then(setItems)
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <p className="text-sm font-bold uppercase tracking-[0.22em] text-sky-700">CSR сравнение</p>
      <h1 className="mt-3 text-4xl font-black tracking-tight text-stone-900">Меню в браузере</h1>
      <p className="mt-3 text-stone-600">Блюда появятся только после загрузки JavaScript и запроса к API.</p>
      {loading && <p className="mt-10 text-stone-600">Загружаем меню…</p>}
      {error && <p className="mt-10 font-semibold text-red-700">{error}</p>}
      {!loading && !error && (
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => <DishCard key={item.id} item={item} />)}
        </div>
      )}
    </main>
  );
}
