import { createFileRoute, Outlet } from "@tanstack/react-router";

/**
 * Customer menu layout. The URL carries only the restaurant slug, which the
 * child routes use to load the real public menu from the backend.
 */
export const Route = createFileRoute("/t/$token")({
  component: TableLayout,
});

function TableLayout() {
  return <Outlet />;
}
