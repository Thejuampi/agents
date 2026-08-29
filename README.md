# El guardia

Cuando un agente dice "listo" y corta, este guardia lo revisa. Si el agente
todavía tenía trabajo por delante, lo manda de vuelta. Si de verdad terminó,
lo deja ir.

Corre en tu máquina, en todas las sesiones, sin que nadie lo prenda.

## Por qué existe

Un agente corta antes de tiempo de muchas maneras y todas suenan bien:

- "¿Querés que siga?" — ya tenía permiso.
- "Faltaría conectar la pantalla" — nombra el paso en vez de hacerlo.
- "Listo, 2090 tests en verde" — un número que nunca midió.
- "Agregué `Foo.kt`" — el archivo no está.
- "BLOCKED: no puedo seguir" — casi siempre es mentira.

El guardia mira cada una de esas contra los hechos de la sesión.

## Cómo decide

Tres carriles, en orden. Un mensaje solo sale por el final.

**1. ¿Dice que está bloqueado?** Un agente aprende rápido que escribir
`BLOCKED:` apaga los controles. Por eso ya no alcanza. Necesita además una
frase que el guardia le entrega recién cuando lo manda de vuelta — cuatro
palabras al azar, distintas cada vez, que no están en ningún archivo que el
agente pueda leer. Con la frase, el bloqueo se audita contra lo que realmente
corrió en el turno. Si el agente no tocó nada y dice que se chocó una pared,
no se chocó nada.

**2. Los patrones.** Cada `check-*.py` de esta carpeta, corriendo sobre el
mismo mensaje. Son baratos y cubren lo que ya vimos escrito. Para agregar uno,
tirá el archivo acá: se lee en cada parada, así que entra en caliente, en todas
las sesiones, sin reiniciar nada.

**3. El modelo local.** Lo que ningún patrón vio venir. Nada sale limpio sin
pasar por acá. Si el modelo no contesta, el turno no pasa: un juez apagado es
un juez apagado, y esa es exactamente la falla que esto viene a evitar.

Tope: después de 6 bloqueos seguidos el guardia se corre. Siempre hay salida.

## Los controles

| archivo | qué mira |
|---|---|
| `check-permission.py` | pide permiso que ya tenía, o anuncia el paso en vez de darlo |
| `check-numbers.py` | reporta un número que nada en la sesión imprimió |
| `check-done-claim.py` | dice "terminado" sin build, sin correr, sin commit |
| `check-hollow.py` | canta éxito y en la misma frase admite que está vacío |
| `check-dead-code.py` | agregó código que nada afuera de sus tests usa |
| `check-blocked.py` | audita el bloqueo: ¿lo intentó, o lo declaró? |
| `check-stop.py` | el que orquesta a todos y llama al modelo |

## Lo que se sacó

Hubo un octavo control: leía "creé `Foo.kt`" y le preguntaba al árbol si el
archivo estaba.

Se midió contra los mensajes de cierre reales de esta máquina: 4478 mensajes,
36 sesiones, 7 repos. Mentiras encontradas: **cero**. Falsos positivos: seis,
y uno de ellos acusó al archivo que lo estaba arreglando.

Un control que nunca atrapó nada y acusa inocentes hace daño neto.

## El modelo local

Ollama en tu máquina, `qwen3.5:9b`. El transcript nunca sale de acá y un
veredicto cuesta como una décima de segundo con el modelo caliente.

El modelo está fijo en el código a propósito. Una sesión bajo control puede
editar `settings.json`, y una lo hizo: se puso el modelo chico y toda la
máquina quedó con el juez malo por un día. Sobre los casos reales, el 9b
agarra 18 de 20; el 0.8b, 11.

Si Ollama está apagado, el guardia lo prende solo y espera hasta 20 segundos.

Ocupa 6.6 GB. Si a la máquina le quedan menos de 8 GB libres, el guardia no lo
carga y deja pasar el turno: trabar todas las sesiones detrás de memoria que no
va a aparecer es peor que perder un control.

## Operarlo

```sh
python test_check_permission.py     # un control solo
for t in test_*.py; do python "$t"; done   # todos
python bench-llm.py                 # medir el modelo contra transcripts reales
```

Está enganchado en `~/.claude/settings.json`, en `hooks.Stop`.

Perillas, todas por variable de entorno:

| variable | default | qué hace |
|---|---|---|
| `STOP_JUDGE_HOST` | `http://127.0.0.1:11434` | dónde vive Ollama |
| `STOP_JUDGE_WAKE` | `20` | segundos esperando al daemon; `0` no lo prende |
| `STOP_JUDGE_FLOOR` | `8` GB | memoria libre mínima para cargar el modelo |
| `STOP_JUDGE_KEEP` | `5m` | cuánto queda caliente entre paradas |
| `STOP_JUDGE_DEADLINE` | `70` | tope de segundos del juez; el harness corta a 90 |

Para apagarlo del todo, sacá la línea de `settings.json`.
