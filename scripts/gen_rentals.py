"""Wypożyczenia, pozycje wypożyczeń i płatności (Osoba 3)."""

from datetime import datetime, time, timedelta

from common import PAYMENT_METHODS, PENALTY_MULTIPLIER, TODAY, money, rng

HISTORY_DAYS = 730         
P_CANCELLED = 0.05         
P_ITEM_CANCELLED = 0.08     
P_LATE = 0.20              
P_NOTE = 0.15           
OPEN_WINDOW_DAYS = 45     
P_OPEN = 0.10            

ITEM_COUNT_WEIGHTS = {1: 55, 2: 25, 3: 13, 4: 7}
DURATION_DAYS = [1, 2, 3, 4, 5, 7, 10, 14]
DURATION_WEIGHTS = [20, 20, 15, 10, 10, 12, 8, 5]
METHOD_WEIGHTS = [15, 45, 15, 25] 

RETURN_NOTES = [
    "Drobne rysy na obudowie.",
    "Brak etui w zestawie.",
    "Zabrudzony obiektyw, wymaga czyszczenia.",
    "Pęknięta osłona ekranu.",
    "Brak ładowarki, klient dosłał później.",
    "Zużyte śmigło, do wymiany.",
    "Sprzęt zwrócony bez oryginalnego opakowania.",
]

NOW = datetime.combine(TODAY, time(0, 0)) 


def _random_datetime_on(day) -> datetime:
    """Losowa godzina pracy wypożyczalni (9:00-18:59) danego dnia."""
    return datetime.combine(day, time(rng.randint(9, 18), rng.randint(0, 59)))


def _rental_dates(n: int, equipment: list[dict]) -> list[datetime]:
    """n posortowanych dat wypożyczeń: ostatnie HISTORY_DAYS dni przed TODAY,
    ale nie wcześniej niż dzień po zakupie najstarszego egzemplarza."""
    first_purchase = min(eq["purchase_date"] for eq in equipment)
    start = max(TODAY - timedelta(days=HISTORY_DAYS), first_purchase + timedelta(days=1))
    span = (TODAY - start).days
    dates = [_random_datetime_on(start + timedelta(days=rng.randint(0, span - 1)))
             for _ in range(n)]
    return sorted(dates)


def _can_rent(eq: dict, is_open: bool, busy_until: datetime) -> bool:
    """Czy egzemplarz może trafić do wypożyczenia zajmującego go do busy_until.

    - w otwartym wypożyczeniu może być tylko sprzęt "available"
      (na końcu dostaje "rented"; maintenance/retired nie mogą być wypożyczone),
    - sprzęt "retired" tylko wtedy, gdy wrócił przed datą wycofania
      (pomocniczy klucz "_retired_date" od Osoby 2; bez niego nie wypożyczamy go wcale).
    """
    status = eq.get("status", "available")
    if is_open and status != "available":
        return False
    if status == "retired":
        retired = eq.get("_retired_date")
        return retired is not None and busy_until.date() < retired
    return True


def generate_rentals(
    customers: list[dict], equipment: list[dict], n: int
) -> tuple[list[dict], list[dict], list[dict]]:
    """Zwraca (rentals, rental_items, payments); klucze jak w COLUMNS, id = 1, 2, 3, ..."""
    rentals: list[dict] = []
    items: list[dict] = []
    if not customers or not equipment: 
        return [], [], []

    free_from = {
        eq["equipment_id"]: datetime.combine(eq["purchase_date"] + timedelta(days=1), time(0))
        for eq in equipment
    }
    by_id = {eq["equipment_id"]: eq for eq in equipment}

    for rental_date in _rental_dates(n, equipment):
        eligible_customers = [
            c for c in customers
            if c.get("registration_date") is None or c["registration_date"] <= rental_date.date()
        ]
        if not eligible_customers:
            continue
        customer = rng.choice(eligible_customers)

        duration = rng.choices(DURATION_DAYS, weights=DURATION_WEIGHTS)[0]
        due_date = rental_date.date() + timedelta(days=duration)
        is_cancelled = rng.random() < P_CANCELLED

        return_date = None
        if not is_cancelled:
            if rng.random() < P_LATE:
                return_day = due_date + timedelta(days=rng.randint(1, 10))
            else:
                return_day = rental_date.date() + timedelta(days=rng.randint(1, duration))
            planned_return = _random_datetime_on(return_day)

            recent = (TODAY - rental_date.date()).days <= OPEN_WINDOW_DAYS
            if planned_return >= NOW or (recent and rng.random() < P_OPEN):
                return_date = None
            else:
                return_date = planned_return
        is_open = not is_cancelled and return_date is None
        busy_until = rental_date if is_cancelled else (return_date or datetime.max)

        candidates = [
            eid for eid, ff in free_from.items()
            if ff is not None and ff <= rental_date
            and _can_rent(by_id[eid], is_open, busy_until)
        ]
        if not candidates:
            continue
        k = min(rng.choices(list(ITEM_COUNT_WEIGHTS), weights=list(ITEM_COUNT_WEIGHTS.values()))[0],
                len(candidates))
        chosen = rng.sample(candidates, k)

        rental_id = len(rentals) + 1
        rentals.append({
            "rental_id": rental_id,
            "customer_id": customer["customer_id"],
            "rental_date": rental_date,
            "due_date": due_date,
            "return_date": return_date,
            "is_cancelled": is_cancelled,
        })

        cancelled_item = None
        if not is_cancelled and k >= 2 and rng.random() < P_ITEM_CANCELLED:
            cancelled_item = rng.choice(chosen)

        for eid in chosen:
            eq = by_id[eid]
            item_cancelled = is_cancelled or eid == cancelled_item
            daily_rate = money(eq["daily_rate"])   
            deposit = money(eq["deposit"])

            penalty = None
            return_notes = None
            if not item_cancelled and return_date is not None:
                days_late = max(0, (return_date.date() - due_date).days)
                penalty = money(days_late * daily_rate * PENALTY_MULTIPLIER)
                if rng.random() < P_NOTE:
                    return_notes = rng.choice(RETURN_NOTES)

            if not item_cancelled:
                free_from[eid] = return_date 

            items.append({
                "rental_item_id": len(items) + 1,
                "rental_id": rental_id,
                "equipment_id": eid,
                "daily_rate": daily_rate,
                "deposit": deposit,
                "penalty": penalty,
                "return_notes": return_notes,
                "is_cancelled": item_cancelled,
            })

    payments = generate_payments(rentals, items)

    for eid, ff in free_from.items():
        if ff is None:
            by_id[eid]["status"] = "rented"

    return rentals, items, payments



def generate_payments(rentals: list[dict], items: list[dict]) -> list[dict]:
    """Płatności spójne z wypożyczeniami (tylko nieanulowane wypożyczenia):
    rental_fee i deposit przy rental_date, deposit_refund i penalty przy return_date."""
    payments: list[dict] = []
    items_by_rental: dict[int, list[dict]] = {}
    for it in items:
        items_by_rental.setdefault(it["rental_id"], []).append(it)

    for r in rentals:
        if r["is_cancelled"]:
            continue
        active = [it for it in items_by_rental[r["rental_id"]] if not it["is_cancelled"]]
        days = (r["due_date"] - r["rental_date"].date()).days
        method = rng.choices(PAYMENT_METHODS, weights=METHOD_WEIGHTS)[0]

        def pay(when, amount, ptype, how=method):
            if amount > 0:  # amount musi być > 0
                payments.append({
                    "payment_id": len(payments) + 1,
                    "rental_id": r["rental_id"],
                    "payment_date": when,
                    "amount": money(amount),
                    "method": how,
                    "type": ptype,
                })

        deposit = sum(it["deposit"] for it in active)
        pay(r["rental_date"], sum(it["daily_rate"] for it in active) * days, "rental_fee")
        pay(r["rental_date"], deposit, "deposit")

        if r["return_date"] is not None:
            pay(r["return_date"], deposit, "deposit_refund")
            pay(r["return_date"], sum(it["penalty"] for it in active), "penalty",
                rng.choices(PAYMENT_METHODS, weights=METHOD_WEIGHTS)[0])

    return payments


if __name__ == "__main__":
    from collections import Counter
    from datetime import date

    customers = [{"customer_id": i} for i in range(1, 21)]
    equipment = [{"equipment_id": i, "daily_rate": 50.00, "deposit": 300.00,
                  "status": "available", "purchase_date": date(2023, 1, 1)}
                 for i in range(1, 31)]
    equipment[0]["status"] = "maintenance"
    equipment[1]["status"] = "retired"
    equipment[1]["_retired_date"] = date(2025, 6, 1)
    equipment[2]["status"] = "retired"          

    r, it, p = generate_rentals(customers, equipment, 1000)
    print("rentals:", len(r), " items:", len(it), " payments:", len(p))

    rmap = {x["rental_id"]: x for x in r}
    emap = {e["equipment_id"]: e for e in equipment}

    spans = {}
    for x in it:
        if not x["is_cancelled"]:
            rr = rmap[x["rental_id"]]
            spans.setdefault(x["equipment_id"], []).append(
                (rr["rental_date"], rr["return_date"] or datetime.max))
    for s in spans.values():
        s.sort()
        for (_, end1), (start2, _) in zip(s, s[1:]):
            assert start2 >= end1, "nakładające się wypożyczenia!"

    for rr in r:
        assert rr["due_date"] > rr["rental_date"].date()
        assert rr["return_date"] is None or rr["return_date"] >= rr["rental_date"]
        assert not (rr["is_cancelled"] and rr["return_date"])
        assert rr["rental_date"].date() < TODAY
    for x in it:
        rr, eq = rmap[x["rental_id"]], emap[x["equipment_id"]]
        assert eq["purchase_date"] < rr["rental_date"].date()
        if eq.get("_retired_date"):
            end = rr["return_date"] or rr["rental_date"]
            assert end.date() < eq["_retired_date"], "wypożyczenie po wycofaniu!"
        assert x["equipment_id"] != 3, "retired bez daty nie powinien być wypożyczany"
        if rr["is_cancelled"]:
            assert x["is_cancelled"]
        if x["is_cancelled"] or rr["return_date"] is None:
            assert x["penalty"] is None
        else:
            d = max(0, (rr["return_date"].date() - rr["due_date"]).days)
            assert x["penalty"] == money(d * x["daily_rate"] * PENALTY_MULTIPLIER)
    assert all(pp["amount"] > 0 for pp in p)

    open_eq = {x["equipment_id"] for x in it
               if not x["is_cancelled"] and not rmap[x["rental_id"]]["is_cancelled"]
               and rmap[x["rental_id"]]["return_date"] is None}
    assert open_eq == {e["equipment_id"] for e in equipment if e["status"] == "rented"}

    print("cancelled:", sum(x["is_cancelled"] for x in r),
          " open:", sum(x["return_date"] is None and not x["is_cancelled"] for x in r),
          " open overdue:", sum(x["return_date"] is None and not x["is_cancelled"]
                                and x["due_date"] < TODAY for x in r),
          " late returns:", sum(1 for x in r if x["return_date"]
                                and x["return_date"].date() > x["due_date"]),
          " cancelled single items:", sum(x["is_cancelled"]
                                          and not rmap[x["rental_id"]]["is_cancelled"] for x in it))
    print("payment types:", dict(Counter(pp["type"] for pp in p)))
    print("methods:", dict(Counter(pp["method"] for pp in p)))
    print("equipment status:", dict(Counter(e["status"] for e in equipment)))
    print("OK - all checks passed")
