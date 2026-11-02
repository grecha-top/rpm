import { DishCard } from "@/components/DishCard";
import { getMenuItems } from "@/lib/api";


export const revalidate = 60;


export default async function MenuPage() {
  const items = await getMenuItems();

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <p className="text-sm font-bold uppercase tracking-[0.22em] text-orange-700">SSR витрина</p>
      <h1 className="mt-3 text-4xl font-black tracking-tight text-stone-900">Меню сегодня</h1>
      <p className="mt-3 max-w-2xl text-stone-600">
        Данные получены серверным компонентом и уже присутствуют в исходном HTML.
      </p>

      {items.length ? (
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => <DishCard key={item.id} item={item} />)}
        </div>
      ) : (
        <p className="mt-10 rounded-3xl border border-dashed border-orange-200 bg-white p-8 text-stone-600">
          Меню пока пусто. Добавьте блюда через API.
        </p>
      )}
    </main>
  );
}
