import json
import math
import os
import tempfile
from pathlib import Path


STATE_VERSION = 1
DEFAULT_STATE_PATH = Path(__file__).with_name("state.json")
VALID_CLASSIFICATIONS = {"ignore", "deal", "hot"}
MINIMUM_DROP_AMOUNT = 50.0
MINIMUM_DROP_PERCENTAGE = 0.05


def new_state() -> dict:
    return {"version": STATE_VERSION, "offers": {}}


def _valid_price(value) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def validate_state(state: dict) -> None:
    if not isinstance(state, dict) or set(state) != {"version", "offers"}:
        raise RuntimeError("Estrutura inválida no arquivo de estado.")
    if state["version"] != STATE_VERSION or not isinstance(state["offers"], dict):
        raise RuntimeError("Versão ou lista de ofertas inválida no estado.")

    expected_fields = {
        "last_observed_price",
        "last_observed_classification",
        "last_notified_price",
        "last_notified_classification",
        "out_of_range",
    }
    for key, record in state["offers"].items():
        if not isinstance(key, str) or not key or not isinstance(record, dict):
            raise RuntimeError("Chave ou registro de oferta inválido no estado.")
        if set(record) != expected_fields:
            raise RuntimeError(f"Campos inválidos no estado da oferta {key}.")
        if not _valid_price(record["last_observed_price"]):
            raise RuntimeError(f"Último preço observado inválido para {key}.")
        if record["last_observed_classification"] not in VALID_CLASSIFICATIONS:
            raise RuntimeError(f"Classificação observada inválida para {key}.")
        if not isinstance(record["out_of_range"], bool):
            raise RuntimeError(f"Indicador de faixa inválido para {key}.")
        if record["out_of_range"] != (
            record["last_observed_classification"] == "ignore"
        ):
            raise RuntimeError(f"Estado comercial inconsistente para {key}.")

        notified_price = record["last_notified_price"]
        notified_classification = record["last_notified_classification"]
        if (notified_price is None) != (notified_classification is None):
            raise RuntimeError(f"Última notificação incompleta para {key}.")
        if notified_price is not None:
            if not _valid_price(notified_price):
                raise RuntimeError(f"Último preço notificado inválido para {key}.")
            if notified_classification not in {"deal", "hot"}:
                raise RuntimeError(
                    f"Classificação notificada inválida para {key}."
                )


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return new_state()
    except OSError as error:
        raise RuntimeError(f"Não foi possível ler o estado: {error}") from error

    try:
        state = json.loads(source)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"JSON inválido no arquivo de estado: {error}") from error
    validate_state(state)
    return state


def save_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    validate_state(state)
    temporary_path = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        raise RuntimeError(f"Não foi possível salvar o estado: {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def should_notify(
    state: dict,
    offer_key: str,
    price: float,
    classification: str,
) -> bool:
    validate_state(state)
    if not offer_key or not _valid_price(price):
        raise ValueError("Oferta e preço devem ser válidos para deduplicação.")
    if classification not in VALID_CLASSIFICATIONS:
        raise ValueError(f"Classificação inválida: {classification}")
    if classification == "ignore":
        return False

    record = state["offers"].get(offer_key)
    if record is None or record["last_notified_price"] is None:
        return True
    if record["out_of_range"]:
        return True

    last_classification = record["last_notified_classification"]
    if classification == "hot" and last_classification == "deal":
        return True
    if classification != last_classification:
        return False

    last_price = record["last_notified_price"]
    drop = last_price - price
    return (
        drop >= MINIMUM_DROP_AMOUNT
        or drop / last_price >= MINIMUM_DROP_PERCENTAGE
    )


def record_observation(
    state: dict,
    offer_key: str,
    price: float,
    classification: str,
) -> None:
    validate_state(state)
    if not offer_key or not _valid_price(price):
        raise ValueError("Oferta e preço devem ser válidos para o estado.")
    if classification not in VALID_CLASSIFICATIONS:
        raise ValueError(f"Classificação inválida: {classification}")

    previous = state["offers"].get(offer_key, {})
    state["offers"][offer_key] = {
        "last_observed_price": price,
        "last_observed_classification": classification,
        "last_notified_price": previous.get("last_notified_price"),
        "last_notified_classification": previous.get(
            "last_notified_classification"
        ),
        "out_of_range": classification == "ignore",
    }


def record_notification(
    state: dict,
    offer_key: str,
    price: float,
    classification: str,
) -> None:
    if classification not in {"deal", "hot"}:
        raise ValueError("Somente deal ou hot podem ser registrados como alerta.")
    record_observation(state, offer_key, price, classification)
    record = state["offers"][offer_key]
    record["last_notified_price"] = price
    record["last_notified_classification"] = classification
    record["out_of_range"] = False
