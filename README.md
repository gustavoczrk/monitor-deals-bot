# Monitor Deals Bot

Utilitário pessoal em Python para consultar preços de monitores, avaliar ofertas
por uma watchlist e enviar alertas pelo [ntfy](https://ntfy.sh/). Atualmente há
suporte inicial à Kabum.

## Requisitos

- Python 3.10 ou superior
- Um tópico ntfy

Defina o tópico antes de executar. No PowerShell:

```powershell
$env:NTFY_TOPIC="seu-topico-ntfy"
```

## Execução

```powershell
python main.py
```

## Testes

```powershell
python -m unittest discover -v
```
