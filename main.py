import json
import math
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path

from watchlist import MONITORS
from amazon import AmazonOffer, fetch_amazon_offer
from kabum import fetch_kabum_price
from state import (
    DEFAULT_STATE_PATH,
    load_state,
    record_notification,
    record_observation,
    save_state,
    should_notify,
)


NTFY_SERVER = "https://ntfy.sh"
KABUM_PRODUCT_ID = "747516"


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


def format_price(price: float) -> str:
    return (
        f"R$ {price:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def process_offer(
    model: str,
    price: float,
    store: str,
    url: str,
    offer_key: str,
    state: dict,
    state_path: Path = DEFAULT_STATE_PATH,
    details: list[str] | None = None,
) -> None:
    monitor = find_monitor(model)
    result = evaluate_price(monitor, price)
    notify = should_notify(state, offer_key, price, result)

    if result == "ignore":
        record_observation(state, offer_key, price, result)
        save_state(state, state_path)
        print(
            f"Ignorado: {model} por R$ {price:.2f}"
        )
        return

    if not notify:
        record_observation(state, offer_key, price, result)
        save_state(state, state_path)
        print(f"Sem novo alerta: {model} por R$ {price:.2f}")
        return

    formatted_price = format_price(price)

    if result == "hot":
        title = "🔥🔥 PREÇO EXCELENTE"
        priority = 5
        tags = "fire,rotating_light"
    else:
        title = "🔥 Oferta de monitor"
        priority = 4
        tags = "fire,computer"

    if details:
        message = f"{model}\n{store}\n\n" + "\n".join(details)
    else:
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

    record_notification(state, offer_key, price, result)
    save_state(state, state_path)

    print(f"Alerta enviado: {model} - {formatted_price}")


def check_kabum(model: str, state: dict, state_path: Path) -> None:
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
        offer_key=f"kabum:{KABUM_PRODUCT_ID}",
        state=state,
        state_path=state_path,
    )


def check_amazon(
    monitor: dict,
    state: dict,
    state_path: Path,
) -> AmazonOffer:
    offer = fetch_amazon_offer(
        url=monitor["amazon_url"],
        expected_asin=monitor["amazon_asin"],
        expected_model=monitor["amazon_model"],
    )
    print(f"Preço encontrado na Amazon: R$ {offer.cash_price:.2f}")

    details = [f"Pix/NuPay: {format_price(offer.cash_price)}"]
    if offer.card_price is not None:
        details.append(f"Cartão: {format_price(offer.card_price)}")
    if offer.seller:
        details.append(f"Vendido por: {offer.seller}")

    process_offer(
        model=monitor["model"],
        price=offer.cash_price,
        store="Amazon",
        url=offer.url,
        offer_key=f"amazon:{offer.asin}",
        state=state,
        state_path=state_path,
        details=details,
    )
    return offer


def _run_store(store: str, action: Callable[[], None]) -> None:
    try:
        action()
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Erro na {store}: {error}")


def main(state_path: Path = DEFAULT_STATE_PATH) -> None:
    model = "ASUS TUF VG27AQ5A"
    monitor = find_monitor(model)
    state = load_state(state_path)

    _run_store("Kabum", lambda: check_kabum(model, state, state_path))
    _run_store("Amazon", lambda: check_amazon(monitor, state, state_path))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(f"Erro: {error}") from error
