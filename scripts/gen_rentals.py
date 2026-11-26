"""Wypożyczenia, pozycje wypożyczeń i płatności (Osoba 3)."""

from common import PENALTY_MULTIPLIER, TODAY, fake, money, rng


def generate_rentals(
    customers: list[dict], equipment: list[dict], n: int
) -> tuple[list[dict], list[dict], list[dict]]:
    """Zwraca (rentals, rental_items, payments); klucze jak w COLUMNS, id = 1, 2, 3, ...

    TODO:
    - rentals: 1-4 pozycje każde, rental_date z ostatnich 2 lat, due_date > rental_date,
    - ten sam egzemplarz nie może być wypożyczony dwa razy w tym samym czasie,
      sprzęt "retired"/"maintenance" nie jest wypożyczany po zmianie statusu,
    - rental_items: daily_rate i deposit skopiowane z equipment,
    - przypadki: zwrot w terminie, zwrot po terminie (penalty = dni spóźnienia
      * daily_rate * PENALTY_MULTIPLIER), w toku (return_date None), anulowane
      (is_cancelled True, return_date None),
    - payments: rental_fee, deposit, deposit_refund, penalty; różne metody,
    - na koniec: equipment["status"] = "rented" dla sprzętu z otwartych wypożyczeń
      (modyfikacja słowników w miejscu).
    """
    return [], [], []
