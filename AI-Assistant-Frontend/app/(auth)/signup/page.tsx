import Link from "next/link";
import { SignupForm } from "./signup-form";

export default function SignupPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Create an account</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Sign up to start chatting with your documents.
        </p>
      </div>
      <SignupForm />
      <p className="text-center text-sm text-[var(--muted-foreground)]">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-medium text-[var(--foreground)] underline-offset-4 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
