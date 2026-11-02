export type MenuItem = {
  id: number;
  name: string;
  price: number;
  is_available: boolean;
  category_id: number | null;
};


const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";


async function apiFetch(path: string): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    next: { revalidate: 60 },
  });
}


export async function getMenuItems(): Promise<MenuItem[]> {
  const response = await apiFetch("/menu/items");
  if (!response.ok) {
    throw new Error(`Menu API returned ${response.status}`);
  }
  return response.json();
}


export async function getMenuItem(id: string): Promise<MenuItem | null> {
  const response = await apiFetch(`/menu/items/${encodeURIComponent(id)}`);
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Menu API returned ${response.status}`);
  }
  return response.json();
}


export function formatPrice(price: number): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(price);
}
