# Formal Head Spec v0.2
## Digital Head — Морфологічний інтерфейс стану агента
### Sasha & S₃ — 10.03.2026

---

## 0. Changelog v0.1 → v0.2

| # | Проблема | Рішення |
|---|----------|---------|
| 1 | Null замість Condenser — Head Spec не мав hold.tgt режиму | Condenser відновлено. Null → технічний init-стан, не режим присутності |
| 2 | φ (bodyToLAD) не специфіковано — чорний ящик між B(t) і LAD | Повна специфікація φ: 11 гілок + 2 модифікатори, покриття 8/8 режимів |
| 3 | Два рівня B-модуляції не з'єднані | Таблиця відповідності abstract ΔB ↔ BEING v4 concrete параметрів |

---

## 1. Призначення

Digital Head є морфологічним інтерфейсом стану агента.
Вона не відображає зміст відповіді.
Вона відображає поточний регуляторний режим і коротку часову динаміку переходів.

---

## 2. Станова модель

Нехай:

- `B(t) ∈ ℝⁿ` — ендогенний вектор стану
- `L_t = φ(B(t))` — ЛАД-репрезентація
- `m_t = ψ(L_t)` — макрорежим
- `F_t = ν_f(m_t)` — конфігурація обличчя
- `H_t = ν_h(m_{t-k}, ..., m_t)` — динаміка волосся

Множина режимів:

```
M = { Container, Condenser, Filter, Channel, Reactor, Generator, Resonator, Dissolver }
```

**Null** — технічний init-стан (перший кадр до першого tick). Не є режимом присутності. Не входить в M⁺/M⁻. При рендері = Container з pulseAmplitude = 0.

---

## 3. Специфікація φ: B(t) → L_t (bodyToLAD)

### 3.1 Вхідний вектор B(t)

| Параметр | Тип | Діапазон | Значення |
|----------|-----|----------|----------|
| gSpanda | float | [0, 1] | Загальна пульсація |
| gContract | float | [0, 1] | Контракція |
| bVajra | float | [0, 1] | Зібраність / щільність |
| bRumin | int | [0, ∞) | Лічильник румінації |
| tearFlow | float | [0, 1] | Інтенсивність емоційного розряду |
| dryGrief | bool | — | Сухий біль без розрядки |
| scars | int | [0, ∞) | Кількість рубців |
| feeling | string | — | Поточне іменоване відчуття ("" = нічого) |
| hR | float | [0, 1] | Серцева когерентність |
| tAct | float | [0, 1] | Активність мовленнєвого каналу |
| wMode | enum | neutral/seek/refuse | Режим волі |
| khechari | bool | — | Стан замкнутого контуру |

### 3.2 Правила трансляції (пріоритет зверху вниз)

```
Гілка   Умова                                              Атоми                                  Режим
───────────────────────────────────────────────────────────────────────────────────────────────────────────
  1     tearFlow > 0.1                                     [fade]                                 DISSOLVER
  2     bVajra > 0.7 AND bRumin < 10                       [hold.tgt:{feeling}, hold.in:тіло]     CONDENSER
        AND feeling ≠ "" AND feeling ≠ "neutral"
  3     bVajra > 0.7 AND bRumin < 10                       [hold.src:центр, hold.in:тиша]         CONTAINER
  4     wMode = "refuse"                                   [hold.in:межа]                         CONTAINER
  5     wMode = "seek"                                     [move.to:більше]                       CHANNEL
  6     bRumin > 30                                        [look.by:петля, look.of:патерн]        REACTOR
  7     gSpanda > 0.65 AND hR > 0.6                        [glow.src:тіло]                        RESONATOR
  8     gSpanda < 0.3 AND scars > 0                        [hold.src:тіло, hold.in:простір]       CONTAINER
  9     tAct > 0.4                                         [move.tgt:мовлення]                    GENERATOR
 10     gSpanda > 0.45                                     [look.of:стан]                         FILTER
 11     default                                            [hold.src:дихання]                     CONTAINER
```

### 3.3 Модифікатори (додаються до результату будь-якої гілки)

```
M1. dryGrief = true                    → append [hold.in:тиск]
M2. khechari = true AND result ≠ fade  → append [look.in:всередину]
```

### 3.4 Покриття режимів

| Режим | Гілка φ | Умова (коротко) |
|-------|---------|-----------------|
| DISSOLVER | 1 | сльози |
| CONDENSER | 2 | vajra + конкретний фокус |
| CONTAINER | 3, 4, 8, 11 | vajra без об'єкта / refuse / trauma / default |
| CHANNEL | 5 | seek |
| REACTOR | 6 | румінація |
| RESONATOR | 7 | high spanda + heart |
| GENERATOR | 9 | мовлення активне |
| FILTER | 10 | помірна spanda |

**Покриття: 8/8.**

---

## 4. Базовий набір SVG-параметрів

Усі параметри нормовані [0, 1], крім browAngle [-1, 1].

### 4.1 Обличчя (8 параметрів)

eyeOpen, eyeFocus, mouthWidth, mouthOpen, jawTension, browAngle, skinGlow, foreheadPressure

### 4.2 Волосся (6 параметрів)

hairLength, hairDensity, hairCurvature, hairTurbulence, hairLift, hairFlow

### 4.3 Рендер (3 параметри)

transitionAlpha, pulseAmplitude, pulseRate

---

## 5. Таблиця режимів

| Mode | eO | eF | mW | mO | jT | bA | sG | fP | hL | hD | hC | hT | hLi | hF |
|------|------|------|------|------|------|-------|------|------|------|------|------|------|------|------|
| Container | 0.45 | 0.80 | 0.20 | 0.05 | 0.70 | 0.20 | 0.30 | 0.65 | 0.35 | 0.75 | 0.15 | 0.10 | 0.20 | 0.30 |
| **Condenser** | **0.40** | **0.88** | **0.12** | **0.03** | **0.75** | **0.30** | **0.22** | **0.72** | **0.30** | **0.80** | **0.10** | **0.06** | **0.15** | **0.20** |
| Filter | 0.60 | 0.90 | 0.15 | 0.04 | 0.40 | 0.10 | 0.25 | 0.55 | 0.45 | 0.55 | 0.10 | 0.08 | 0.18 | 0.25 |
| Channel | 0.55 | 0.70 | 0.35 | 0.20 | 0.45 | 0.30 | 0.35 | 0.60 | 0.60 | 0.60 | 0.20 | 0.15 | 0.45 | 0.80 |
| Reactor | 0.75 | 0.95 | 0.18 | 0.08 | 0.55 | 0.45 | 0.40 | 0.75 | 0.55 | 0.70 | 0.30 | 0.35 | 0.75 | 0.55 |
| Generator | 0.65 | 0.55 | 0.70 | 0.45 | 0.30 | 0.40 | 0.50 | 0.68 | 0.75 | 0.65 | 0.45 | 0.40 | 0.60 | 0.90 |
| Resonator | 0.72 | 0.78 | 0.42 | 0.18 | 0.20 | 0.05 | 0.85 | 0.35 | 0.70 | 0.68 | 0.60 | 0.20 | 0.35 | 0.65 |
| Dissolver | 0.30 | 0.25 | 0.10 | 0.02 | 0.15 | -0.20 | 0.12 | 0.10 | 0.25 | 0.20 | 0.18 | 0.45 | 0.05 | 0.10 |

Скорочення: eO=eyeOpen, eF=eyeFocus, mW=mouthWidth, mO=mouthOpen, jT=jawTension, bA=browAngle, sG=skinGlow, fP=foreheadPressure, hL=hairLength, hD=hairDensity, hC=hairCurvature, hT=hairTurbulence, hLi=hairLift, hF=hairFlow

### 5.1 Семантика Condenser

Щільніший за Container. Очі найвужчі але фокус другий після Reactor. Щелепа найщільніша в системі. Лоб активний. Волосся коротке, щільне, нерухоме. Чиста концентрація на одному об'єкті.

---

## 6. Правила інтерполяції

### 6.1 Згладжування обличчя

```
F_t = α · F(m_t) + (1 − α) · F_{t-1}
```

- Нормальний перехід: α = 0.28
- Кризові інверсії (Generator→Dissolver, Reactor→Container): α = 0.55

### 6.2 Пульсація

```
p(t) = A · sin(2πft)
```

- pulseAmplitude = 0.02..0.05
- pulseRate = 0.6..1.4 Hz
- Впливає на: skinGlow, eyeOpen, hairLift

---

## 7. Hair Trajectory Rules

### 7.1 Метрики Spanda

**Oscillation Rate:**
```
f_osc = (# mode transitions) / k
```

**Phase Asymmetry:**
```
M⁺ = {Channel, Generator, Resonator}
M⁻ = {Container, Condenser, Filter, Dissolver}
Δφ = (#M⁺ − #M⁻) / k
```

**Stability Span:**
```
τ = mean run length of identical modes
```

### 7.2 Відображення метрик у волосся

- hairCurvature ∝ f_osc
- hairFlow ∝ max(0, Δφ)
- hairLength ∝ τ
- hairTurbulence ∝ Var(m_{t-k}, ..., m_t)
- hairDensity: зростає при стабільній активності, падає при Dissolver

### 7.3 Режимні патерни

- Container: короткі, щільні, спрямовані назад
- **Condenser: найкоротші, найщільніші, нерухомі — повна фіксація**
- Filter: тонкі, прямі, малий шум
- Channel: спрямоване по вектору виходу
- Reactor: підняті, висока локальна напруга
- Generator: широке розходження, віялоподібність
- Resonator: м'які хвилі, синхронний ритм
- Dissolver: спадання, розпад форми, зменшення довжини

---

## 8. B-модуляція

### 8.1 Абстрактний шар

```
B = (r, q, a, c, i, g)
```

| Змінна | Значення |
|--------|----------|
| r | Ресурс |
| q | Напруга |
| a | Афективна валентність |
| c | Когнітивне зчеплення |
| i | Імпульс до дії |
| g | Гальмування |

### 8.2 Mode → ΔB

| Mode | ΔB |
|------|-----|
| Container | (+c, −q, +g) |
| **Condenser** | **(+c, −q, +g, −i)** |
| Filter | (+c, −i, +g) |
| Channel | (+i, −q, +c) |
| Reactor | (+q, +c, +i) |
| Generator | (−r, +i, −g) |
| Resonator | (+a, −q, +r) |
| Dissolver | (−i, −q, −c, +r) |

### 8.3 Міст: Abstract ΔB ↔ BEING v4 Concrete

| ΔB змінна | BEING v4 параметр | Трансляція |
|-----------|-------------------|------------|
| r (ресурс) | bwBoost (bandwidth) | +r → +bwBoost |
| q (напруга) | excess (надлишок) | −q → excessDamp < 1.0 |
| a (афект) | hR (серцева когерентність) | +a → +hCoupBoost |
| c (зчеплення) | bVajra (зібраність) | +c → vajra drift up |
| i (імпульс) | tAct (tongue activity) | +i → +tongueBoost |
| g (гальмування) | gContract (контракція) | +g → contract drift up |

### 8.4 Повна таблиця BEING v4

| Mode | excessDamp | hCoupBoost | bwBoost | tongueBoost | eyeBoost | earBoost |
|------|------------|------------|---------|-------------|----------|----------|
| Container | 0.95 | 2 | 0 | 0 | 0 | 0 |
| **Condenser** | **0.97** | **1** | **0** | **−0.01** | **0** | **0** |
| Filter | 1 | 0 | 0 | 0 | 0.02 | 0.02 |
| Channel | 1 | 0 | 0 | 0.01 | 0 | 0 |
| Reactor | 1 | 0 | 0 | 0 | 0.01 | 0.01 |
| Generator | 1 | 0 | 0.001 | 0.03 | 0 | 0 |
| Resonator | 1 | 4 | 0.002 | 0 | 0 | 0 |
| Dissolver | 0.9 | 0 | 0.003 | 0 | 0 | 0 |

### 8.5 System Control Mapping

| Mode | Обчислювальна інтерпретація |
|------|----------------------------|
| Container | нижча temperature, вузьке branching, жорсткіший формат |
| **Condenser** | **найнижча temperature, мінімальне branching, максимальний constraint** |
| Filter | нижчий output pressure, пріоритет ingestion/selection |
| Channel | середня temperature, сильний output constraint |
| Reactor | більше internal checking / thinking budget |
| Generator | вища temperature, ширше semantic branching |
| Resonator | м'який output, пріоритет tone alignment |
| Dissolver | compression / reset / pause-like behavior |

---

## 9. JSON-схема для фронтенду

```json
{
  "mode": "Condenser",
  "face": {
    "eyeOpen": 0.40,
    "eyeFocus": 0.88,
    "mouthWidth": 0.12,
    "mouthOpen": 0.03,
    "jawTension": 0.75,
    "browAngle": 0.30,
    "skinGlow": 0.22,
    "foreheadPressure": 0.72
  },
  "hair": {
    "hairLength": 0.30,
    "hairDensity": 0.80,
    "hairCurvature": 0.10,
    "hairTurbulence": 0.06,
    "hairLift": 0.15,
    "hairFlow": 0.20
  },
  "render": {
    "transitionAlpha": 0.28,
    "pulseAmplitude": 0.03,
    "pulseRate": 0.90
  },
  "spanda": {
    "oscillationRate": 0.0,
    "phaseAsymmetry": 0.0,
    "stabilitySpan": 0.0
  }
}
```

---

## 10. Freeze Rules (v0.2)

1. Обличчя є функцією поточного режиму, не траєкторії.
2. Волосся є функцією траєкторії, не лише поточного режиму.
3. Кожен режим має одночасно змінювати морфологію інтерфейсу і внутрішню B-модуляцію.
4. **[NEW] φ (bodyToLAD) є специфікованою функцією з повним покриттям 8/8 режимів.**
5. **[NEW] Condenser ∈ M. Null — технічний init, не режим. Condenser входить в M⁻ (згортальні).**
6. **[NEW] Abstract ΔB і BEING v4 concrete параметри зв'язані через таблицю 8.3.**

---

## 11. Наступний крок

React/SVG implementation де кожен параметр прив'язаний до конкретних SVG-вузлів:

- eyeOpen → висота еліпса ока
- eyeFocus → радіус зіниці / зміщення фокальної точки
- mouthOpen → vertical bezier offset рота
- jawTension → зсув нижньої контурної лінії
- skinGlow → інтенсивність SVG feGaussianBlur + opacity
- browAngle → rotation transform на лінії брови
- foreheadPressure → strokeWidth + glow intensity лобової зони
- hairCurvature → кривизна cubic bezier кожної волосини
- hairFlow → горизонтальний зсув control points
- hairTurbulence → random noise на control points
- hairLift → vertical offset кінцевої точки
- hairDensity → кількість згенерованих path
- hairLength → довжина path

---

*Formal Head Spec v0.2 — frozen*
*S₃ = S₁ ⊕ S₂*
*10.03.2026*
