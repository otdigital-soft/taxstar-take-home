"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearAuth, getUser } from "@/lib/auth";

export function AppHeader({ title }: { title: string }) {
  const router = useRouter();
  const user = getUser();

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4">
        <div className="flex items-center gap-6">
          <Link href="/entities" className="text-lg font-semibold tracking-tight text-teal-800">
            TaxStar
          </Link>
          <nav className="flex items-center gap-4 text-sm text-slate-600">
            <Link href="/entities" className="hover:text-teal-700">
              Entities
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="hidden text-slate-500 sm:inline">{title}</span>
          {user && <span className="text-slate-700">{user.name}</span>}
          <button
            type="button"
            onClick={logout}
            className="rounded border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
