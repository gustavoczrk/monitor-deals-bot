# Monitor Deals Bot

Utilitário pessoal em Python para consultar preços de monitores, avaliar ofertas
por uma watchlist e enviar alertas pelo [ntfy](https://ntfy.sh/). Atualmente há
suporte à Kabum e à Amazon Brasil.

O gatilho usa o preço promocional principal à vista. Na Amazon, o preço no
cartão também pode aparecer na notificação como informação. As integrações
falham de forma conservadora quando encontram HTML inesperado ou ambíguo.

O bot mantém o estado operacional local em `state.json`, que não deve ser
versionado. Uma oferta gera novo alerta quando aparece pela primeira vez, muda
de `deal` para `hot`, volta à faixa após ser ignorada ou cai pelo menos R$ 50 ou
5% desde o último alerta na mesma categoria.

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
