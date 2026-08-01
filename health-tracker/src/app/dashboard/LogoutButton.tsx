import { logout } from "@/app/actions/auth";

export function LogoutButton() {
  return (
    <form action={logout}>
      <button type="submit" className="text-sm underline">
        Sign out
      </button>
    </form>
  );
}
