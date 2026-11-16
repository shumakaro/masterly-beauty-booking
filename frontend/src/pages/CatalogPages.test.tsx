import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError, requestJson } from "../shared/api/client";
import { MasterPage, MastersPage } from "./CatalogPages";

vi.mock("../shared/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../shared/api/client")>()),
  requestJson: vi.fn(),
}));
const id = "00000000-0000-4000-8000-000000000001";
const master = {
  id,
  display_name: "Мастер теста",
  bio: "Описание",
  address: "Адрес",
  timezone: "Asia/Qyzylorda",
  avatar_url: null,
  is_demo: true,
  rating: null,
  review_count: 0,
  price_from: "1250.50",
};
const clients: QueryClient[] = [];
function Location() {
  return <output aria-label="Адрес">{useLocation().search}</output>;
}
function show(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/masters" element={<MastersPage />} />
          <Route path="/masters/:id" element={<MasterPage />} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.mocked(requestJson).mockReset();
});
afterEach(() => {
  cleanup();
  clients.forEach((client) => client.clear());
  clients.length = 0;
});

it("submits filters into the URL, resets pagination and keeps filters when paging", async () => {
  vi.mocked(requestJson).mockImplementation(
    async <T,>(path: string): Promise<T> => {
      if (path.startsWith("categories"))
        return { items: [{ id, name: "Волосы" }], total: 1 } as T;
      return {
        items: [master],
        total: 25,
        page: Number(new URLSearchParams(path.split("?")[1]).get("page")),
        page_size: 12,
      } as T;
    },
  );
  show("/masters?search=старый&page=3");
  await screen.findByRole("option", { name: "Волосы" });
  fireEvent.change(screen.getByLabelText("Поиск"), {
    target: { value: "новый" },
  });
  fireEvent.change(screen.getByLabelText("Направление"), {
    target: { value: id },
  });
  fireEvent.change(screen.getByLabelText("Цена до, ₸"), {
    target: { value: "3000" },
  });
  fireEvent.change(screen.getByLabelText("Свободная дата"), {
    target: { value: "2030-01-08" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Найти" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Адрес")).toHaveTextContent(
      "search=%D0%BD%D0%BE%D0%B2%D1%8B%D0%B9",
    ),
  );
  expect(screen.getByLabelText("Адрес").textContent).not.toContain("page=3");
  fireEvent.click(await screen.findByRole("link", { name: "Далее →" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Адрес")).toHaveTextContent("page=2"),
  );
  expect(screen.getByLabelText("Адрес")).toHaveTextContent(`category_id=${id}`);
  expect(screen.getByLabelText("Адрес")).toHaveTextContent("max_price=3000");
  expect(screen.getByLabelText("Адрес")).toHaveTextContent(
    "available_on=2030-01-08",
  );
  expect(
    await screen.findByRole("link", { name: "Профиль: Мастер теста" }),
  ).toHaveAttribute("href", `/masters/${id}?date=2030-01-08`);
  expect(await screen.findByText("Пока без отзывов")).toBeInTheDocument();
});

it("blocks invalid URLs without making a catalog request and allows reset", async () => {
  vi.mocked(requestJson).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 12,
  });
  show("/masters?min_price=900&max_price=100&page=-1");
  expect(screen.getByRole("alert")).toHaveTextContent("Проверьте фильтры");
  expect(
    vi
      .mocked(requestJson)
      .mock.calls.some(([path]) => path.startsWith("masters")),
  ).toBe(false);
  fireEvent.click(screen.getByRole("link", { name: "Сбросить" }));
  expect(
    await screen.findByText(/По этим условиям мастеров нет/),
  ).toBeInTheDocument();
});

it("preserves a category from a direct URL when its label loads asynchronously", async () => {
  let resolveCategories!: (value: unknown) => void;
  const categories = new Promise((resolve) => {
    resolveCategories = resolve;
  });
  vi.mocked(requestJson).mockImplementation(
    async <T,>(path: string): Promise<T> => {
      if (path.startsWith("categories")) return (await categories) as T;
      return { items: [], total: 0, page: 1, page_size: 12 } as T;
    },
  );
  show(`/masters?category_id=${id}`);
  expect(screen.getByLabelText("Направление")).toBeDisabled();
  resolveCategories({ items: [{ id, name: "Волосы" }], total: 1 });
  await waitFor(() =>
    expect(screen.getByLabelText("Направление")).toBeEnabled(),
  );
  expect(screen.getByLabelText("Направление")).toHaveValue(id);
});

it("recovers from an API failure with an explicit retry", async () => {
  let fail = true;
  vi.mocked(requestJson).mockImplementation(
    async <T,>(path: string): Promise<T> => {
      if (path.startsWith("categories")) return { items: [], total: 0 } as T;
      if (fail) throw new ApiError(503, "Сервис временно недоступен.");
      return { items: [master], total: 1, page: 1, page_size: 12 } as T;
    },
  );
  show("/masters");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Сервис временно недоступен",
  );
  fail = false;
  fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }));
  expect(
    await screen.findByRole("heading", { name: master.display_name }),
  ).toBeInTheDocument();
});

it("provides a catalog recovery link for a missing profile", async () => {
  vi.mocked(requestJson).mockRejectedValue(new ApiError(404));
  show(`/masters/${id}`);
  expect(
    await screen.findByRole("heading", { name: "Мастер не найден." }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Вернуться в каталог" }),
  ).toHaveAttribute("href", "/masters");
});
