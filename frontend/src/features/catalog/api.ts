import { useQuery } from "@tanstack/react-query";
import { requestJson } from "../../shared/api/client";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Category {
  id: string;
  name: string;
  slug: string;
}
export interface Service {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
}
export interface Master {
  id: string;
  display_name: string;
  bio: string;
  timezone: string;
  address: string;
  avatar_url: string | null;
  is_demo: boolean;
  price_from: string | null;
  rating: number | null;
  review_count: number;
}
export interface Offer extends Service {
  master_id: string;
  service_id: string;
  price: string;
  duration_minutes: number;
}
export interface Portfolio {
  id: string;
  url: string;
  alt_text: string;
  source_url: string | null;
  license: string;
}
export interface Review {
  id: string;
  rating: number;
  text: string;
  author_name: string;
  created_at: string;
}
export interface Availability {
  date: string;
  timezone: string;
  duration_minutes: number;
  slots: { starts_at: string; ends_at: string }[];
}

export function useCatalogQuery<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ["catalog", path],
    queryFn: ({ signal }) => requestJson<T>(path, { signal }),
    enabled,
    staleTime: 30_000,
    retry: false,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["catalog", "categories"],
    staleTime: 300_000,
    retry: false,
    queryFn: async ({ signal }) => {
      const items: Category[] = [];
      let page = 1;
      while (true) {
        const result = await requestJson<Page<Category>>(
          `categories?page=${page}&page_size=50`,
          { signal },
        );
        items.push(...result.items);
        if (items.length >= result.total || result.items.length === 0)
          return items;
        page += 1;
      }
    },
  });
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function isIdentifier(value: string) {
  return uuid.test(value);
}
export function readFilters(params: URLSearchParams, masters: boolean) {
  const search = (params.get("search") ?? "").trim();
  const category = params.get("category_id") ?? "";
  const sort = params.get("sort") ?? "name";
  const page = params.get("page") ?? "1";
  const min = params.get("min_price") ?? "";
  const max = params.get("max_price") ?? "";
  const priceValid = (value: string) =>
    !value || /^\d{1,10}(\.\d{1,2})?$/.test(value);
  const valid =
    search.length <= 100 &&
    (!category || isIdentifier(category)) &&
    /^[1-9]\d{0,5}$/.test(page) &&
    (!masters ||
      (["name", "price_asc", "price_desc", "rating"].includes(sort) &&
        priceValid(min) &&
        priceValid(max) &&
        (!min || !max || Number(min) <= Number(max))));
  const query = new URLSearchParams({ page, page_size: "12" });
  if (search) query.set("search", search);
  if (category) query.set("category_id", category);
  if (masters) {
    query.set("sort", sort);
    if (min) query.set("min_price", min);
    if (max) query.set("max_price", max);
  }
  return {
    search,
    category,
    sort,
    page: Number(page),
    min,
    max,
    valid,
    query: query.toString(),
  };
}
export function money(value: string) {
  return new Intl.NumberFormat("ru-KZ", {
    style: "currency",
    currency: "KZT",
    maximumFractionDigits: 2,
  }).format(Number(value));
}
export function localDate(timezone: string, value = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  return ["year", "month", "day"]
    .map((key) => parts.find((part) => part.type === key)?.value)
    .join("-");
}
