"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { AuthGuard } from "@/components/auth-guard";
import { AppHeader } from "@/components/app-header";
import { api, ApiError } from "@/lib/api";
import { entitySchema, type EntityForm } from "@/lib/schemas";

export default function EntitiesPage() {
  return (
    <AuthGuard>
      <EntitiesContent />
    </AuthGuard>
  );
}

function EntitiesContent() {
  const queryClient = useQueryClient();
  const {
    data: entities = [],
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["entities"],
    queryFn: api.listEntities,
  });

  const form = useForm<EntityForm>({
    resolver: zodResolver(entitySchema),
    defaultValues: { name: "", trn: "" },
  });

  const createMutation = useMutation({
    mutationFn: api.createEntity,
    onSuccess: () => {
      toast.success("Entity created");
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["entities"] });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? err.message : "Could not create entity");
    },
  });

  return (
    <div>
      <AppHeader title="Entities" />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-teal-950">Company entities</h1>
          <p className="mt-2 text-slate-600">
            Create entities and open one to manage its invoices.
          </p>
        </div>

        <section
          aria-labelledby="create-entity-heading"
          className="mb-10 rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm"
        >
          <h2 id="create-entity-heading" className="mb-4 text-xl font-semibold">
            Create entity
          </h2>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
            noValidate
          >
            <label className="block text-sm sm:col-span-1">
              <span className="mb-1 block font-medium text-slate-700">Name</span>
              <input
                aria-invalid={!!form.formState.errors.name}
                aria-describedby={
                  form.formState.errors.name ? "entity-name-error" : undefined
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
                {...form.register("name")}
              />
              {form.formState.errors.name && (
                <span id="entity-name-error" className="mt-1 block text-rose-600" role="alert">
                  {form.formState.errors.name.message}
                </span>
              )}
            </label>
            <label className="block text-sm sm:col-span-1">
              <span className="mb-1 block font-medium text-slate-700">
                Tax registration number
              </span>
              <input
                aria-invalid={!!form.formState.errors.trn}
                aria-describedby={
                  form.formState.errors.trn ? "entity-trn-error" : undefined
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
                {...form.register("trn")}
              />
              {form.formState.errors.trn && (
                <span id="entity-trn-error" className="mt-1 block text-rose-600" role="alert">
                  {form.formState.errors.trn.message}
                </span>
              )}
            </label>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-lg bg-teal-700 px-4 py-2.5 text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {createMutation.isPending ? "Creating entity…" : "Create entity"}
              </button>
            </div>
          </form>
        </section>

        <section aria-labelledby="entity-list-heading">
          <h2 id="entity-list-heading" className="mb-4 text-xl font-semibold">
            Your entities
          </h2>

          {isLoading && <EntityListSkeleton />}

          {isError && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-6 text-center">
              <p className="text-rose-700">Could not load entities.</p>
              <button
                type="button"
                onClick={() => refetch()}
                disabled={isFetching}
                className="mt-3 rounded-lg border border-rose-300 px-3 py-1.5 text-sm text-rose-800 hover:bg-white disabled:opacity-60"
              >
                {isFetching ? "Retrying…" : "Try again"}
              </button>
            </div>
          )}

          {!isLoading && !isError && entities.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center">
              <p className="font-medium text-slate-800">No entities yet.</p>
              <p className="mt-1 text-sm text-slate-500">
                Create your first company entity using the form above.
              </p>
            </div>
          )}

          {!isLoading && !isError && entities.length > 0 && (
            <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-[var(--border)] bg-white">
              {entities.map((entity) => (
                <li key={entity.id}>
                  <Link
                    href={`/entities/${entity.id}/invoices`}
                    className="flex items-center justify-between gap-4 px-4 py-4 hover:bg-teal-50/50"
                  >
                    <div>
                      <p className="font-medium text-slate-900">{entity.name}</p>
                      <p className="text-sm text-slate-500">
                        TRN: {entity.trn_masked}
                      </p>
                    </div>
                    <span className="text-sm text-teal-700">View invoices →</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

function EntityListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading entities">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-16 animate-pulse rounded-xl border border-slate-200 bg-slate-100"
        />
      ))}
    </div>
  );
}
