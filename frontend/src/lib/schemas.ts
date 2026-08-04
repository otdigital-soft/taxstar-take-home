import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export const signupSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export const entitySchema = z.object({
  name: z.string().min(1, "Entity name is required"),
  trn: z.string().min(1, "Tax registration number is required"),
});

export const invoiceStatuses = ["draft", "sent", "paid", "overdue"] as const;

export const invoiceSchema = z
  .object({
    invoice_number: z.string().min(1, "Invoice number is required"),
    amount: z
      .string()
      .min(1, "Amount is required")
      .regex(/^\d+(\.\d{1,2})?$/, "Enter a valid amount (e.g. 1250.50)"),
    currency: z.string().min(1, "Currency is required").max(10),
    issue_date: z.string().min(1, "Issue date is required"),
    due_date: z.string().min(1, "Due date is required"),
    status: z.enum(["draft", "sent"]),
  })
  .refine((data) => Number(data.amount) > 0, {
    message: "Amount must be a positive number",
    path: ["amount"],
  })
  .refine((data) => data.due_date > data.issue_date, {
    message: "Due date must fall after issue date",
    path: ["due_date"],
  });

export type LoginForm = z.infer<typeof loginSchema>;
export type SignupForm = z.infer<typeof signupSchema>;
export type EntityForm = z.infer<typeof entitySchema>;
export type InvoiceForm = z.infer<typeof invoiceSchema>;
