# Сириус Еда frontend

Витрина на Next.js 16 App Router демонстрирует SSR и ISR для публичного меню и отдельную CSR-страницу для сравнения.

## Запуск

Backend должен отвечать на `http://127.0.0.1:8000`.

```bash
cp .env.example .env.local
npm install
npm run dev
```

Открыть:

- `http://localhost:3000/menu` — серверная витрина;
- `http://localhost:3000/menu/1` — серверная карточка блюда;
- `http://localhost:3000/menu-csr` — клиентская версия.

Production-проверка:

```bash
npm run lint
npm run build
npm start
```

Сборка использует webpack, потому что Turbopack в локальном окружении Node.js 26 некорректно загружал native-модуль `lightningcss`. Это не меняет поведение Next.js-приложения.

## Реализовано

- Server Component `/menu` получает список из `GET /menu/items`;
- `/menu/[id]` получает одно блюдо и вызывает `notFound()` для API 404;
- `loading.tsx` показывает skeleton;
- `error.tsx` показывает ошибку API и кнопку повторного запроса;
- ISR кеширует HTML и `fetch` на 60 секунд;
- `generateMetadata()` формирует title, description и Open Graph;
- `/menu-csr` загружает данные в `useEffect` с `cache: "no-store"`;
- backend разрешает origin `http://localhost:3000` через `ALLOWED_ORIGINS`.

## Проверка SSR

```bash
curl -s http://localhost:3000/menu | grep "Борщ"
curl -s http://localhost:3000/menu/1 | grep "og:title"
curl -s http://localhost:3000/menu-csr | grep "Борщ"
```

Ожидаемый результат:

- первый запрос находит название блюда;
- второй находит SEO-метаданные;
- третий ничего не находит, потому что CSR получает блюда только после запуска JavaScript.

Production build проверен на Next.js 16.4.6. Итог маршрутов:

```text
/             static
/menu         ISR, revalidate 60 seconds
/menu-csr     static shell with client fetch
/menu/[id]    dynamic server render
```

## SSR и CSR

| Метрика | SSR `/menu` | CSR `/menu-csr` |
|---|---|---|
| Данные блюда в исходном HTML | есть | нет |
| Запрос к API | сервер Next.js | браузер |
| Первый полезный контент | вместе с HTML | после JS и fetch |
| SEO без выполнения JavaScript | работает | ограничено |
| Кеширование | ISR 60 секунд | `no-store` |

Для отчётного замера в Chrome DevTools:

1. открыть Network и включить Disable cache;
2. выполнить по три hard reload для `/menu` и `/menu-csr`;
3. записать First Contentful Paint и момент появления первой карточки;
4. приложить скриншоты Performance или Network к отчёту.

SSR предпочтителен для публичной витрины: поисковик и пользователь сразу получают содержимое меню. CSR полезен для приватных интерактивных экранов, где SEO не требуется и данные часто меняются после действий пользователя.

## Проверка ISR

ISR проверяется только в production-режиме:

1. выполнить `npm run build && npm start`;
2. открыть `/menu`;
3. изменить цену через backend API;
4. обновить страницу — до истечения окна может отображаться кешированное значение;
5. через 60 секунд повторить запрос и увидеть новую цену.
