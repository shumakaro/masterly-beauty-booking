import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Введите корректный email").max(254),
  password: z.string().min(1, "Введите пароль"),
});
const password = z
  .string()
  .min(10, "Минимум 10 символов")
  .refine(
    (value) =>
      new TextEncoder().encode(value).length <= 72 && !value.includes("\0"),
    "Не более 72 байт UTF-8, без нулевого символа",
  );
export const registrationSchema = z
  .object({
    email: loginSchema.shape.email,
    display_name: z
      .string()
      .trim()
      .min(1, "Введите имя")
      .max(100, "Не более 100 символов"),
    password,
    confirm_password: z.string(),
    role: z.enum(["CLIENT", "MASTER"]),
  })
  .refine((values) => values.password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Пароли не совпадают",
  });
export const profileSchema = z.object({
  display_name: registrationSchema.shape.display_name,
});
