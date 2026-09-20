"""In-memory fake Supabase client for DashboardService / auth tests.

Implements only the query/storage surface DashboardService uses. The store is
a dict of table-name -> list of row dicts. `.eq()` filters apply to selects and
updates. `select("*, restaurants!inner(owner_id)")` enriches categories and
menu_items with a synthetic `restaurants` owner lookup so the ownership guard
can be exercised without a live Postgres.
"""

from __future__ import annotations


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Builder:
    def __init__(self, store: "FakeSupabase", table: str) -> None:
        self._store = store
        self._table = table
        self._filters: list[tuple[str, object]] = []
        self._in_filters: list[tuple[str, list[object]]] = []
        self._order_col: str | None = None
        self._order_desc = False
        self._select_cols = "*"
        self._pending_insert: list[dict] | None = None
        self._pending_update: dict | None = None
        self._pending_delete = False

    def select(self, cols: str = "*") -> "_Builder":
        self._select_cols = cols
        return self

    def insert(self, rows) -> "_Builder":
        self._pending_insert = rows if isinstance(rows, list) else [rows]
        return self

    def update(self, data: dict) -> "_Builder":
        self._pending_update = data
        return self

    def delete(self) -> "_Builder":
        self._pending_delete = True
        return self

    def eq(self, col: str, value: object) -> "_Builder":
        self._filters.append((col, value))
        return self

    def in_(self, col: str, values) -> "_Builder":
        self._in_filters.append((col, list(values)))
        return self

    def order(self, col: str, desc: bool = False) -> "_Builder":
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "_Builder":
        return self

    def execute(self) -> _Result:
        if self._pending_insert is not None:
            import uuid

            rows = []
            for row in self._pending_insert:
                if "id" not in row:
                    row = {**row, "id": str(uuid.uuid4())}
                rows.append(row)
            self._store._rows[self._table].extend(rows)
            return _Result(rows)

        if self._pending_update is not None:
            rows = self._matching_rows()
            for row in rows:
                row.update(self._pending_update)
            return _Result(rows)

        if self._pending_delete:
            rows = self._matching_rows()
            for row in rows:
                self._store._rows[self._table].remove(row)
            return _Result([])

        rows = self._matching_rows()
        if self._order_col:
            rows = sorted(
                rows,
                key=lambda r: r.get(self._order_col, 0),
                reverse=self._order_desc,
            )
        if "!inner" in self._select_cols:
            rows = [self._enrich(row) for row in rows]
        return _Result(rows)

    def _matching_rows(self) -> list[dict]:
        out = []
        for row in self._store._rows[self._table]:
            if all(row.get(col) == val for col, val in self._filters):
                if all(row.get(col) in vals for col, vals in self._in_filters):
                    out.append(row)
        return out

    def _enrich(self, row: dict) -> dict:
        restaurant_id = row.get("restaurant_id")
        restaurants = self._store._rows.get("restaurants", [])
        owner = next((r["owner_id"] for r in restaurants if r["id"] == restaurant_id), None)
        return {**row, "restaurants": {"owner_id": owner}}


class _Bucket:
    def __init__(self, store: "FakeSupabase", bucket: str) -> None:
        self._store = store
        self._bucket = bucket

    def upload(self, path: str, data: bytes, _opts: dict | None = None) -> None:
        self._store._objects[path] = data

    def get_public_url(self, path: str) -> str:
        return f"https://storage.test/object/public/{self._bucket}/{path}"


class FakeSupabase:
    def __init__(self) -> None:
        self._rows: dict[str, list[dict]] = {
            "restaurants": [],
            "categories": [],
            "menu_items": [],
            "generations": [],
        }
        self._objects: dict[str, bytes] = {}

    def table(self, name: str) -> _Builder:
        self._rows.setdefault(name, [])
        return _Builder(self, name)

    @property
    def storage(self) -> "_StorageFacade":
        return _StorageFacade(self)


class _StorageFacade:
    def __init__(self, store: "FakeSupabase") -> None:
        self._store = store

    def from_(self, bucket: str) -> _Bucket:
        return _Bucket(self._store, bucket)


def seed_restaurant(
    fake: FakeSupabase,
    *,
    restaurant_id: str,
    owner_id: str,
    name: str = "Restaurant",
    slug: str | None = None,
) -> dict:
    row = {
        "id": restaurant_id,
        "owner_id": owner_id,
        "slug": slug or f"{name.lower().replace(' ', '-')}",
        "name": name,
        "logo_url": None,
        "description": None,
        "address": None,
        "phone": None,
    }
    fake.table("restaurants").insert(row).execute()
    return row
