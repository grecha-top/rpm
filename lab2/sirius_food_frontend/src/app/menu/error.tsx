"use client";


export default function MenuError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <section className="rounded-3xl border border-red-200 bg-white p-8">
        <p className="text-sm font-bold uppercase tracking-wider text-red-700">API недоступен</p>
        <h1 className="mt-3 text-3xl font-black text-stone-900">Не удалось загрузить меню</h1>
        <p className="mt-4 text-stone-600">Проверьте backend и повторите запрос.</p>
        <p className="mt-2 text-sm text-red-700">{error.message}</p>
        <button
          type="button"
          onClick={reset}
          className="mt-7 rounded-full bg-red-700 px-6 py-3 font-bold text-white"
        >
          Попробовать снова
        </button>
      </section>
    </main>
  );
}
