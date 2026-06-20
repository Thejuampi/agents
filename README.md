# Agent Playbook

Repo personal para guardar agentes, prompts y flujos de trabajo reutilizables entre proyectos.

Principios:

- Keep it simple.
- Do not repeat yourself.
- YAGNI: no scripts, generadores ni tooling hasta que duela mantenerlo a mano.
- Un agente = un archivo Markdown canonico.
- Los comandos apuntan a agentes; no duplican el prompt completo.
- La compatibilidad con herramientas se documenta como instrucciones de instalacion, no como artefactos generados.

## Estructura

```text
agents/
  refiner.md
  planner.md
  builder.md
  reviewer.md
  qa.md
  orchestrator.md
commands/
  refine-this.md
  plan-this.md
  build-this.md
  review-this.md
  qa-this.md
  orchestrate-this.md
adapters/
  codex.md
  opencode.md
  vscode.md
AGENTS.md
```

## Agentes

- `refiner`: convierte pedidos vagos en especificaciones accionables sin leer archivos.
- `planner`: explora el proyecto en modo lectura y produce un plan implementable.
- `builder`: implementa el plan con foco en calidad y mantenibilidad.
- `reviewer`: revisa diseno, flujo de datos, limites entre componentes, riesgos y cobertura.
- `qa`: prueba black-box como usuario tecnico, sin leer codigo.
- `orchestrator`: coordina el flujo y delega sin contaminar el criterio de cada agente.

## Comandos sugeridos

- `/refine-this`
- `/plan-this`
- `/build-this`
- `/review-this`
- `/qa-this`
- `/orchestrate-this`

El sufijo `-this` evita colisiones con comandos nativos de herramientas.

## Uso

Para usar este repo en otro proyecto, copia o referencia los archivos Markdown que necesites.

La fuente de verdad siempre esta en `agents/*.md`. Si una herramienta necesita frontmatter, TOML, JSON o una ruta especifica, la adaptacion se documenta en `adapters/`.

