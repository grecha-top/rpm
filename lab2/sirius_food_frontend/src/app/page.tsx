import Link from "next/link";


export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-[75vh] max-w-6xl items-center px-6 py-16">
      <section className="max-w-3xl">
        <p className="text-sm font-bold uppercase tracking-[0.24em] text-orange-700">
          Готовим на кампусе
        </p>
        <h1 className="mt-5 text-5xl font-black leading-tight tracking-tight text-stone-900 sm:text-7xl">
          Обед уже ближе, чем кажется
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-8 text-stone-600">
          Откройте серверную витрину: блюда и цены уже находятся в HTML при первом ответе.
        </p>
        <Link
          href="/menu"
          className="mt-10 inline-flex rounded-full bg-orange-700 px-7 py-3.5 font-bold text-white shadow-lg shadow-orange-900/15 transition hover:bg-orange-800"
        >
          Смотреть меню
        </Link>
      </section>
    </main>
  );
}
