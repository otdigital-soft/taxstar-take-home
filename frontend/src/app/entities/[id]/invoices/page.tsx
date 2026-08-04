"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { AuthGuard } from "@/components/auth-guard";
import { AppHeader } from "@/components/app-header";
import { api, ApiError, type Invoice, type InvoiceStatus } from "@/lib/api";
import { invoiceSchema, type InvoiceForm } from "@/lib/schemas";

const FILTER_STATUSES = ["draft", "sent", "paid", "overdue"] as const;

export default function EntityInvoicesPage() {
  return (
    <AuthGuard>
      <InvoicesContent />
    </AuthGuard>
  );
}

function InvoicesContent() {
  const params = useParams<{ id: string }>();
  const entityId = params.id;
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [confirmPaidId, setConfirmPaidId] = useState<string | null>(null);

  const entityQuery = useQuery({
    queryKey: ["entity", entityId],
    queryFn: () => api.getEntity(entityId),
  });

  const invoicesQuery = useQuery({
    queryKey: ["invoices", entityId, statusFilter],
    queryFn: () =>
      api.listInvoices({
        entity_id: entityId,
        status: statusFilter || undefined,
      }),
  });

  const form = useForm<InvoiceForm>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      invoice_number: "",
      amount: "",
      currency: "USD",
      issue_date: "",
      due_date: "",
      status: "draft",
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: InvoiceForm) =>
      api.createInvoice({ ...values, entity_id: entityId }),
    onSuccess: () => {
      toast.success("Invoice created");
      form.reset({
        invoice_number: "",
        amount: "",
        currency: "USD",
        issue_date: "",
        due_date: "",
        status: "draft",
      });
      queryClient.invalidateQueries({ queryKey: ["invoices", entityId] });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.fields) {
        Object.entries(err.fields).forEach(([key, message]) => {
          if (key in form.getValues()) {
            form.setError(key as keyof InvoiceForm, { message });
          }
        });
      }
      toast.error(err instanceof ApiError ? err.message : "Could not create invoice");
    },
  });

  const markPaidMutation = useMutation({
    mutationFn: (invoiceId: string) => api.updateInvoiceStatus(invoiceId, "paid"),
    onMutate: async (invoiceId) => {
      await queryClient.cancelQueries({ queryKey: ["invoices", entityId] });
      const key = ["invoices", entityId, statusFilter] as const;
      const previous = queryClient.getQueryData<Invoice[]>(key);
      queryClient.setQueryData<Invoice[]>(key, (old = []) =>
        old.map((inv) =>
          inv.id === invoiceId
            ? { ...inv, status: "paid", effective_status: "paid" }
            : inv,
        ),
      );
      return { previous, key };
    },
    onError: (err, _id, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(ctx.key, ctx.previous);
      }
      toast.error(err instanceof ApiError ? err.message : "Update failed");
    },
    onSuccess: () => {
      toast.success("Invoice marked as paid");
      setConfirmPaidId(null);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices", entityId] });
    },
  });

  const invoices = useMemo(
    () => invoicesQuery.data ?? [],
    [invoicesQuery.data],
  );

  return (
    <div>
      <AppHeader title="Invoices" />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-2">
          <Link href="/entities" className="text-sm text-teal-700 hover:underline">
            ← Back to entities
          </Link>
        </div>
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-teal-950">
            {entityQuery.isLoading
              ? "Loading…"
              : `${entityQuery.data?.name ?? "Entity"} invoices`}
          </h1>
          <p className="mt-2 text-slate-600">
            Filter by status, add invoices, and mark them as paid.
          </p>
          {entityQuery.data && (
            <p className="mt-1 text-sm text-slate-500">
              TRN: {entityQuery.data.trn_masked}
            </p>
          )}
        </div>

        <section
          aria-labelledby="add-invoice-heading"
          className="mb-10 rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm"
        >
          <h2 id="add-invoice-heading" className="mb-4 text-xl font-semibold">
            Add invoice
          </h2>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
            noValidate
          >
            <TextField
              label="Invoice number"
              error={form.formState.errors.invoice_number?.message}
              {...form.register("invoice_number")}
            />
            <TextField
              label="Amount"
              inputMode="decimal"
              placeholder="1250.50"
              error={form.formState.errors.amount?.message}
              {...form.register("amount")}
            />
            <TextField
              label="Currency"
              error={form.formState.errors.currency?.message}
              {...form.register("currency")}
            />
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">
                Initial status
              </span>
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
                {...form.register("status")}
              >
                <option value="draft">draft</option>
                <option value="sent">sent</option>
              </select>
            </label>
            <TextField
              label="Issue date"
              type="date"
              error={form.formState.errors.issue_date?.message}
              {...form.register("issue_date")}
            />
            <TextField
              label="Due date"
              type="date"
              error={form.formState.errors.due_date?.message}
              {...form.register("due_date")}
            />
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-lg bg-teal-700 px-4 py-2.5 text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {createMutation.isPending ? "Creating invoice…" : "Create invoice"}
              </button>
            </div>
          </form>
        </section>

        <section aria-labelledby="invoice-list-heading">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 id="invoice-list-heading" className="text-xl font-semibold">
              Invoices
            </h2>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              Filter by status
              <select
                className="rounded-lg border border-slate-300 px-3 py-2"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter invoices by status"
              >
                <option value="">All</option>
                {FILTER_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {invoicesQuery.isLoading && <InvoiceTableSkeleton />}

          {invoicesQuery.isError && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-6 text-center">
              <p className="text-rose-700">Could not load invoices.</p>
              <button
                type="button"
                onClick={() => invoicesQuery.refetch()}
                disabled={invoicesQuery.isFetching}
                className="mt-3 rounded-lg border border-rose-300 px-3 py-1.5 text-sm text-rose-800 hover:bg-white disabled:opacity-60"
              >
                {invoicesQuery.isFetching ? "Retrying…" : "Try again"}
              </button>
            </div>
          )}

          {!invoicesQuery.isLoading &&
            !invoicesQuery.isError &&
            invoices.length === 0 &&
            !statusFilter && (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center">
                <p className="font-medium text-slate-800">No invoices yet.</p>
                <p className="mt-1 text-sm text-slate-500">
                  Create the first invoice for this entity.
                </p>
              </div>
            )}

          {!invoicesQuery.isLoading &&
            !invoicesQuery.isError &&
            invoices.length === 0 &&
            statusFilter && (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center">
                <p className="font-medium text-slate-800">
                  No {statusFilter} invoices found.
                </p>
                <button
                  type="button"
                  onClick={() => setStatusFilter("")}
                  className="mt-3 text-sm text-teal-700 hover:underline"
                >
                  Clear the filter to view all invoices
                </button>
              </div>
            )}

          {!invoicesQuery.isLoading &&
            !invoicesQuery.isError &&
            invoices.length > 0 && (
              <div className="overflow-x-auto rounded-xl border border-[var(--border)] bg-white">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                    <tr>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Number
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Amount
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Issue
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Due
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Status
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((invoice) => (
                      <InvoiceRow
                        key={invoice.id}
                        invoice={invoice}
                        confirming={confirmPaidId === invoice.id}
                        pending={
                          markPaidMutation.isPending &&
                          markPaidMutation.variables === invoice.id
                        }
                        onAskConfirm={() => setConfirmPaidId(invoice.id)}
                        onCancelConfirm={() => setConfirmPaidId(null)}
                        onConfirmPaid={() => markPaidMutation.mutate(invoice.id)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </section>
      </main>
    </div>
  );
}

function InvoiceRow({
  invoice,
  confirming,
  pending,
  onAskConfirm,
  onCancelConfirm,
  onConfirmPaid,
}: {
  invoice: Invoice;
  confirming: boolean;
  pending: boolean;
  onAskConfirm: () => void;
  onCancelConfirm: () => void;
  onConfirmPaid: () => void;
}) {
  const canMarkPaid =
    invoice.status !== "paid" &&
    (invoice.status === "draft" ||
      invoice.status === "sent" ||
      invoice.status === "overdue");

  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="px-4 py-3 font-medium">{invoice.invoice_number}</td>
      <td className="px-4 py-3">
        {formatMoney(invoice.amount, invoice.currency)}
      </td>
      <td className="px-4 py-3">{invoice.issue_date}</td>
      <td className="px-4 py-3">{invoice.due_date}</td>
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          <StatusBadge status={invoice.effective_status} />
          {invoice.effective_status !== invoice.status && (
            <span className="text-xs text-slate-500">
              stored: {invoice.status}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {!canMarkPaid ? (
          <span className="text-slate-400">—</span>
        ) : confirming ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-600">Mark as paid?</span>
            <button
              type="button"
              onClick={onConfirmPaid}
              disabled={pending}
              className="rounded bg-teal-700 px-2.5 py-1 text-xs text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {pending ? "Updating…" : "Confirm"}
            </button>
            <button
              type="button"
              onClick={onCancelConfirm}
              disabled={pending}
              className="rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onAskConfirm}
            className="rounded border border-teal-700 px-3 py-1.5 text-teal-800 hover:bg-teal-50"
          >
            Mark as paid
          </button>
        )}
      </td>
    </tr>
  );
}

function formatMoney(amount: string, currency: string) {
  const value = Number(amount);
  if (Number.isNaN(value)) return `${amount} ${currency}`;
  try {
    return value.toLocaleString(undefined, {
      style: "currency",
      currency: currency || "USD",
    });
  } catch {
    return `${amount} ${currency}`;
  }
}

function StatusBadge({ status }: { status: InvoiceStatus }) {
  const styles: Record<InvoiceStatus, string> = {
    draft: "bg-slate-100 text-slate-700",
    sent: "bg-sky-100 text-sky-800",
    paid: "bg-emerald-100 text-emerald-800",
    overdue: "bg-rose-100 text-rose-800",
  };
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

function InvoiceTableSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading invoices">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-12 animate-pulse rounded-lg border border-slate-200 bg-slate-100"
        />
      ))}
    </div>
  );
}

function TextField({
  label,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
}) {
  const id = props.id || props.name;
  return (
    <label className="block text-sm" htmlFor={id}>
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        id={id}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
        {...props}
      />
      {error && (
        <span id={`${id}-error`} className="mt-1 block text-rose-600" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}
