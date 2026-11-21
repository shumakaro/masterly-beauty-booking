import { DataPanel } from "./ui";
import { usePrivateOptions, usePrivateQuery } from "./api";
import {
  ResourceForm,
  ResourceManager,
  type ResourceConfig,
  type Row,
  type Field,
} from "./ResourceManager";
import {
  usePublicOptions,
  money,
  type Category,
  type Service,
} from "../catalog/api";

const days = [
  "Понедельник",
  "Вторник",
  "Среда",
  "Четверг",
  "Пятница",
  "Суббота",
  "Воскресенье",
];
const active: Field = {
  name: "is_active",
  label: "Активно",
  type: "checkbox",
  default: true,
};
const published: Field = {
  name: "is_published",
  label: "Профиль опубликован",
  type: "checkbox",
};
const workTimes: Field[] = [
  { name: "starts_local", label: "Начало работы", type: "time" },
  { name: "ends_local", label: "Конец работы", type: "time" },
];

export function BusinessProfile() {
  const query = usePrivateQuery<Row>("master/profile");
  return (
    <section className="workspace-section">
      <h2>Профиль мастера</h2>
      <p className="workspace-hint">
        Опишите свой подход, укажите адрес и часовой пояс. После публикации
        профиль станет виден в каталоге. При действующих записях смена часового
        пояса недоступна.
      </p>
      <DataPanel query={query}>
        {(profile) => (
          <ResourceForm
            key={profile.id}
            path="master/profile"
            method="PATCH"
            initial={profile}
            fields={[
              {
                name: "specialization",
                label: "Специализация",
                maxLength: 160,
              },
              {
                name: "experience_years",
                label: "Опыт работы в годах",
                type: "number",
                min: 0,
                max: 80,
                step: 1,
                default: 0,
              },
              {
                name: "bio",
                label: "О себе",
                type: "textarea",
                maxLength: 3000,
              },
              { name: "address", label: "Адрес приема", maxLength: 300 },
              {
                name: "timezone",
                label: "Часовой пояс (например, Asia/Qyzylorda)",
                required: true,
                maxLength: 64,
              },
              {
                name: "avatar_url",
                label: "Ссылка на фотографию",
                maxLength: 1000,
              },
              published,
            ]}
            prepare={(values) => ({
              ...values,
              avatar_url: values.avatar_url || null,
            })}
          />
        )}
      </DataPanel>
    </section>
  );
}

export function MasterManagement({ tab }: { tab: string }) {
  const services = usePublicOptions<Service>("services", tab === "offers");
  const categories = usePublicOptions<Category>(
    "categories",
    tab === "portfolio",
  );
  if (tab === "business-profile") return <BusinessProfile />;
  let config: ResourceConfig;
  if (tab === "offers") {
    return (
      <DataPanel query={services}>
        {(options) => (
          <ResourceManager
            config={{
              title: "Мои услуги",
              read: "master/services",
              write: "master/services",
              create: true,
              remove: true,
              removeLabel: "Отключить",
              description:
                "Выберите услугу каталога и установите свою цену и длительность. Отключенные предложения остаются в истории; их можно снова включить при редактировании.",
              summary: (row) =>
                `${row.name} · ${money(String(row.price))} · ${row.duration_minutes} мин${row.is_active ? "" : " · Отключено"}`,
              fields: [
                {
                  name: "service_id",
                  label: "Услуга каталога",
                  type: "select",
                  required: true,
                  createOnly: true,
                  options: options.map((service) => ({
                    value: service.id,
                    label: service.name,
                  })),
                },
                {
                  name: "price",
                  label: "Стоимость, ₸",
                  type: "decimal",
                  min: 0,
                  max: 9999999999,
                  required: true,
                },
                {
                  name: "duration_minutes",
                  label: "Длительность в минутах",
                  type: "number",
                  min: 15,
                  max: 720,
                  step: 15,
                  required: true,
                  default: 60,
                },
                active,
              ],
            }}
          />
        )}
      </DataPanel>
    );
  }
  if (tab === "schedules")
    config = {
      title: "Рабочая неделя",
      read: "master/schedules",
      write: "master/schedules",
      create: true,
      remove: true,
      description:
        "Часы в вашем часовом поясе, с шагом 15 минут. Для перерыва создайте два отдельных интервала. Начало должно быть раньше конца. Изменения не могут затрагивать подтвержденные посещения.",
      summary: (row) =>
        `${days[Number(row.weekday)]} · ${String(row.starts_local).slice(0, 5)}–${String(row.ends_local).slice(0, 5)}`,
      fields: [
        {
          name: "weekday",
          label: "День недели",
          type: "select",
          required: true,
          options: days.map((name, index) => ({
            value: String(index),
            label: name,
          })),
        },
        ...workTimes.map((field) => ({ ...field, required: true })),
      ],
      prepare: (values) => ({ ...values, weekday: Number(values.weekday) }),
    };
  else if (tab === "exceptions")
    config = {
      title: "Особые даты",
      read: "master/schedule-exceptions",
      write: "master/schedule-exceptions",
      create: true,
      remove: true,
      description:
        "Выходной или особые часы полностью заменяют график выбранной даты. Для выходного отметьте флажок; для рабочего дня задайте начало и конец с шагом 15 минут.",
      summary: (row) =>
        `${row.local_date} · ${row.is_closed ? "Выходной" : `${String(row.starts_local).slice(0, 5)}–${String(row.ends_local).slice(0, 5)}`}`,
      fields: [
        { name: "local_date", label: "Дата", type: "date", required: true },
        {
          name: "is_closed",
          label: "Выходной",
          type: "checkbox",
          default: true,
        },
        ...workTimes,
      ],
      prepare: (values) => ({
        ...values,
        starts_local: values.is_closed ? null : values.starts_local || null,
        ends_local: values.is_closed ? null : values.ends_local || null,
      }),
    };
  else
    config = {
      title: "Мое портфолио",
      read: "master/portfolio",
      write: "master/portfolio",
      create: true,
      remove: true,
      description:
        "Добавляйте свои работы или фотографии, на использование которых у вас есть разрешение. Меньшая позиция показывается раньше.",
      summary: (row) =>
        `${row.alt_text} · ${row.license} · Позиция ${row.position}`,
      fields: [
        { name: "title", label: "Название работы", maxLength: 150 },
        {
          name: "description",
          label: "Описание работы",
          type: "textarea",
          maxLength: 1500,
        },
        {
          name: "category_id",
          label: "Направление работы",
          type: "select",
          options:
            categories.data?.map((item) => ({
              value: item.id,
              label: item.name,
            })) ?? [],
        },
        {
          name: "url",
          label: "Ссылка на изображение",
          type: "url",
          required: true,
          maxLength: 1000,
          createOnly: true,
        },
        {
          name: "alt_text",
          label: "Описание фотографии",
          required: true,
          maxLength: 300,
        },
        {
          name: "source_url",
          label: "Ссылка на источник (необязательно)",
          type: "url",
          maxLength: 1000,
          createOnly: true,
        },
        {
          name: "license",
          label: "Лицензия или разрешение на использование",
          required: true,
          maxLength: 150,
          createOnly: true,
        },
        {
          name: "position",
          label: "Позиция в портфолио",
          type: "number",
          min: 0,
          step: 1,
          default: 0,
          required: true,
        },
      ],
      prepare: (values) => ({
        ...values,
        category_id: values.category_id || null,
        ...(Object.hasOwn(values, "source_url")
          ? { source_url: values.source_url || null }
          : {}),
      }),
    };
  return <ResourceManager config={config} />;
}

export function AdminManagement({ tab }: { tab: string }) {
  const categories = usePrivateOptions<Category>(
    "admin/categories",
    tab === "services",
  );
  const users = usePrivateOptions<{
    id: string;
    display_name: string;
    email: string;
  }>("admin/users", tab === "masters");
  if (tab === "masters")
    return (
      <DataPanel query={users}>
        {(options) => (
          <ResourceManager
            config={{
              title: "Видимость мастеров",
              read: "admin/masters",
              write: "admin/masters",
              fields: [published],
              summary: (row) =>
                `${options.find((user) => user.id === row.user_id)?.display_name ?? "Мастер"} · ${row.is_published ? "Опубликован" : "Скрыт"}`,
              description:
                "Скрытый профиль пропадает из публичного каталога. Существующие посещения сохраняются.",
            }}
          />
        )}
      </DataPanel>
    );
  if (tab === "users")
    return (
      <ResourceManager
        config={{
          title: "Пользователи",
          read: "admin/users",
          write: "admin/users",
          fields: [active],
          summary: (row) =>
            `${row.display_name} · ${row.email} · ${row.role === "CLIENT" ? "Клиент" : row.role === "MASTER" ? "Мастер" : "Администратор"} · ${row.is_active ? "Активен" : "Заблокирован"}`,
          description:
            "Блокировка отключает доступ к аккаунту. Роль через этот раздел не меняется. Администраторов блокировать нельзя.",
        }}
      />
    );
  if (tab === "categories")
    return (
      <ResourceManager
        config={{
          title: "Направления",
          read: "admin/categories",
          write: "categories",
          create: true,
          remove: true,
          summary: (row) =>
            `${row.name} · ${row.is_active ? "Активно" : "Отключено"}`,
          description:
            "Направления с услугами можно отключить. Удаление доступно только для неиспользуемых направлений.",
          fields: [
            {
              name: "name",
              label: "Название направления",
              maxLength: 100,
              required: true,
            },
            {
              name: "slug",
              label: "Короткое название латиницей (например, hair-care)",
              maxLength: 60,
              required: true,
            },
            active,
          ],
        }}
      />
    );
  return (
    <DataPanel query={categories}>
      {(options) => (
        <ResourceManager
          config={{
            title: "Каталог услуг",
            read: "admin/services",
            write: "services",
            create: true,
            remove: true,
            summary: (row) =>
              `${row.name} · ${options.find((category) => category.id === row.category_id)?.name ?? "Направление"} · ${row.is_active ? "Активно" : "Отключено"}`,
            fields: [
              {
                name: "category_id",
                label: "Направление",
                type: "select",
                required: true,
                options: options.map((category) => ({
                  value: category.id,
                  label: category.name,
                })),
              },
              {
                name: "name",
                label: "Название услуги",
                maxLength: 150,
                required: true,
              },
              {
                name: "description",
                label: "Описание",
                type: "textarea",
                maxLength: 3000,
              },
              active,
            ],
            description:
              "Неиспользуемые услуги можно удалить, используемые — отключить, сохранив историю посещений.",
          }}
        />
      )}
    </DataPanel>
  );
}
