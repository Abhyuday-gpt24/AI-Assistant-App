import Link from "next/link";
import { LoginForm } from "./login-form";

export default function LoginPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Welcome back</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Sign in to continue your conversations.
        </p>
      </div>
      <LoginForm />
      <p className="text-center text-sm text-[var(--muted-foreground)]">
        Don&apos;t have an account?{" "}
        <Link
          href="/signup"
          className="font-medium text-[var(--foreground)] underline-offset-4 hover:underline"
        >
          Sign up
        </Link>
      </p>
    </div>
  );
}
