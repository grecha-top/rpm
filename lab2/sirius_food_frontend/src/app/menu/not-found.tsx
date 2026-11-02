import Link from "next/link";


export default function MenuItemNotFound() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-4xl font-black text-stone-900">Блюдо не найдено</h1>
      <p className="mt-4 text-stone-600">Возможно, его убрали из текущего меню.</p>
      <Link href="/menu" className="mt-7 inline-block font-bold text-orange-700">
        Вернуться к меню
      </Link>
    </main>
  );
}
