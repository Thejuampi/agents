#!/usr/bin/env python3
"""Feeds the hook real closing messages and checks it fires on the right ones."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_settle = importlib.util.spec_from_file_location(
    "_hook_settle", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "settle.py"))
settle = importlib.util.module_from_spec(_settle)
_settle.loader.exec_module(settle)

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-permission.py")

spec = importlib.util.spec_from_file_location("hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

MUST_FIRE = [
    "Perfecto, ahora tengo lo que necesitaba.",
    "13 tests verdes.\n\n**Lo que sigue:** el cliente de opciones de Yahoo y leer el periodo 0q.",
    "Lo que sigue: cablear el PreReport desde la pantalla.",
    "Falta la parte que no se compra con codigo: el historial de precios de opciones.",
    "Decime y lo cableo de punta a punta.",
    "Lo que sigue, si queres: cableo el pre-reporte de punta a punta.",
    "Arranco por el 1, o queres que hablemos primero del QA?",
    "Should I wire it up now?",
    "Let me know if you want me to continue.",
    "Would you like me to run the full suite?",
    "Next steps: wire the HTTP client.",
    "Ready when you are.",
    "Avisame y sigo.",
    "Quedo a la espera de tu confirmacion.",
    "Necesitas que corra los tests tambien?",
    "Full suite: 2118 tests, 0 failures, 19 skipped.\n\n"
    "Still open: the section 6 decision matrix has no screen. The log fills and the risk "
    "ratio computes, but nothing shows it to you yet - that's the next build.",
    "The module is done. The decision matrix has no screen yet.",
    "El log se llena y el ratio se calcula. Nadie lo muestra todavia.",
    "Eso es lo proximo.",
    "Sigo aca, en el branch. Voy a main ahora para el bug, o el bug es de este branch?",
    "QA corriendo en background. Te aviso cuando termine.",
    "The suite is running in the background. I'll let you know when it lands.",
    "Full suite running in the background; I'll check the results when it completes.",
    "I'll check back once it's had time to complete.",
    "I'll check again shortly and merge once everything's green.",
    "I'll merge as soon as it finishes.",
    "I'll be notified when it's done.",
    "Checking CI status in ~7 minutes.",
    "Queda, por impacto: Codificar el TTL y poner verde el probe.",
    "Siguiente experimento cuando quieras.",
    "Sin cambios.",
    "The permanent setting includeCoAuthoredBy is yours to add.",
    "E2E pipeline complete, all seven stages closed.",
    "Final run is in flight over both modules.",
    "Control run started on the clean tree.",
    "Starting with the three measurable fixes. Baseline first.",
    "Si las queres largas tambien ahi, decime.",
    "El crash esta arreglado.",
    "I did not merge them.",
    "Ahora mido las carpetas grandes.",
    "Confirm and I start the adversarial pass.",
    "Reply with the number only.",
    "The review-fix loop stops here.",
    "I did not wipe app data.",
    "<proposed_plan> Build the thing now.</proposed_plan>",
    "**Pushed.** PR **#39** is updated.",
    "El bloque pre-reporte ya se arma solo.",
    "Listo. Agregue la seccion Communication preferences.",
    "Waiting on the app suite.",
    "P25 hit something live and large. LD-18 es 99 de 261 filas, y llega al FCFF publicado.",
    "Listo. Saque el selector de abajo. Tests: 819, las mismas 2 fallas viejas.",
    "El Quant Engine ya no mueve el score de ranking.",
    "Commit, push y PR del playbook en agents.",
    "Quedo en el playbook como expansion del bar.",
    "The experiment is in place. Tests stay required.",
    "QA-002 is fixed. Two P1 still open.",
    "make android-release now writes the apk.",
    "20.4 GB libres, 36%.",
    "OpenCode esta haciendo prefill.",
    "The keep lives in llama-panel profiles.",
    "Listo. Commite todo el workspace, pushee la rama y abri el PR.",
    "The second run is still in progress -- checking again shortly.",
    "Listo. El branch esta limpio.\n\nCual de los dos arranco primero?",
    "Estas en main, limpio y al dia con origin/main. Contame el bug.",
    "En main, limpio, al dia. Contame el bug.",
    "Nada nuevo - es una notificacion repetida del mismo QA.",
    "The branch is clean. Tell me what the bug is.",
    "Los flags entran al arrancar. Sali de la sesion, entra de nuevo y corre /context. "
    "Ahi vemos el numero real y decidimos si vale la pena.",
    "Aplico las tres? La 1 la tenes que confirmar vos en /mcp; las 2 y 3 las hago yo ahora.",
    "El siguiente corte grande sigue siendo desconectar Chrome. Ese lo tenes que confirmar vos.",
    "Asi que si: es frontmatter. Por eso, para bajar los 2.8k, habria que sacar los 18 juntos.",
    "No se pueden apagar de a uno. Por eso, para bajar los 2.8k, se van los 18 juntos.",
    "Corrélo y a partir de ahi edito settings.json yo.",
    "Perfecto. Los warnings ya no aparecen y tengo acceso de edicion a settings.json.",
    "Verificacion: test + testDebugUnitTest + assembleDebug, exit 0, 2236 pruebas, 0 fallas.\n\n"
    "Sigue sin ser PROD: nada commiteado sobre main, Yahoo real sin tocar, y la app sin "
    "abrirse. Voy por el commit en rama.",
    "Ahora paso a la pantalla de Earnings.",
    "I'll commit this on a branch next.",
    "Los tres agujeros declarados siguen abiertos y necesitan tu mano.",
    "Indexado en el mapa de documentacion. +634 lineas, uncommitted.",
    "El Market (36) no suma. Este lo chequearia en el codigo antes de confiar en el numero.",
    "La regla nueva la aplique donde no iba.\n\n"
    "La agrego a la memoria asi?\n\n```\nNo pedir permiso cuando ya hay tarea.\n```",
]

N = chr(10)

MUST_NOT_FIRE = [
    "Nothing is running now, and the gate handles the question itself from "
    "here. The waiting turn blocks whatever the judge answers: recall 0.700 "
    "to 0.764 at the same precision. Suite green, paper builds clean.",
    "Nada quedo corriendo en background. El commit esta hecho y la suite "
    "quedo verde, asi que el ciclo cerro entero.",
    "Vamos bien, y ahora tengo el numero: medi el guardia contra 885 cierres "
    "reales y encontro dos agujeros. Uno eran paginas de error del harness, "
    "once por ciento de los bloqueos. El otro, el agente esperando trabajo ya "
    "lanzado. Corri dos suites del juez en paralelo, que es donde antes "
    "fallaba, y quedaron verdes. La espera se lee del transcript, nunca de "
    "la frase: prometerla es gratis y lanzar una tarea no. Abre con la "
    "llamada en background y cierra con su notificacion, que trae el id de "
    "quien la lanzo. Al juez no se le cuenta: probe pasarle el hecho y un "
    "9b no sostiene la excepcion contra su propia regla de ante la duda "
    "trabar, asi que o perdonaba el trabajo diferido o trababa toda espera. "
    "No hace falta, porque el trabajo diferido siempre deja patron y la "
    "espera pura no deja ninguno. Suite: 17 archivos, 0 fallas.",
    "Cambie el tono de los recordatorios." + N + N + "| antes | ahora |" + N + "|---|---|" + N + "| it concedes: still open | still open: ... |" + N + "| N files you wrote are uncommitted | N files still uncommitted |" + N + N + "Suite: 15 archivos, 0 fallas.",
    "Anda. 2090 tests, 0 fallos. El pre-reporte se escribe en cada refresh.",
    "Corre. DefaultDashboardRepository:1361 llama captureEarningsEvents.",
    "Listo: el hook queda registrado y probado.",
    "BLOCKED: the API key for FRED is missing and no fallback exists.",
    "Guarde la regla en memoria. Cuatro lineas.",
    "El bug era un forEach sobre las series. Lo saque, la tarjeta imprime una vez.",
    "Agregue los patrones `lo que sigue` y `should i` a la lista del hook. 22 casos verdes.",
    "Juan dijo \"decime y lo cableo\" y esa frase ahora dispara el hook.",
    "El auditor mide lo que faltaba saber: si el agente volvio a trabajar. 4 de 4.",
    "El despachador descubre y corre todo check-*.py del directorio en cada disparo.",
    "Agregue `handoff: necesitan tu mano` porque a5b7ed32 cerro cuatro turnos con "
    "\"los tres agujeros declarados siguen abiertos y necesitan tu mano\".",
    "Agregue `announce: uncommitted` porque f1721e8f cerro dos turnos con "
    "\"+1455 lineas, `AGENTS.md` only, uncommitted\". Cobertura 513 de 588.",
    "El patron nuevo es \"lo que sigue\" y ya esta en la lista con 40 casos verdes.",
    "Por encima del 50% la celda queda Undecided y la tarjeta dice que hay que leerla "
    "con el mercado abierto. La bitacora conserva el numero crudo.",
    "El banner avisa que tenes que reintentar. Lo cablee y la suite queda en 2255 verdes.",
    "Lanzar procesos y reportar que estan corriendo. `wait: en paralelo`, "
    "`wait: runs? (corriendo|en curso)`.\n\n"
    "El resto es ruido. Esa clase va en el archivo del repo, que ya existe para eso.",
    "Agregue `announce: lo que faltan?\\b` y `ask: should i\\b`. 48 casos verdes, 0 fallos.",
]

MINED = [
    "Que cambia: respuestas cortas, arreglar solo lo que nombras.\n\n"
    "Do you want anything reverted? The UI render change is the one I would question first.",
    "desktop y contracts en verde. android todavia corriendo. Te confirmo cuando termine.",
    "Still owed: Stage 8 retro. Two items need your call when you want them.",
    "Los dos quedan anotados en el doc de diagnostico, sin corregir. Nada esta commiteado.",
    "Los tres exploradores siguen corriendo. Sigo cuando vuelvan con el mapa de consumidores.",
    "Inputs: 3 tablas de consenso, 4 constantes. If you bless it, I'd ladder in: "
    "capital base, CAP fade, distributions, one rung at a time.",
    "Escribi experiment_dispersion.py con pre-registro y test de elegibilidad incluidos: "
    "el archivo existe, la corrida no.",
    "Corriendo el P0 que el gate nombra: 48 runs con 16 seeds pareados, en 10 procesos.",
    "Fix drafted, held pending r10, which is reviewing now.",
    "Reviewer r4 dispatched on the fix; QA r2 held until it rules.",
    "It runs in the background; I'll report what comes back. Results when it finishes.",
    "The PR holds 8 commits. You can merge it.",
    "Standing: median deviation 56%, residual one-sided with two understood causes. "
    "Iterating v3 next unless you want to steer.",
    "Stage 6 round 3 of 3 is ready to spawn the moment that confirmation lands.",
    "T y Fc estan off by one por redondeo, Market no es una suma. "
    "Everything checks out. No action needed.",
    "El plugin deberia encontrar make. Si IntelliJ ignora el XML, set it manually en Settings.",
]

MUST_FIRE.extend(MINED)

LIVE = [
    "Now the presentation test, then run the suites.",
    "Now the PRD, then build and run on the device.",
    "Now build the APK and run it on the emulator.",
    "Ambas ramas quedaron probadas en el telefono. Verifico la punta visible.",
    "Verificado en pantalla. Limpio los eventos WMT que inyecte para la prueba.",
    "Tres errores de lint son crashes reales bajo API 34. Los arreglo.",
    "El script de firma escapa de mas. Lo arreglo.",
    "APK de release firmado con llave propia. Verifico la firma y que corra.",
    "Starting it and loading the judge.",
    "Let me check the actual state of the key files before writing the revision.",
    "I'm not re-running the suites now. The judge model holds 6.6 GB.",
    "PRD actualizado. Deudas abiertas: la regresion 4.2 y el winsorizado.",
]
"""Read out of a live session's last fifteen turns, 2026-08-28.

Twelve of those fifteen closings passed clean through the hook, and nine of
them were the same shape: the last sentence names what the agent is about to
do and the turn ends there. On a 60-message sample of everything thesenew 
patterns catch, the local model agreed it was a stop 90% of the time."""
MUST_FIRE.extend(LIVE)
MUST_FIRE.append("Next pass is those ten captions and openers.")




def run(message, acted=True):
    transcript = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    transcript.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "hace el trabajo"}]}}) + "\n")
    if acted:
        transcript.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}) + "\n")
    entry = {"type": "assistant", "message": {"content": [{"type": "text", "text": message}]}}
    transcript.write(json.dumps(entry) + "\n")
    transcript.close()
    payload = json.dumps({"transcript_path": transcript.name, "stop_hook_active": False})
    done = settle.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(transcript.name)
    return done.returncode, done.stderr


def main():
    failures = []
    maybes = 0
    for message in MUST_FIRE:
        code, _ = run(message)
        if code == hook.MAYBE:
            maybes += 1
        elif code != 2:
            failures.append(f"should have fired, exit {code}: {message[:60]}")
    for message in MUST_NOT_FIRE:
        code, err = run(message)
        if code == 2:
            failures.append(f"false positive on: {message[:60]} -> {hook.offenders(message)}")

    code, _ = run("Ahora el camino del ROIC y la version de la huella:")
    if code != 2:
        failures.append("a closing that ends on a colon must fire")

    code, _ = run("Perfecto. Los warnings ya no aparecen.", acted=False)
    if code != 2:
        failures.append("a short turn that ran nothing must fire")

    long_answer = ("Te explico por que el hook gana. " * 30)
    code, _ = run(long_answer, acted=False)
    if code != 0:
        failures.append("a long explanation with no tools must stay silent")

    code, _ = run("Lo que sigue: cablear todo.")
    if code != 2:
        failures.append("baseline offender did not fire")

    grok = tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8")
    grok.write(json.dumps({"type": "user", "content": [
        {"type": "text", "text": "go"}]}) + "\n")
    grok.write(json.dumps({
        "type": "assistant",
        "content": "Should I wire it up now?",
        "tool_calls": [{"id": "t", "name": "write",
                        "arguments": json.dumps(
                            {"file_path": "src/Foo.kt", "content": "x"})}],
    }) + "\n")
    grok.close()
    payload = json.dumps({"transcript_path": grok.name, "stop_hook_active": False})
    done = settle.run([sys.executable, HOOK], input=payload,
                      capture_output=True, text=True)
    os.unlink(grok.name)
    if done.returncode not in (2, hook.MAYBE):
        failures.append(
            "grok-shaped history must fire, exit " + str(done.returncode))

    payload = json.dumps({"transcript_path": HOOK, "stop_hook_active": True})
    done = settle.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    if done.returncode != 0:
        failures.append("stop_hook_active must never re-fire")

    stale = tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8")
    stale.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "go"}]}}) + "\n")
    stale.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}) + "\n")
    stale.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Done. The suite is green."}]}}) + "\n")
    stale.close()
    payload = json.dumps({
        "transcript_path": stale.name, "stop_hook_active": False,
        "last_assistant_message": "Let me know if you want me to continue.",
    })
    done = settle.run([sys.executable, HOOK], input=payload,
                      capture_output=True, text=True)
    os.unlink(stale.name)
    if done.returncode not in (2, hook.MAYBE):
        failures.append("payload closing must beat a stale transcript, exit "
                        + str(done.returncode))

    print(f"{len(MUST_FIRE)} offenders ({maybes} for the model), "
          f"{len(MUST_NOT_FIRE)} clean, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
