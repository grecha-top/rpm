export default function MenuLoading() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12" aria-busy="true">
      <div className="h-5 w-36 animate-pulse rounded bg-orange-100" />
      <div className="mt-4 h-12 w-72 animate-pulse rounded-xl bg-stone-200" />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-44 animate-pulse rounded-3xl bg-white" />
        ))}
      </div>
    </main>
  );
}
