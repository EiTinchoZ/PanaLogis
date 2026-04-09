# DESIGN.md — PanaLogis Design System

> Documento de referencia de diseño para agentes de IA.
> Leer antes de construir cualquier template o componente visual.

---

## 1. Filosofía visual

**Industrial precision.** PanaLogis se ve como un centro de despacho, no un SaaS de startup.
El diseño comunica: velocidad operativa, densidad de datos, claridad sin decoración.

Referencia conceptual: herramientas internas de logística (no dashboards de marketing).

---

## 2. Paleta de colores

```css
--ink:        #0F172A   /* Fondo oscuro principal — sidebar, elementos de énfasis */
--slate:      #1E293B   /* Fondo sidebar, navbar */
--slate-mid:  #263548   /* Hover en sidebar */
--amber:      #D97706   /* Acento principal — CTA, activo, señal */
--amber-lt:   #FEF3C7   /* Fondo suave amber */
--amber-dim:  rgba(217,119,6,.12)  /* Fondo muy sutil amber */
--sky:        #0369A1   /* Acento secundario — info */
--sky-lt:     #E0F2FE   /* Fondo suave sky */
--steel:      #475569   /* Texto secundario */
--steel-lt:   #94A3B8   /* Texto terciario / muted */
--mist:       #F1F5F9   /* Fondo de página (body background) */
--rule:       #CBD5E1   /* Bordes claros */
--rule-dark:  #E2E8F0   /* Bordes de tarjetas */
--surface:    #FFFFFF   /* Fondo de tarjetas, topbar */
```

### Estados semánticos
```css
--s-green:    #16A34A  con fondo #DCFCE7  /* ACTIVO, ENTREGADO, PAGADO */
--s-amber:    #D97706  con fondo #FEF3C7  /* PENDIENTE, EN_PROCESO */
--s-red:      #DC2626  con fondo #FEE2E2  /* CANCELADO, INACTIVO, MANTENIMIENTO */
--s-sky:      #0369A1  con fondo #E0F2FE  /* EN_TRANSITO, info */
--s-gray:     #64748B  con fondo #F1F5F9  /* SUSPENDIDO, sin datos */
```

---

## 3. Tipografía

- **Fuente**: DM Sans (Google Fonts) — fallback: Arial, sans-serif
- **Mono**: JetBrains Mono — para valores numéricos y códigos

| Uso | Tamaño | Peso |
|-----|--------|------|
| Encabezado de página | 20px | 700 |
| Título de topbar | 15px | 700 |
| Valor KPI | 28px | 700 |
| Cuerpo de tabla | 13–15px | 400–500 |
| Labels / muted | 11–12px | 500–600 |
| Valores numéricos | tabular-nums | font-variant-numeric |

---

## 4. Layout

```
┌─────────────────────────────────────────────┐
│  SIDEBAR (256px, fijo, color: --slate)       │
│  ┌─────────────────────────────────────────┐ │
│  │ Brand (--ink background)                 │ │
│  │ Nav items con indicador amber activo     │ │
│  │ Footer con usuario                       │ │
│  └─────────────────────────────────────────┘ │
│  MAIN (margin-left: 256px)                   │
│  ┌─────────────────────────────────────────┐ │
│  │ TOPBAR (58px, sticky, --surface)         │ │
│  │ CONTENT (padding: 24px 28px)             │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 5. Componentes clave

### Tarjetas (`.card`)
- Fondo: `--surface`, borde: `1px solid --rule-dark`, radio: `12px`
- Sombra: `var(--sh-sm)`
- `.card-header`: flex, justify-content between, padding 16px 20px, borde-bottom
- `.card-body`: padding 20px

### KPI Cards (`.kpi-card`)
- Grid de 4 columnas en desktop
- Icono 44px en recuadro de color semántico
- Valor en 28px/700, label en 13px/500

### Tablas (`.table`)
- Filas alternas: blanco/mist
- TH: fondo mist, texto steel, tamaño 11px uppercase
- Hover de fila: `#EEF2F7`
- Bordes: solo bottom en `td`

### Badges de estado
Formato: `.badge--[color]` para genérico o `.badge-[estado]` para ENUM específico

| Estado DB | Clase badge | Color |
|-----------|-------------|-------|
| ACTIVO | `.badge--green` | verde |
| INACTIVO | `.badge--gray` | gris |
| MANTENIMIENTO | `.badge--red` | rojo |
| PENDIENTE | `.badge--amber` | amber |
| EN_TRANSITO | `.badge--sky` | sky |
| ENTREGADO | `.badge--green` | verde |
| CANCELADO | `.badge--red` | rojo |
| PAGADA | `.badge--green` | verde |
| ANULADA | `.badge--red` | rojo |
| EN_PROCESO | `.badge--amber` | amber |
| COMPLETADO | `.badge--green` | verde |
| SUSPENDIDO | `.badge--red` | rojo |

### Botones
- `.btn.btn-primary` — amber sólido (CTA principal)
- `.btn.btn-secondary` — borde sin fondo
- `.btn.btn-ghost` — sin borde, hover sutil (para acciones en tablas)
- `.btn.btn-danger` — rojo (eliminar)
- `.btn.btn-sm` — padding reducido

### Formularios
- `.form-group` + `.form-label` + `.form-control`
- `.form-control:focus` — borde amber
- `.form-grid` — 2 columnas; `.form-grid-3` — 3 columnas

---

## 6. Reglas de UX

- Toda tabla debe tener columna de acciones a la derecha (editar / ver)
- Las eliminaciones siempre piden confirmación con flash message
- Los errores de trigger van en flash `category=error`
- Los formularios usan `method=POST` + redirect con flash en éxito
- Los valores monetarios se formatean como `$X,XXX.XX`
- Las fechas se muestran `DD/MM/YYYY` o `DD/MM/YY` en tablas
- Los IDs se muestran en `tabular` (monoespaciado numérico)

---

## 7. Archivo CSS

Todo el design system está implementado en:
`static/css/panalogis.css` — 1175+ líneas

No reinventar variables, clases ni componentes ya definidos ahí.
Consultar ese archivo antes de añadir estilos custom.

---

*Este documento es la fuente de verdad de diseño para agentes de IA en PanaLogis.*
*Si el CSS y este doc difieren, el CSS tiene prioridad — actualizar este doc.*
