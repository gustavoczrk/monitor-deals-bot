# Monitor Deals Bot

Utilitário pessoal em Python para consultar preços de monitores, avaliar ofertas
por uma watchlist e enviar alertas pelo [ntfy](https://ntfy.sh/). Atualmente há
suporte à Kabum e à Amazon Brasil.

O gatilho usa o preço promocional principal à vista. Na Amazon, o preço no
cartão também pode aparecer na notificação como informação. As integrações
falham de forma conservadora quando encontram HTML inesperado ou ambíguo.

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
