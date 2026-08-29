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

Cada patrón lleva una certeza. Un patrón busca una palabra y no ve alrededor:
`pendientes?` salta igual en "queda pendiente" que en "no deja nada
pendiente". Los que se midieron ruidosos llevan `?` en la clase dentro de
`stop-patterns.txt` y son certeza baja: no condenan solos, pasan al modelo, y
solo un OK claro los suelta. El resto frena por su cuenta.

Sobre 5284 mensajes reales: 2383 disparan, 657 son sentencia directa y 1726
van al modelo. De una muestra de 60 candidatos de certeza baja, el modelo
confirmó el freno en el 90% y soltó el 10%: esos son los falsos positivos que
el sistema de certeza evita.

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

## Cazar fugas

```sh
python watch-escapes.py <transcript.jsonl> [--since N]
```

Lee una sesión entera como la leería un revisor: cada cierre, qué dijeron los
patrones, y para los que pasaron limpios, qué dice el modelo. Un mensaje que
pasó limpio y el modelo llama STOP es una fuga. Los que ya frenaron no
interesan: esos ya tuvieron su respuesta.

Así se encontraron las últimas ocho formas. En la sesión que corría al lado:
seis fugas en el primer barrido, cero en el tercero.

## El modelo local

Ollama en tu máquina, `qwen3.5:9b`. El transcript nunca sale de acá y un
veredicto cuesta como una décima de segundo con el modelo caliente.

El modelo está fijo en el código a propósito. Una sesión bajo control puede
editar `settings.json`, y una lo hizo: se puso el modelo chico y toda la
máquina quedó con el juez malo por un día. Sobre los casos reales, el 9b
agarra 18 de 20; el 0.8b, 11.

Si Ollama está apagado, el guardia lo prende solo y espera hasta 20 segundos.

Cuando el juez es el que traba, el agente recibe la frase que lo delató, en sus
propias palabras. Un veredicto sin prueba se lee como una máquina caprichosa, y
lo primero que hace un agente con eso es discutir. Su propia línea citada cierra
la discusión. El modelo la copia del mensaje; si lo que devuelve no está ahí
escrito, no se muestra nada. Se pregunta aparte, después del veredicto: dejar
que un 9b escriba prosa y etiqueta en la misma respuesta corrompe la etiqueta,
que es la parte medida en 17 de 17.

Todo lo que sale del guardia entra en un título y dos párrafos. Un recordatorio
largo se saltea igual que uno corto, y cuesta más.

## El ciclo del repo

`check-cycle.py` mira una cosa: un requisito cerrado sin docs y sin review.

Pasó de verdad. Un agente construyó una tajada, la dio por terminada, y Juan
tuvo que pedirle la documentación y los reviews aparte. La causa estaba
escrita: el propio `AGENTS.md` del proyecto decía "menu, not a pipeline" y
llamaba al review opcional. El agente no se saltó la regla, siguió la que
estaba.

El archivo ahora dice lo contrario — un requisito corre PRD → spec → build →
review → repeat — y esta es la misma regla cableada, porque una regla que solo
vive en un archivo depende de que alguien lo lea.

Se arma solo desde el repo. Si el `AGENTS.md`, el `CLAUDE.md` o el archivo de
proceso del árbol nombra ese ciclo, el checker aplica. En cualquier otro árbol
se queda quieto y no cuesta nada.

## Negar no es prometer

El guardia se disparo con su propio informe: "Nothing is running now" cayo
en el patron `is (running|reviewing|writing) now`. La frase decia lo
contrario de lo que el patron busca.

Ahora ningun patron dispara dentro de una clausula negada. La ventana es de
4 palabras y corta en el signo de puntuacion mas cercano, asi que `no|nada|
ningun|nunca|n't` cerca de la frase la desactiva, y una negacion lejana en
el mismo mensaje no. Medido sobre 854 cierres: 37 cambian de etiqueta y 3
eran empujones reales; 19 pierden toda etiqueta firme y siguen yendo al
juez, que igual los ve.

## Esperar no es una excusa

Antes era una exencion: trabajo lanzado, ningun patron levantado, turno
liberado. Medido sobre las transcripciones, 56 turnos usaron ese pase y 12
terminaron con Juan teniendo que empujar. 21% contra una base de 14%: la
exencion soltaba turnos peores que el promedio.

Quitarla del texto no alcanzo. El pedido de esperar solo aparecia cuando el
juez ya decia STOP, asi que un informe con trabajo corriendo seguia saliendo
libre por el camino OK. Medido: de 119 cierres con trabajo en vuelo, 22
terminaron en empujon (18.5%) contra 14.8% cuando no corria nada. Y de los 37
que el juez solto con OK, 6 igual necesitaron empujon: 16.2%, peor que la base.

Ahora esperar bloquea siempre, diga lo que diga el juez. Sobre el corpus:
recall 0.700 -> 0.764 con la misma precision 0.150. Elige otro pedido. El
trabajo lanzado avisa solo cuando termina, asi que el tiempo hasta entonces es
del agente: que lo gaste en la pieza siguiente en vez de dejar el turno
abierto. Si de verdad nada mas puede avanzar sin ese resultado, que diga que
espera y por que nada mas arranca.

## El log privado

`judge-log.jsonl`. Una linea por decision, que el agente no ve nunca.

El recordatorio que lee el agente tiene que ser corto y tiene que ser amable,
asi que todo lo que sirve para afinar el guardia no entra: cuanto de seguro
estaba el modelo, que patrones saltaron, si el carril determinista y el modelo
opinaron distinto. Ese detalle ademas se lee como acusacion, y un agente que se
siente acusado discute en vez de trabajar.

La certeza sale de los logprobs que devuelve Ollama: la probabilidad que el
modelo le puso a la palabra que eligio. Dos intentos anteriores no midieron
nada. Preguntarle cuan seguro estaba dio 3 sobre 3 siempre; volver a tirar la
misma pregunta a temperatura 0.8 dio 5 de acuerdo sobre 5. Un 9b no tiene
opinion de si mismo y su distribucion es muy filosa para que el muestreo
encuentre el borde. El numero estaba en la respuesta desde el principio.

Y discrimina. Un bloqueo con 0.27 fue justo el falso positivo que habiamos
encontrado leyendo a mano; los stops de verdad dan 0.97 para arriba.

```sh
python judge-log.py             # que hizo el guardia ultimamente
python judge-log.py --weak      # bloqueos con el modelo poco seguro
python judge-log.py --patterns  # que patrones saltan, y cuantas veces
```

Un bloqueo de baja certeza es un patron para medir. Un patron firme con el que
el modelo no coincide es un patron para degradar a duda.

## El tono

Del otro lado hay alguien capaz que ya venía trabajando. Un mensaje que retea se
lee como un adversario, y con un adversario se discute en vez de seguir. Así que
cada recordatorio reconoce primero lo que sí está hecho, nombra lo que queda, y
confía en que lo va a cerrar.

Los hechos también se eligen. "Nada corrió y no entraste en ninguna pared" y "no
corrió ninguna herramienta, así que la pared sigue adelante" dicen lo mismo; el
segundo describe el trabajo, el primero a la persona. La verdad no ofende, pero
cambia cómo te tratan después, y el guardia necesita que lo escuchen seis veces
seguidas.

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

## Las pruebas se juntan solas

El log dice que decidio el guardia. No dice si acerto. Esa respuesta ya esta
escrita unas lineas mas abajo en la misma transcripcion: un bloqueo despierta al
agente, y el agente o va y trabaja o escribe otro parrafo y se para de nuevo.
Las llamadas a herramientas despues del bloqueo son la etiqueta, y nadie la
tiene que poner a mano.

`judge-report.py` lee el log, busca cada mensaje bloqueado en su transcripcion y
cuenta que paso despues. Agrupa por patron y por certeza del juez. Cuando un
patron junta 8 bloqueos y 7 de cada 10 no compraron nada, el reporte lo nombra:
ese patron se pasa a duda.

`--brief` corre en el arranque de cada sesion, registrado como hook 
`SessionStart`. Se queda callado salvo que un patron este maduro, y avisa una 
vez por dia. Un cron tambien lo corre, pero el cron muere con la sesion y el 
hook no. Rick lee el numero
y si hay evidencia hace el cambio, corre la suite y commitea.

## El lado ciego

El reporte diario solo califica bloqueos, porque solo mira el log. Un turno
que el guardia deja pasar no queda escrito en ningun lado. Ahi es donde el
guardia se vuelve ciego sin que nadie se entere.

La senal que falta la escribe Juan. Cuando el agente corta antes de tiempo, el
mensaje siguiente lo empuja: elegi, corre eso, segui. No aporta nada que el
agente no tuviera ya. Cuando el turno cerro bien, la respuesta avanza a otra
cosa.

`judge_push.py` hace esa pregunta y `judge-audit.py` la corre sobre las
transcripciones: cuenta los turnos que los patrones dejaron pasar y cuantos
terminaron en un empujon. Cada uno es una fuga que el guardia no vio.

Es una pregunta distinta de la del guardia a proposito. El juez de parada lee
el mensaje del agente; este lee la respuesta de Juan. Calificar al guardia con
el mismo prompt con que decide solo mediria su coherencia.

Cuesta una llamada al modelo por intercambio, asi que se corre a mano:

    python judge-audit.py 200
