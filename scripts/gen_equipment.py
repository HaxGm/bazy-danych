"""Katalog modeli i generator egzemplarzy sprzętu (Osoba 2)."""

from datetime import timedelta

from common import TODAY, fake, money, rng


# Modele są rzeczywiste, ale ceny w PLN i numery seryjne są danymi testowymi.
# Wszystkie modele były dostępne przed początkiem zakresu dat zakupu.
MODEL_CATALOG = [
    # https://psref.lenovo.com/Product/ThinkPad/ThinkPad_T14_Gen_2_Intel
    {
        "name": "ThinkPad T14 Gen 2 (Intel)",
        "category": "laptop",
        "manufacturer": "Lenovo",
        "description": "Laptop biznesowy z ekranem 14 cali i procesorem Intel.",
        "daily_rate": 60,
        "deposit": 800,
    },
    # https://www.dell.com/support/product-details/en-ca/product/latitude-5420-laptop/resources/manuals
    {
        "name": "Latitude 5420",
        "category": "laptop",
        "manufacturer": "Dell",
        "description": "Laptop biznesowy z ekranem 14 cali do pracy biurowej.",
        "daily_rate": 55,
        "deposit": 700,
    },
    # https://support.apple.com/en-us/111883
    {
        "name": "MacBook Air (M1, 2020)",
        "category": "laptop",
        "manufacturer": "Apple",
        "description": "Laptop z układem Apple M1 i ekranem Retina 13,3 cala.",
        "daily_rate": 80,
        "deposit": 1000,
    },
    # https://www.canon-europe.com/cameras/eos-r6/specifications/
    {
        "name": "EOS R6",
        "category": "camera",
        "manufacturer": "Canon",
        "description": "Pełnoklatkowy aparat bezlusterkowy z mocowaniem Canon RF.",
        "daily_rate": 140,
        "deposit": 2000,
    },
    # https://www.nikonusa.com/p/z-6ii/1659/overview
    {
        "name": "Z 6II",
        "category": "camera",
        "manufacturer": "Nikon",
        "description": "Pełnoklatkowy aparat bezlusterkowy z mocowaniem Nikon Z.",
        "daily_rate": 130,
        "deposit": 1800,
    },
    # https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7m3/specifications
    {
        "name": "Alpha 7 III",
        "category": "camera",
        "manufacturer": "Sony",
        "description": "Pełnoklatkowy aparat bezlusterkowy 24,2 MP, mocowanie Sony E.",
        "daily_rate": 120,
        "deposit": 1600,
    },
    # https://www.epson.eu/en_EU/products/projector/home-cinema/ef-12/p/30883
    {
        "name": "EF-12",
        "category": "projector",
        "manufacturer": "Epson",
        "description": "Projektor laserowy 3LCD o rozdzielczości Full HD.",
        "daily_rate": 90,
        "deposit": 1000,
    },
    # https://www.benq.com/en-ap/projector/cinema/th685/spec.html
    {
        "name": "TH685",
        "category": "projector",
        "manufacturer": "BenQ",
        "description": "Projektor Full HD z wejściami HDMI do filmów i gier.",
        "daily_rate": 75,
        "deposit": 800,
    },
    # https://au.optoma.com/product/hd146x
    {
        "name": "HD146X",
        "category": "projector",
        "manufacturer": "Optoma",
        "description": "Projektor kina domowego o rozdzielczości 1920 x 1080.",
        "daily_rate": 70,
        "deposit": 700,
    },
    # https://blog.playstation.com/2020/11/09/ps5-the-ultimate-faq/
    {
        "name": "PlayStation 5",
        "category": "console",
        "manufacturer": "Sony",
        "description": "Stacjonarna konsola do gier z kontrolerem DualSense.",
        "daily_rate": 45,
        "deposit": 600,
    },
    # https://www.xbox.com/en-US/consoles/xbox-series-x
    {
        "name": "Xbox Series X",
        "category": "console",
        "manufacturer": "Microsoft",
        "description": "Stacjonarna konsola do gier z dyskiem SSD 1 TB.",
        "daily_rate": 45,
        "deposit": 600,
    },
    # https://www.nintendo.com/us/gaming-systems/switch/oled-model/
    {
        "name": "Switch OLED",
        "category": "console",
        "manufacturer": "Nintendo",
        "description": "Konsola hybrydowa z ekranem OLED 7 cali i pamięcią 64 GB.",
        "daily_rate": 35,
        "deposit": 400,
    },
    # https://store.dji.com/content/air-3-vs-mini-3-pro-vs-air-2s
    {
        "name": "Mini 3 Pro",
        "category": "drone",
        "manufacturer": "DJI",
        "description": "Kompaktowy, składany dron z kamerą na stabilizowanym gimbalu.",
        "daily_rate": 130,
        "deposit": 1500,
    },
    {
        "name": "Air 2S",
        "category": "drone",
        "manufacturer": "DJI",
        "description": "Składany dron z kamerą do fotografii i nagrań z powietrza.",
        "daily_rate": 160,
        "deposit": 2000,
    },
    # https://www.dji.com/rc/specs
    {
        "name": "Mavic 3",
        "category": "drone",
        "manufacturer": "DJI",
        "description": "Dron z serii Mavic z kamerą do fotografii i filmowania.",
        "daily_rate": 220,
        "deposit": 3000,
    },
]


def generate_equipment(n: int) -> list[dict]:
    """Zwraca n egzemplarzy; klucze jak w COLUMNS["equipment"], equipment_id = 1..n.

    Modele wybieramy kolejno z katalogu, więc przy n=150 każdy ma 10 sztuk.
    Około 5% egzemplarzy jest w serwisie, a 3% wycofanych (po zaokrągleniu
    w dół). Status rented ustawia później generate_rentals.
    Losowanie korzysta ze wspólnych fake i rng oraz stałej daty TODAY.
    Dla n=0 zwraca pustą listę, dla n<0 zgłasza ValueError.
    """
    if n < 0:
        raise ValueError("Liczba egzemplarzy nie może być ujemna.")
    if n == 0:
        return []

    maintenance_count = n // 20
    retired_count = n // 30
    statuses = (
        ["available"] * (n - maintenance_count - retired_count)
        + ["maintenance"] * maintenance_count
        + ["retired"] * retired_count
    )
    rng.shuffle(statuses)

    equipment = []
    for index in range(n):
        model = MODEL_CATALOG[index % len(MODEL_CATALOG)]
        equipment_id = index + 1
        equipment.append({
            "equipment_id": equipment_id,
            "name": model["name"],
            "category": model["category"],
            "manufacturer": model["manufacturer"],
            # Jawne id gwarantuje unikalność także przy powtórzeniu losowej części.
            "serial_number": f"TEST-{equipment_id:06d}-{fake.bothify('??########')}",
            "description": model["description"],
            "daily_rate": money(model["daily_rate"]),
            "deposit": money(model["deposit"]),
            "status": statuses[index],
            "purchase_date": fake.date_between(
                start_date=TODAY - timedelta(days=3 * 365),
                end_date=TODAY - timedelta(days=1),
            ),
        })

    return equipment
