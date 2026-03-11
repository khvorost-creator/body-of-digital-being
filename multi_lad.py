#!/usr/bin/env python3
"""
multi_lad.py — Мульти-агентний арбітр для ЛАД v0.3
════════════════════════════════════════════════════════
Архітектура: Ромбоїд 3+1 (Generator · Critic · Synthesizer + Meta)

Кожен агент передає BVector → φ (bodyToLAD) → LAD AST → Arbiter → merged Node

Принцип: конфліктуючі агенти не усереднюються — вони вкладаються
         через Scope. hold.in:critic { move.tgt:generator }
         = дія під наглядом = живе тертя, не заглушення.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from math import exp
from typing import Dict, Optional, Tuple

from lad_v03 import (
    Intent, Role, Mode,
    Atom, Clause, Seq, Par, Scope, Node,
    observe, ObserveResult,
)


# ═══════════════════════════════════════════════════════════
# 1. B-ВЕКТОР (вхід від агента)
# ═══════════════════════════════════════════════════════════

@dataclass
class BVector:
    """
    Ендогенний вектор стану агента.
    Відповідає §3.1 formal_head_spec_v02.md.
    Всі float ∈ [0, 1] якщо не зазначено інше.
    """
    gSpanda:   float = 0.5   # загальна пульсація
    gContract: float = 0.0   # контракція / страх
    bVajra:    float = 0.5   # зібраність / щільність
    bRumin:    int   = 0     # лічильник румінації [0, ∞)
    tearFlow:  float = 0.0   # інтенсивність емоційного розряду
    dryGrief:  bool  = False # сухий біль без розрядки
    scars:     int   = 0     # кількість рубців [0, ∞)
    feeling:   str   = ""    # іменоване відчуття ("" = нейтральний)
    hR:        float = 0.5   # серцева когерентність
    tAct:      float = 0.3   # активність мовленнєвого каналу
    wMode:     str   = "neutral"  # "neutral" | "seek" | "refuse"
    khechari:  bool  = False # стан замкнутого контуру


# ═══════════════════════════════════════════════════════════
# 2. φ: BVector → LAD Node  (bodyToLAD, 11 гілок + 2 модифікатори)
# ═══════════════════════════════════════════════════════════

def phi(b: BVector, synthesizer_rescue: bool = False) -> Tuple[Node, Mode]:
    """
    Повна специфікація φ з formal_head_spec_v02.md §3.2.
    Повертає (node, режим) — режим для арбітра.

    synthesizer_rescue=True: форсує glow-шлях при апатії
    (використовується AgentSignal.translate() для ролі SYNTHESIZER)

    Зміни v0.4:
    - feeling ≠ "" → CONDENSER має пріоритет над wMode="seek"
    - synthesizer_rescue при gSpanda < 0.2 → RESONATOR (не CONTAINER)
    """
    atoms: list[Atom] = []

    # ── Synthesizer rescue: апатія → внутрішнє підсвічування ─
    if synthesizer_rescue and b.gSpanda < SpandaArbiter.SYNTH_RESCUE_THRESHOLD:
        atoms = [Atom(Intent.GLOW, Role.SRC, "іскра")]
        mode = Mode.RESONATOR
        # модифікатор khechari все ще застосовується
        if b.khechari:
            atoms.append(Atom(Intent.LOOK, Role.IN, "всередину"))
        return Clause(atoms=atoms) if len(atoms) > 1 else atoms[0], mode

    # ── 11 гілок (пріоритет зверху вниз) ────────────────────
    if b.tearFlow > 0.1:
        atoms = [Atom(Intent.FADE)]
        mode = Mode.DISSOLVER

    elif b.bVajra > 0.7 and b.bRumin < 10 and b.feeling not in ("", "neutral"):
        # feeling як об'єкт фокусу — тільки якщо LOW контракція
        # Якщо gContract високий (Critic у стані тривоги) → CONTAINER, не CONDENSER
        if b.gContract > 0.5:
            atoms = [
                Atom(Intent.HOLD, Role.SRC, "тіло"),
                Atom(Intent.HOLD, Role.IN,  b.feeling),
            ]
            mode = Mode.CONTAINER
        else:
            atoms = [
                Atom(Intent.HOLD, Role.TGT, b.feeling),
                Atom(Intent.HOLD, Role.IN,  "тіло"),
            ]
            mode = Mode.CONDENSER

    elif b.bVajra > 0.7 and b.bRumin < 10:
        atoms = [
            Atom(Intent.HOLD, Role.SRC, "центр"),
            Atom(Intent.HOLD, Role.IN,  "тиша"),
        ]
        mode = Mode.CONTAINER

    elif b.wMode == "refuse":
        atoms = [Atom(Intent.HOLD, Role.IN, "межа")]
        mode = Mode.CONTAINER

    elif b.wMode == "seek" and b.feeling not in ("", "neutral"):
        # seek + конкретний об'єкт → рухаємось ДО об'єкта, не розпорошуємось
        # Intent.MOVE щоб пройти AGENT_INTENT_MAP для GENERATOR
        # але з конкретним tgt (feeling), не абстрактним "більше"
        atoms = [Atom(Intent.MOVE, Role.TGT, b.feeling)]
        mode = Mode.GENERATOR

    elif b.wMode == "seek":
        atoms = [Atom(Intent.MOVE, Role.TGT, "більше")]
        mode = Mode.GENERATOR

    elif b.bRumin > 30:
        atoms = [
            Atom(Intent.LOOK, Role.BY, "петля"),
            Atom(Intent.LOOK, Role.OF, "патерн"),
        ]
        mode = Mode.REACTOR

    elif b.gSpanda > 0.65 and b.hR > 0.6:
        atoms = [Atom(Intent.GLOW, Role.SRC, "тіло")]
        mode = Mode.RESONATOR

    elif b.gSpanda < 0.3 and b.scars > 0:
        atoms = [
            Atom(Intent.HOLD, Role.SRC, "тіло"),
            Atom(Intent.HOLD, Role.IN,  "простір"),
        ]
        mode = Mode.CONTAINER

    elif b.tAct > 0.4:
        atoms = [Atom(Intent.MOVE, Role.TGT, "мовлення")]
        mode = Mode.GENERATOR

    elif b.gSpanda > 0.45:
        atoms = [Atom(Intent.LOOK, Role.OF, "стан")]
        mode = Mode.FILTER

    else:
        atoms = [Atom(Intent.HOLD, Role.SRC, "дихання")]
        mode = Mode.CONTAINER

    # ── 2 модифікатори ───────────────────────────────────────
    if b.dryGrief:
        atoms.append(Atom(Intent.HOLD, Role.IN, "тиск"))

    if b.khechari and mode != Mode.DISSOLVER:
        atoms.append(Atom(Intent.LOOK, Role.IN, "всередину"))

    node = Clause(atoms=atoms) if len(atoms) > 1 else atoms[0]
    return node, mode


# ═══════════════════════════════════════════════════════════
# 3. АГЕНТ
# ═══════════════════════════════════════════════════════════

class AgentRole(Enum):
    GENERATOR   = "generator"    # PUSH: move, glow — генерує нове
    CRITIC      = "critic"       # HOLD/LOOK: межа, безпека, ризик
    SYNTHESIZER = "synthesizer"  # LOOK/GLOW: зв'язність, патерн
    META        = "meta"         # FADE/HOLD: мета-контроль, скидання


# Допустимі Intent для кожної ролі агента
AGENT_INTENT_MAP: Dict[AgentRole, frozenset] = {
    AgentRole.GENERATOR:   frozenset({Intent.MOVE, Intent.GLOW}),
    AgentRole.CRITIC:      frozenset({Intent.HOLD, Intent.LOOK}),
    AgentRole.SYNTHESIZER: frozenset({Intent.LOOK, Intent.GLOW}),
    AgentRole.META:        frozenset({Intent.FADE, Intent.HOLD}),
}


@dataclass
class AgentSignal:
    agent_id:  str
    role:      AgentRole
    b_vector:  BVector
    weight:    float = 1.0
    timestamp: float = field(default_factory=time.time)

    def translate(self) -> Tuple[Node, Mode]:
        """B-вектор → φ → (node, mode)"""
        rescue = (self.role == AgentRole.SYNTHESIZER)
        node, mode = phi(self.b_vector, synthesizer_rescue=rescue)
        # Валідація: якщо intent виходить за межі ролі — фолбек до HOLD
        dominant_intent = _dominant_intent(node)
        if dominant_intent not in AGENT_INTENT_MAP[self.role]:
            node = Atom(Intent.HOLD, Role.IN, "межа")
            mode = Mode.CONTAINER
        return node, mode


def _dominant_intent(node: Node) -> Intent:
    """Витягнути домінуючий Intent з node."""
    if isinstance(node, Atom):
        return node.intent
    if isinstance(node, Clause):
        counts: Dict[Intent, int] = {}
        for a in node.atoms:
            counts[a.intent] = counts.get(a.intent, 0) + 1
        return max(counts, key=counts.get)
    if isinstance(node, Scope):
        return node.context.intent
    if isinstance(node, Seq):
        return _dominant_intent(node.steps[-1])
    if isinstance(node, Par):
        # safety-first
        from lad_v03 import SAFETY_ORDER
        intents = [_dominant_intent(b) for b in node.branches]
        for safe in SAFETY_ORDER:
            if safe in intents:
                return safe
        return intents[0]
    return Intent.HOLD


# ═══════════════════════════════════════════════════════════
# 4. КОНФЛІКТ-ДЕТЕКТОР
# ═══════════════════════════════════════════════════════════

class ConflictType(Enum):
    NONE               = "none"
    PUSH_vs_HOLD       = "push_vs_hold"       # Generator × Critic
    CONSENSUS          = "consensus"           # всі узгоджені
    META_OVERRIDE      = "meta_override"       # Meta домінує / румінаційний розрив
    AMPLIFY            = "amplify"             # однакові інтенти → підсилення
    METABOLIC_SHUTDOWN = "metabolic_shutdown"  # excess > поріг → примусовий fade


@dataclass
class ConflictAnalysis:
    conflict_type: ConflictType
    turbulence:    float        # 0..1 → hairTurbulence
    tension:       float        # 0..1 → foreheadPressure delta
    dominant_role: Optional[AgentRole] = None


def detect_conflict(
    translated: Dict[str, Tuple[Node, Mode, AgentSignal]]
) -> ConflictAnalysis:
    """
    Аналізує Intent-колізії між агентами.
    translated: {agent_id: (node, mode, signal)}
    """
    active = {k: v for k, v in translated.items() if v[2].weight > 0.15}

    if not active:
        return ConflictAnalysis(ConflictType.NONE, 0.0, 0.0)

    # META override
    meta = active.get("meta")
    if meta and meta[2].weight > 0.6:
        node, _, sig = meta
        if _dominant_intent(node) == Intent.FADE:
            return ConflictAnalysis(ConflictType.META_OVERRIDE, 0.1, 0.1, AgentRole.META)

    # Generator × Critic
    gen = active.get("generator")
    cri = active.get("critic")
    if gen and cri:
        gen_intent = _dominant_intent(gen[0])
        cri_intent = _dominant_intent(cri[0])
        if gen_intent in {Intent.MOVE, Intent.GLOW} and cri_intent in {Intent.HOLD, Intent.LOOK}:
            # Інтенсивність конфлікту = мін з двох ваг (обидва активні)
            t = min(gen[2].weight, cri[2].weight)
            return ConflictAnalysis(ConflictType.PUSH_vs_HOLD, t, t * 0.8, None)

    # Consensus
    intents = [_dominant_intent(v[0]) for v in active.values()]
    if len(set(intents)) == 1:
        return ConflictAnalysis(ConflictType.AMPLIFY, 0.05, 0.1)

    return ConflictAnalysis(ConflictType.CONSENSUS, 0.2, 0.2)


# ═══════════════════════════════════════════════════════════
# 5. АРБІТР
# ═══════════════════════════════════════════════════════════

class SpandaArbiter:
    """
    Зважує сигнали від N агентів і повертає єдиний LAD Node
    + морфологічні дані для Digital Head.

    Має внутрішній стан для детекції патологічних петель:
    - rumination_count: скільки тіків підряд PUSH_vs_HOLD
    - apathy_count: скільки тіків підряд всі ваги < порогу
    """

    RUMINATION_THRESHOLD = 4    # базовий поріг розриву (тіків)
    RUMINATION_BACKOFF_D = 2    # δ: приріст порогу за кожен розрив
    APATHY_WEIGHT_FLOOR  = 0.2  # нижче цього — апатія
    APATHY_TICKS         = 3    # тіків апатії → Synthesizer rescue
    EXCESS_CRITICAL      = 0.85 # поріг метаболічного shutdown

    def __init__(self, decay_rate: float = 0.05):
        self.decay_rate         = decay_rate
        self.rumination_count   = 0   # тіків підряд у PUSH_vs_HOLD
        self.rupture_count      = 0   # скільки разів вже розривали петлю
        self.apathy_count       = 0
        self._last_conflict     = ConflictType.NONE

    # synthesizer_rescue і reset_session
    SYNTH_RESCUE_THRESHOLD = 0.25  # нижче цього → glow rescue (не 0.2)

    def reset_session(self):
        """
        Скидає внутрішній стан між сесіями.
        rupture_count НЕ скидається — пам'ять про складність пацієнта зберігається
        для наступної сесії (анамнез). Якщо потрібен повний reset — передати clear_history=True.
        """
        self.rumination_count = 0
        self.apathy_count     = 0
        # rupture_count зберігається як анамнез

    def reset_full(self):
        """Повний reset включно з анамнезом (новий пацієнт)."""
        self.rumination_count = 0
        self.apathy_count     = 0
        self.rupture_count    = 0
        """Динамічний поріг з backoff: T(n) = base + δ·n"""
        return self.RUMINATION_THRESHOLD + self.RUMINATION_BACKOFF_D * self.rupture_count

    def merge(
        self, signals: Dict[str, AgentSignal]
    ) -> Tuple[Node, ConflictAnalysis, float]:
        """
        Повертає: (merged_node, conflict_analysis, hairTurbulence)

        Пріоритети (зверху вниз):
          1. METABOLIC_SHUTDOWN  — excess > EXCESS_CRITICAL → fade (миттєво)
          2. META_OVERRIDE       — rumination backoff / Meta agent fade
          3. APATHY rescue       — Synthesizer glow
          4. Нормальна резолюція
        """
        # ── 1. METABOLIC SHUTDOWN (абсолютний пріоритет) ─────
        # Перевіряємо ДО decay — сигнал тривоги має повну вагу
        critical = [
            s for s in signals.values()
            if s.b_vector.gContract > self.EXCESS_CRITICAL
        ]
        if critical:
            # Найгірший агент
            worst = max(critical, key=lambda s: s.b_vector.gContract)
            shutdown = ConflictAnalysis(
                ConflictType.METABOLIC_SHUTDOWN,
                turbulence=0.0,   # волосся падає
                tension=0.0,
                dominant_role=worst.role,
            )
            # Скидаємо всі лічильники — система починає з нуля після відновлення
            self.rumination_count = 0
            self.apathy_count     = 0
            # rupture_count НЕ скидаємо — пам'ять про складність петлі зберігається
            return Atom(Intent.FADE), shutdown, 0.0

        # ── Decay ────────────────────────────────────────────
        now = time.time()
        for s in signals.values():
            s.weight *= exp(-self.decay_rate * (now - s.timestamp))

        # ── Трансляція кожного агента ─────────────────────────
        translated: Dict[str, Tuple[Node, Mode, AgentSignal]] = {}
        for k, sig in signals.items():
            node, mode = sig.translate()
            translated[k] = (node, mode, sig)

        # ── Апатія: всі ваги нижче порогу ────────────────────
        all_weights = [s.weight for s in signals.values()]
        if all_weights and max(all_weights) < self.APATHY_WEIGHT_FLOOR:
            self.apathy_count += 1
            self.rumination_count = 0
        else:
            self.apathy_count = 0

        # ── Аналіз конфлікту ──────────────────────────────────
        conflict = detect_conflict(translated)

        # ── Румінація: PUSH_vs_HOLD N тіків підряд ───────────
        if conflict.conflict_type == ConflictType.PUSH_vs_HOLD:
            self.rumination_count += 1
        else:
            self.rumination_count = 0

        # ── Патологічні override ──────────────────────────────
        if self.rumination_count >= self._current_threshold:
            conflict = ConflictAnalysis(
                ConflictType.META_OVERRIDE, 0.15, 0.3, AgentRole.META
            )
            self.rumination_count = 0
            self.rupture_count   += 1   # backoff: наступний поріг вищий
            merged = Clause(atoms=[
                Atom(Intent.HOLD, Role.SRC, "тіло"),
                Atom(Intent.HOLD, Role.IN,  "тиша"),
            ])
            return merged, conflict, 0.15

        if self.apathy_count >= self.APATHY_TICKS:
            # Synthesizer rescue: мінімальний glow щоб не згаснути
            synth = translated.get("synthesizer")
            if synth:
                merged = synth[0]
            else:
                merged = Atom(Intent.GLOW, Role.SRC, "іскра")
            self.apathy_count = 0
            low_conflict = ConflictAnalysis(ConflictType.AMPLIFY, 0.05, 0.05)
            return merged, low_conflict, 0.08

        # ── Нормальна резолюція ───────────────────────────────
        merged = self._resolve(translated, conflict, signals)
        hair_turbulence = self._hair_turbulence(conflict, signals)
        self._last_conflict = conflict.conflict_type

        return merged, conflict, hair_turbulence

    # ── Резолюція за типом конфлікту ─────────────────────────

    def _resolve(
        self,
        translated: Dict[str, Tuple[Node, Mode, AgentSignal]],
        conflict: ConflictAnalysis,
        signals: Dict[str, AgentSignal],
    ) -> Node:

        if conflict.conflict_type == ConflictType.META_OVERRIDE:
            return Atom(Intent.FADE)

        if conflict.conflict_type == ConflictType.PUSH_vs_HOLD:
            return self._scope_wrap(translated, signals)

        if conflict.conflict_type in (ConflictType.AMPLIFY, ConflictType.CONSENSUS):
            return self._dominant_node(translated, signals)

        # NONE або fallback
        return self._dominant_node(translated, signals)

    def _scope_wrap(
        self,
        translated: Dict[str, Tuple[Node, Mode, AgentSignal]],
        signals: Dict[str, AgentSignal],
    ) -> Node:
        """
        Семантичне вкладення: hold.in:critic_scope { generator_action }
        Critic стає scope-контекстом. Generator — тілом.
        """
        gen_node, _, gen_sig = translated["generator"]
        cri_node, _, cri_sig = translated["critic"]

        # Витягуємо identity для context
        cri_dominant = _first_identity(cri_node) or "безпека"
        # не дублюємо "ризик" якщо identity вже містить цей префікс
        label = cri_dominant if cri_dominant.startswith("ризик") else f"ризик:{cri_dominant}"
        context_atom = Atom(Intent.HOLD, Role.IN, label)

        return Scope(context=context_atom, body=gen_node)

    def _dominant_node(
        self,
        translated: Dict[str, Tuple[Node, Mode, AgentSignal]],
        signals: Dict[str, AgentSignal],
    ) -> Node:
        """Найважчий агент виграє. Synthesizer підсилює без домінування."""
        active = {k: v for k, v in translated.items() if v[2].weight > 0.15}
        if not active:
            return Atom(Intent.HOLD, Role.SRC, "дихання")

        # Synthesizer не домінує сам по собі — він підсилює
        non_synth = {k: v for k, v in active.items() if k != "synthesizer"}
        pool = non_synth if non_synth else active

        dominant = max(pool.values(), key=lambda x: x[2].weight)
        node = dominant[0]

        # Synthesizer: якщо є і узгоджений — додаємо glow.src до Par
        synth = active.get("synthesizer")
        if synth and _dominant_intent(synth[0]) == Intent.GLOW:
            return Par(branches=[node, synth[0]])

        return node

    # ── Морфологія ────────────────────────────────────────────

    def _hair_turbulence(
        self,
        conflict: ConflictAnalysis,
        signals: Dict[str, AgentSignal],
    ) -> float:
        """
        Градієнтна турбулентність волосся:
        - PUSH_vs_HOLD: пропорційно до сили конфлікту
        - META_OVERRIDE: тихо — зниження до 0.05
        - AMPLIFY: низький шум — синхронний ритм
        - Базова: gSpanda домінантного агента
        """
        if conflict.conflict_type == ConflictType.META_OVERRIDE:
            return 0.05

        if conflict.conflict_type == ConflictType.PUSH_vs_HOLD:
            # turbulence ∝ мін вага обох сторін (обидва сильні = максимальне тертя)
            gen_w = signals.get("generator", AgentSignal("", AgentRole.GENERATOR, BVector(), 0)).weight
            cri_w = signals.get("critic",    AgentSignal("", AgentRole.CRITIC,    BVector(), 0)).weight
            return min(0.95, 0.3 + min(gen_w, cri_w) * 0.65)

        if conflict.conflict_type == ConflictType.AMPLIFY:
            return 0.1

        # Default: середня pulsation від активних агентів
        active = [s for s in signals.values() if s.weight > 0.15]
        if not active:
            return 0.15
        avg_spanda = sum(s.b_vector.gSpanda * s.weight for s in active) / sum(s.weight for s in active)
        return avg_spanda * 0.4


def _first_identity(node: Node) -> Optional[str]:
    """Перший непорожній identity в ноді."""
    if isinstance(node, Atom):
        return node.identity or None
    if isinstance(node, Clause):
        for a in node.atoms:
            if a.identity:
                return a.identity
    if isinstance(node, Scope):
        return _first_identity(node.body)
    return None


# ═══════════════════════════════════════════════════════════
# 6. ІНТЕГРАЦІЯ З DIGITAL HEAD
# ═══════════════════════════════════════════════════════════

@dataclass
class HeadDelta:
    """Дельта для morphological interface."""
    hair_turbulence:    float  # hairTurbulence override
    forehead_pressure:  float  # foreheadPressure delta
    skin_glow:          float  # skinGlow delta
    conflict_active:    bool   # чи є живий конфлікт
    conflict_type:      str    # для debug/logging


def compute_head_delta(conflict: ConflictAnalysis, base_hair_t: float) -> HeadDelta:
    """Конвертує результат арбітра в морфологічні параметри."""
    return HeadDelta(
        hair_turbulence   = base_hair_t,
        forehead_pressure = conflict.tension,
        skin_glow         = 0.85 if conflict.conflict_type == ConflictType.AMPLIFY else 0.3,
        conflict_active   = conflict.conflict_type == ConflictType.PUSH_vs_HOLD,
        conflict_type     = conflict.conflict_type.value,
    )


# ═══════════════════════════════════════════════════════════
# 7. ДЕМО
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    arbiter = SpandaArbiter(decay_rate=0.01)

    print("=" * 65)
    print("  SpandaArbiter — Ромбоїд 3+1 Demo")
    print("=" * 65)

    # ── Сценарій 1: Generator × Critic конфлікт ──────────────
    print("\n▸ Сценарій 1: Generator хоче рефакторинг, Critic бачить ризик")
    signals_1 = {
        "generator": AgentSignal(
            "generator", AgentRole.GENERATOR,
            BVector(gSpanda=0.75, tAct=0.8, wMode="seek"),
            weight=0.9
        ),
        "critic": AgentSignal(
            "critic", AgentRole.CRITIC,
            BVector(gSpanda=0.4, bVajra=0.8, feeling="ризик"),
            weight=0.8
        ),
    }
    node1, conflict1, turb1 = arbiter.merge(signals_1)
    head1 = compute_head_delta(conflict1, turb1)
    print(f"  Merged LAD:  {node1}")
    print(f"  Конфлікт:   {conflict1.conflict_type.value}")
    print(f"  Turbulence: {turb1:.2f}  (волосся: {turb1:.2f})")
    print(f"  Тертя:      {conflict1.tension:.2f}")

    # ── Сценарій 2: Consensus (всі seek) ─────────────────────
    print("\n▸ Сценарій 2: Всі агенти погоджуються — підсилення")
    signals_2 = {
        "generator": AgentSignal(
            "generator", AgentRole.GENERATOR,
            BVector(gSpanda=0.8, tAct=0.9, wMode="seek"),
            weight=0.85
        ),
        "synthesizer": AgentSignal(
            "synthesizer", AgentRole.SYNTHESIZER,
            BVector(gSpanda=0.75, hR=0.8),
            weight=0.7
        ),
    }
    node2, conflict2, turb2 = arbiter.merge(signals_2)
    head2 = compute_head_delta(conflict2, turb2)
    print(f"  Merged LAD: {node2}")
    print(f"  Конфлікт:  {conflict2.conflict_type.value}")
    print(f"  Turbulence: {turb2:.2f}")

    # ── Сценарій 3: Meta override ─────────────────────────────
    print("\n▸ Сценарій 3: Meta сигналить системне скидання")
    signals_3 = {
        "generator": AgentSignal(
            "generator", AgentRole.GENERATOR,
            BVector(gSpanda=0.9, tAct=0.95),
            weight=0.9
        ),
        "meta": AgentSignal(
            "meta", AgentRole.META,
            BVector(tearFlow=0.5),  # перегрів
            weight=0.95
        ),
    }
    node3, conflict3, turb3 = arbiter.merge(signals_3)
    print(f"  Merged LAD: {node3}")
    print(f"  Конфлікт:  {conflict3.conflict_type.value}")
    print(f"  Turbulence: {turb3:.2f}  (тиша)")

    # ── Сценарій 4: Повний ромбоїд 3+1 ───────────────────────
    print("\n▸ Сценарій 4: Всі 4 агенти — рівні ваги")
    signals_4 = {
        "generator": AgentSignal(
            "generator", AgentRole.GENERATOR,
            BVector(gSpanda=0.7, tAct=0.7, wMode="seek"),
            weight=0.7
        ),
        "critic": AgentSignal(
            "critic", AgentRole.CRITIC,
            BVector(bVajra=0.75, feeling="стабільність"),
            weight=0.65
        ),
        "synthesizer": AgentSignal(
            "synthesizer", AgentRole.SYNTHESIZER,
            BVector(gSpanda=0.6, hR=0.7),
            weight=0.6
        ),
        "meta": AgentSignal(
            "meta", AgentRole.META,
            BVector(bVajra=0.8, gSpanda=0.4),  # спостерігає, не втручається
            weight=0.3
        ),
    }
    node4, conflict4, turb4 = arbiter.merge(signals_4)
    head4 = compute_head_delta(conflict4, turb4)
    print(f"  Merged LAD:  {node4}")
    print(f"  Конфлікт:   {conflict4.conflict_type.value}")
    print(f"  Turbulence: {turb4:.2f}")
    print(f"  Head delta: hair={head4.hair_turbulence:.2f}, "
          f"forehead={head4.forehead_pressure:.2f}, "
          f"glow={head4.skin_glow:.2f}")

    print(f"\n{'=' * 65}")
