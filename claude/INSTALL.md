# Instalar el guardia

El guardia es un hook `Stop`. Corre en cada cierre de turno, en todas las
sesiones, y no necesita que nadie lo prenda. Lee [`README.md`](README.md) para
saber qué decide y por qué.

## Antes de empezar

- **Python 3** en el PATH, o la ruta al `python.exe` a mano.
- **Ollama** con el modelo `stop-judge`. Sin Ollama el guardia igual corre: se
  queda con los patrones y pierde el carril del juez.
- **Windows** para el instalador. En Linux o macOS la instalación es escribir
  el bloque JSON a mano; el hook en sí es Python puro y no le importa el SO.

## El modelo local

```sh
ollama pull qwen3.8-ud:latest
ollama create stop-judge -f stop-judge.Modelfile
```

Ocupa 13 GB. Si a la máquina le quedan menos de 14 GB libres de RAM, el guardia
lo saltea y deja pasar el turno: trabar todas las sesiones detrás de memoria que
no va a aparecer es peor que perder un control. El modelo está fijo en el
código, no se lee del entorno, porque una sesión bajo control puede editar
`settings.json` y una ya lo hizo.

## Instalar

Desde esta carpeta:

```powershell
.\install.ps1
```

Escribe el hook en `~\.claude\settings.json` apuntando a esta misma carpeta,
con backup en `settings.json.bak`. El hook resuelve sus checkers desde su propia
ruta, así que la carpeta puede vivir donde vos quieras: cloná el repo, corré el
instalador, listo.

| bandera | qué hace |
|---|---|
| `-WhatIfOnly` | imprime el `settings.json` resultante y no toca nada |
| `-Python <ruta>` | fija el intérprete en vez de buscarlo en el PATH |
| `-Target <ruta>` | otra carpeta de usuario, útil para probar |
| `-Timeout <seg>` | tope del harness, `90` por defecto |
| `-WithReport` | agrega `judge-report.py --brief` como hook `SessionStart` |

## A mano

Si preferís editarlo vos, el bloque es el de [`stop.json`](stop.json), con la
ruta cambiada por la tuya:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "C:/Python314/python.exe -u <ruta>/claude/check-stop.py",
            "timeout": 90,
            "env": { "HOME": "C:/Users/<vos>", "STOP_HOLDOUT": "0" }
          }
        ]
      }
    ]
  }
}
```

Claude Code y Grok Build cargan el mismo bloque. `SubagentStop` no va: un hijo
corto que el guardia mantiene vivo empila rondas y el modelo de 13 GB.

## Comprobar que quedó

```sh
bash run-tests.sh
```

Todas las suites, con el ledger de procesos. No toca la placa: cuesta 42
procesos y ni un byte de VRAM. Una suite sola:

```sh
python test_check_permission.py
python test_check_tree.py
```

Después, en una sesión nueva, decí "listo" con trabajo a medias. Si el guardia
está vivo, te manda de vuelta.

## Perillas

Todas por variable de entorno, en el `env` del hook. La tabla completa está en
el [README](README.md#operarlo). Las que más se tocan:

| variable | default | qué hace |
|---|---|---|
| `STOP_JUDGE_HOST` | `http://127.0.0.1:11434` | dónde vive Ollama |
| `STOP_SURE_FLOOR` | `0.5` | confianza mínima para frenar en vez de preguntar |
| `STOP_JUDGE_FLOOR` | `14` | GB libres mínimos para cargar el modelo |
| `STOP_JUDGE_DEADLINE` | `70` | tope de segundos del juez; el harness corta a 90 |

## Sacarlo

```powershell
.\uninstall.ps1
```

Saca las entradas del guardia de `settings.json` y deja el resto como estaba.
