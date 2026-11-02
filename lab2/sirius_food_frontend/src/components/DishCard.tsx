import Link from "next/link";

import { formatPrice, type MenuItem } from "@/lib/api";


export function DishCard({ item }: { item: MenuItem }) {
  return (
    <Link
      href={`/menu/${item.id}`}
      className="group flex min-h-44 flex-col justify-between rounded-3xl border border-orange-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-xl hover:shadow-orange-900/10"
    >
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-orange-600">
          {item.is_available ? "Доступно" : "Временно недоступно"}
        </p>
        <h2 className="mt-3 text-2xl font-black text-stone-900 group-hover:text-orange-800">
          {item.name}
        </h2>
      </div>
      <p className="mt-6 text-xl font-black text-orange-700">{formatPrice(item.price)}</p>
    </Link>
  );
}
