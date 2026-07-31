import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="text-3xl font-semibold">Health Tracker</h1>
      <p className="text-gray-500">
        Privately track your health records and goals. Only you can see your data.
      </p>
      <div className="flex gap-4">
        <Link href="/login" className="rounded bg-black px-4 py-2 text-white">
          Sign in
        </Link>
        <Link href="/signup" className="rounded border px-4 py-2">
          Sign up
        </Link>
      </div>
    </div>
  );
}
