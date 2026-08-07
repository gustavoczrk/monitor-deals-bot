import json
import math
import os
import urllib.request

from watchlist import MONITORS
from kabum import fetch_kabum_price


NTFY_SERVER = "https://ntfy.sh"


def send_notification(
    title: str,
    message: str,
    url: str | None = None,
    priority: int = 3,
    tags: str = "computer",
) -> None:
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        raise RuntimeError(
            "NTFY_TOPIC não configurada. Defina a variável de ambiente "
            "antes de enviar notificações."
        )

    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "priority": priority,
        "tags": tags.split(","),
    }

    if url:
        payload["click"] = url

    data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        NTFY_SERVER,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 400:
            raise RuntimeError(
                f"Falha ao enviar notificação: HTTP {response.status}"
            )


def find_monitor(model: str) -> dict:
    for monitor in MONITORS:
        if monitor["model"] == model:
            return monitor

    raise ValueError(f"Monitor não cadastrado: {model}")


def evaluate_price(monitor: dict, price: float) -> str:
    if (
        isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(price)
        or price <= 0
    ):
        raise ValueError("O preço da oferta deve ser um número maior que zero.")

    if price <= monitor["hot_price"]:
        return "hot"

    if price <= monitor["alert_price"]:
        return "deal"

    return "ignore"


def process_offer(
    model: str,
    price: float,
    store: str,
    url: str,
) -> None:
    monitor = find_monitor(model)
    result = evaluate_price(monitor, price)

    if result == "ignore":
        print(
            f"Ignorado: {model} por R$ {price:.2f}"
        )
        return

    formatted_price = (
        f"R$ {price:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    if result == "hot":
        title = "🔥🔥 PREÇO EXCELENTE"
        priority = 5
        tags = "fire,rotating_light"
    else:
        title = "🔥 Oferta de monitor"
        priority = 4
        tags = "fire,computer"

    message = (
        f"{model}\n"
        f"{formatted_price} - {store}\n\n"
        "27\" | QHD | IPS"
    )

    send_notification(
        title=title,
        message=message,
        url=url,
        priority=priority,
        tags=tags,
    )

    print(f"Alerta enviado: {model} - {formatted_price}")


def main() -> None:
    model = "ASUS TUF VG27AQ5A"

    url = (
        "https://www.kabum.com.br/produto/747516/"
        "monitor-gamer-asus-tuf-27-qhd-210hz-0-3ms-fast-ips-"
        "g-sync-comp-freesync-premium-hdr10-som-integrado-vg27aq5a"
    )

    price = fetch_kabum_price(
        url=url,
        expected_model="VG27AQ5A",
    )

    print(f"Preço encontrado na Kabum: R$ {price:.2f}")

    process_offer(
        model=model,
        price=price,
        store="Kabum",
        url=url,
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(f"Erro: {error}") from error
