# Monitor Deals Bot

Utilitário pessoal em Python para consultar preços de monitores, avaliar ofertas
por uma watchlist e enviar alertas pelo [ntfy](https://ntfy.sh/). Atualmente há
suporte à Kabum e à Amazon Brasil.
Múltiplos modelos e suas fontes podem ser configurados diretamente na watchlist.

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
- Windows PowerShell para usar os scripts de agendamento

O projeto usa somente a biblioteca padrão do Python e não requer a instalação de
pacotes externos. Em um clone limpo, crie o ambiente virtual esperado pelos
scripts PowerShell:

```powershell
python -m venv .venv
```

Não é necessário ativar o ambiente virtual. Defina o tópico antes de executar:

```powershell
$env:NTFY_TOPIC="seu-topico-ntfy"
```

O arquivo `.env.example` serve apenas como referência: o bot não carrega arquivos
`.env` automaticamente. Use a variável de ambiente conforme o exemplo acima.

Escolha para `NTFY_TOPIC` um nome longo, aleatório e exclusivo, e nunca o
versione. O envio padrão usa o servidor público `ntfy.sh` sem autenticação; por
isso, um tópico nesse servidor não equivale a um canal privado autenticado.

Para mantê-lo entre sessões do Windows sem gravá-lo no projeto:

```powershell
[Environment]::SetEnvironmentVariable("NTFY_TOPIC", "seu-topico-ntfy", "User")
```

## Execução

```powershell
.\.venv\Scripts\python.exe main.py
```

O estado de deduplicação fica em `state.json`.

O processo termina com código `0` quando todas as fontes são processadas sem
erros operacionais. Se alguma fonte, configuração ou notificação falhar, as
demais fontes ainda são processadas, mas o código final é `1`.

## Personalização da watchlist

Edite `watchlist.py` para alterar os produtos monitorados. Cada produto define:

- `model`: nome exibido na notificação;
- `alert_price`: maior preço classificado como oferta;
- `hot_price`: maior preço classificado como oferta excelente;
- `sources`: loja, identificador, modelo esperado e URL de cada página.

Mantenha `hot_price` menor ou igual a `alert_price`, use um `id` único por fonte
e preserve os nomes de loja atualmente suportados: `kabum` e `amazon`.

## Execução automática no Windows

Confira a configuração sem alterar o sistema e depois instale a tarefa:

```powershell
.\setup_scheduler.ps1 -DryRun
.\setup_scheduler.ps1
```

O segundo comando solicita o tópico sem exibi-lo e registra a tarefa
`Monitor Deals Bot`, executada silenciosamente a cada 30 minutos. As saídas ficam
em `logs/monitor-deals.log`; ao atingir 5 MB, o arquivo anterior é mantido como
`monitor-deals.log.1`. Para validar o runner sem executar o bot, use
`.\run_monitor.ps1 -ValidateOnly`. Depois da instalação, a tarefa pode ser
iniciada manualmente com `Start-ScheduledTask -TaskName "Monitor Deals Bot"`.
Para desativá-la temporariamente, use
`Disable-ScheduledTask -TaskName "Monitor Deals Bot"`.

Para remover somente a tarefa, preservando estado, logs e `NTFY_TOPIC`:

```powershell
.\uninstall_scheduler.ps1
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```
