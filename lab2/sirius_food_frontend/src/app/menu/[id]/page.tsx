import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { formatPrice, getMenuItem } from "@/lib/api";


type PageProps = { params: Promise<{ id: string }> };


export const revalidate = 60;


export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const item = await getMenuItem(id);
  if (!item) return { title: "Блюдо не найдено" };
  const description = `${item.name} за ${formatPrice(item.price)} в Сириус Еде`;
  return {
    title: item.name,
    description,
    openGraph: {
      title: item.name,
      description,
      type: "website",
    },
  };
}


export default async function MenuItemPage({ params }: PageProps) {
  const { id } = await params;
  const item = await getMenuItem(id);
  if (!item) notFound();

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <Link href="/menu" className="font-bold text-orange-700 hover:text-orange-900">
        ← Назад к меню
      </Link>
      <article className="mt-7 rounded-[2rem] border border-orange-100 bg-white p-8 shadow-xl shadow-orange-900/10 sm:p-12">
        <p className="text-sm font-bold uppercase tracking-wider text-orange-600">
          {item.is_available ? "Можно заказать" : "Сейчас недоступно"}
        </p>
        <h1 className="mt-4 text-4xl font-black tracking-tight text-stone-900 sm:text-5xl">
          {item.name}
        </h1>
        <p className="mt-8 text-3xl font-black text-orange-700">{formatPrice(item.price)}</p>
      </article>
    </main>
  );
}
