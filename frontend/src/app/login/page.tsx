"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import { setAuth, getToken } from "@/lib/auth";
import {
  loginSchema,
  signupSchema,
  type LoginForm,
  type SignupForm,
} from "@/lib/schemas";
import { useEffect } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");

  useEffect(() => {
    if (getToken()) router.replace("/entities");
  }, [router]);

  const loginForm = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const signupForm = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { name: "", email: "", password: "" },
  });

  async function onLogin(values: LoginForm) {
    try {
      const res = await api.login(values);
      setAuth(res.token, res.user);
      toast.success("Signed in");
      router.push("/entities");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Login failed");
    }
  }

  async function onSignup(values: SignupForm) {
    try {
      const res = await api.signup(values);
      setAuth(res.token, res.user);
      toast.success("Account created");
      router.push("/entities");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Signup failed");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8">
        <p className="display text-3xl font-semibold text-teal-900">TaxStar</p>
        <p className="mt-2 text-slate-600">
          Sign in to manage company entities and invoices.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
        <div className="mb-6 flex gap-2 rounded-lg bg-slate-100 p-1 text-sm">
          <button
            type="button"
            className={`flex-1 rounded-md px-3 py-2 ${
              mode === "login" ? "bg-white font-medium shadow-sm" : "text-slate-600"
            }`}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`flex-1 rounded-md px-3 py-2 ${
              mode === "signup" ? "bg-white font-medium shadow-sm" : "text-slate-600"
            }`}
            onClick={() => setMode("signup")}
          >
            Sign up
          </button>
        </div>

        {mode === "login" ? (
          <form className="space-y-4" onSubmit={loginForm.handleSubmit(onLogin)}>
            <Field
              label="Email"
              type="email"
              error={loginForm.formState.errors.email?.message}
              {...loginForm.register("email")}
            />
            <Field
              label="Password"
              type="password"
              error={loginForm.formState.errors.password?.message}
              {...loginForm.register("password")}
            />
            <button
              type="submit"
              disabled={loginForm.formState.isSubmitting}
              className="w-full rounded-lg bg-teal-700 px-4 py-2.5 text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {loginForm.formState.isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        ) : (
          <form className="space-y-4" onSubmit={signupForm.handleSubmit(onSignup)}>
            <Field
              label="Name"
              error={signupForm.formState.errors.name?.message}
              {...signupForm.register("name")}
            />
            <Field
              label="Email"
              type="email"
              error={signupForm.formState.errors.email?.message}
              {...signupForm.register("email")}
            />
            <Field
              label="Password"
              type="password"
              error={signupForm.formState.errors.password?.message}
              {...signupForm.register("password")}
            />
            <button
              type="submit"
              disabled={signupForm.formState.isSubmitting}
              className="w-full rounded-lg bg-teal-700 px-4 py-2.5 text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {signupForm.formState.isSubmitting ? "Creating…" : "Create account"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
        {...props}
      />
      {error && <span className="mt-1 block text-rose-600">{error}</span>}
    </label>
  );
}
