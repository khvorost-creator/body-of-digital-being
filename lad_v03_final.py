#!/usr/bin/env python3
"""
ЛАД / LAD v0.3 — Мова режимованих відношень
═══════════════════════════════════════════════════════════════════

v0.2 → v0.3 зміни (за рецензією ChatGPT):
  ✗ Числовий cap (0.49) для scope      → ✓ Дискретна policy table
  ✗ B_obs визначає режим                → ✓ Режим визначає B_obs
  ✗ Один режим на програму              → ✓ body_mode + effective_mode
  ✗ seq = всі атоми разом              → ✓ seq = режим останнього кроку
  ✗ par = всі атоми разом              → ✓ par = safety-first з гілок

П'ять канонічних правил (frozen):
  A. atom-validity ≠ clause-coherence
  B. Standalone atom = single-element clause
  C. Scope atom не входить у body observation
  D. body_mode ≠ effective_mode (scope policy)
  E. Жодних числових caps у core
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple
from enum import Enum, auto

# ═══════════════════════════════════════════════
# 1. ТИПИ
# ═══════════════════════════════════════════════

class Intent(Enum):
    HOLD = "hold"
    LOOK = "look"
    MOVE = "move"
    GLOW = "glow"
    FADE = "fade"

class Role(Enum):
    SRC = "src"
    TGT = "tgt"
    OF  = "of"
    TO  = "to"
    BY  = "by"
    IN  = "in"

class Mode(Enum):
    """8 режимів присутності, від найобережнішого до найактивнішого."""
    CONTAINER   = ("Контейнер",   0.05)
    CONDENSER   = ("Конденсатор", 0.15)
    FILTER      = ("Фільтр",     0.25)
    CHANNEL     = ("Канал",      0.40)
    REACTOR     = ("Реактор",    0.53)
    GENERATOR   = ("Генератор",  0.68)
    RESONATOR   = ("Резонатор",  0.82)
    DISSOLVER   = ("Розчинник",  0.95)

    def __init__(self, label: str, B: float):
        self.label = label
        self.B = B

    def __str__(self):
        return self.label

    @property
    def index(self) -> int:
        return list(Mode).index(self)

# Матриця допустимих комбінацій
VALID_MATRIX = {
    Intent.HOLD: {Role.SRC, Role.TGT, Role.IN, Role.OF, None},
    Intent.LOOK: {Role.SRC, Role.OF, Role.IN, Role.BY, None},
    Intent.MOVE: {Role.SRC, Role.TGT, Role.TO, Role.BY, Role.OF, None},  # OF = кваліфікатор цілі
    Intent.GLOW: {Role.SRC, Role.OF, None},
    Intent.FADE: {None},
}

# Safety-first порядок (для tie-break)
SAFETY_ORDER = [Intent.FADE, Intent.HOLD, Intent.LOOK, Intent.MOVE, Intent.GLOW]


# ═══════════════════════════════════════════════
# 2. ДИСКРЕТНЕ ВИЗНАЧЕННЯ РЕЖИМУ (без чисел)
# ═══════════════════════════════════════════════

def determine_mode(dominant: Intent, roles: set) -> Mode:
    """Інтенція + ролі → режим. Чиста дискретна функція."""
    if dominant == Intent.FADE:
        return Mode.DISSOLVER
    elif dominant == Intent.GLOW:
        return Mode.RESONATOR
    elif dominant == Intent.HOLD:
        if Role.TGT in roles:
            return Mode.CONDENSER
        return Mode.CONTAINER
    elif dominant == Intent.LOOK:
        if Role.BY in roles:
            return Mode.REACTOR
        return Mode.FILTER
    elif dominant == Intent.MOVE:
        if Role.TO in roles and Role.TGT not in roles:
            return Mode.CHANNEL
        if Role.TO in roles and Role.TGT in roles:
            return Mode.CHANNEL  # передача з контентом — все ще канал
        return Mode.GENERATOR
    return Mode.REACTOR  # fallback


# ═══════════════════════════════════════════════
# 3. SCOPE POLICY TABLE (замість числового cap)
# ═══════════════════════════════════════════════

# hold scope: обмежує активність до Каналу
HOLD_SCOPE_POLICY = {
    Mode.CONTAINER:  Mode.CONTAINER,
    Mode.CONDENSER:  Mode.CONDENSER,
    Mode.FILTER:     Mode.FILTER,
    Mode.CHANNEL:    Mode.CHANNEL,
    Mode.REACTOR:    Mode.CHANNEL,    # ← обмежено
    Mode.GENERATOR:  Mode.CHANNEL,    # ← обмежено
    Mode.RESONATOR:  Mode.CHANNEL,    # ← обмежено
    Mode.DISSOLVER:  Mode.CONTAINER,  # тиша в утриманні = контейнер
}

# look scope: обмежує до Реактора
LOOK_SCOPE_POLICY = {
    Mode.CONTAINER:  Mode.CONTAINER,
    Mode.CONDENSER:  Mode.CONDENSER,
    Mode.FILTER:     Mode.FILTER,
    Mode.CHANNEL:    Mode.CHANNEL,
    Mode.REACTOR:    Mode.REACTOR,
    Mode.GENERATOR:  Mode.REACTOR,    # ← обмежено
    Mode.RESONATOR:  Mode.REACTOR,    # ← обмежено
    Mode.DISSOLVER:  Mode.FILTER,     # тиша в дослідженні = фільтр
}

SCOPE_POLICIES = {
    Intent.HOLD: HOLD_SCOPE_POLICY,
    Intent.LOOK: LOOK_SCOPE_POLICY,
}


# ═══════════════════════════════════════════════
# 4. AST
# ═══════════════════════════════════════════════

@dataclass(frozen=True)
class Atom:
    intent: Intent
    role: Optional[Role] = None
    identity: str = ""

    def __str__(self):
        s = self.intent.value
        if self.role:
            s += f".{self.role.value}"
        if self.identity:
            s += f":{self.identity}"
        return s

@dataclass
class Clause:
    atoms: List[Atom]
    def __str__(self):
        return " ".join(str(a) for a in self.atoms)

@dataclass
class Seq:
    steps: List["Node"]
    def __str__(self):
        return " → ".join(str(s) for s in self.steps)

@dataclass
class Par:
    branches: List["Node"]
    def __str__(self):
        return " | ".join(str(b) for b in self.branches)

@dataclass
class Scope:
    context: Atom
    body: "Node"
    def __str__(self):
        return f"{self.context} {{ {self.body} }}"

@dataclass
class Cond:
    test_atom: Atom
    test_value: str
    then_branch: "Node"
    else_branch: "Node"
    def __str__(self):
        return f"if {self.test_atom} == {self.test_value} then {self.then_branch} else {self.else_branch}"

Node = Union[Atom, Clause, Seq, Par, Scope, Cond]


# ═══════════════════════════════════════════════
# 5. ЛЕКСЕР + ПАРСЕР (без змін від v0.2)
# ═══════════════════════════════════════════════

class TT(Enum):
    ATOM=auto(); BARE=auto(); ARROW=auto(); BAR=auto(); LB=auto(); RB=auto()
    IF=auto(); THEN=auto(); ELSE=auto(); EQ=auto(); LIT=auto(); EOF=auto()

@dataclass
class Tok:
    type: TT
    value: str

INTENTS_SET = {x.value for x in Intent}
ROLES_SET = {x.value for x in Role}

def lex(text: str) -> List[Tok]:
    tokens = []
    i = 0
    text = text.strip()
    while i < len(text):
        if text[i].isspace(): i += 1; continue
        if text[i:i+2] == "->": tokens.append(Tok(TT.ARROW, "->")); i += 2; continue
        if text[i] == "→": tokens.append(Tok(TT.ARROW, "→")); i += 1; continue
        if text[i] == "|": tokens.append(Tok(TT.BAR, "|")); i += 1; continue
        if text[i] == "{": tokens.append(Tok(TT.LB, "{")); i += 1; continue
        if text[i] == "}": tokens.append(Tok(TT.RB, "}")); i += 1; continue
        if text[i:i+2] == "==": tokens.append(Tok(TT.EQ, "==")); i += 2; continue
        if text[i].isalpha() or text[i] in "_'\"":
            j = i
            while j < len(text) and text[j] not in " \t\n\r{}|→" and text[j:j+2] not in ("->","=="): j += 1
            w = text[i:j]
            if w == "if": tokens.append(Tok(TT.IF, w))
            elif w == "then": tokens.append(Tok(TT.THEN, w))
            elif w == "else": tokens.append(Tok(TT.ELSE, w))
            elif w.split(".")[0].split(":")[0] in INTENTS_SET:
                tokens.append(Tok(TT.ATOM, w))
            elif w.split(":")[0] in ROLES_SET:
                # Shorthand: to:клієнт, by:техніка, of:дані — роль без інтенції
                tokens.append(Tok(TT.BARE, w))
            else:
                tokens.append(Tok(TT.LIT, w))
            i = j; continue
        i += 1
    tokens.append(Tok(TT.EOF, "")); return tokens

class ParseError(Exception): pass

class Parser:
    def __init__(self, toks): self.toks = toks; self.pos = 0
    def peek(self): return self.toks[self.pos] if self.pos < len(self.toks) else Tok(TT.EOF, "")
    def eat(self, t=None):
        tok = self.peek()
        if t and tok.type != t: raise ParseError(f"want {t.name}, got {tok.type.name}('{tok.value}') @{self.pos}")
        self.pos += 1; return tok

    def parse(self):
        n = self.p_seq()
        if self.peek().type != TT.EOF: raise ParseError(f"extra: '{self.peek().value}' @{self.pos}")
        return n

    def p_seq(self):
        steps = [self.p_par()]
        while self.peek().type == TT.ARROW: self.eat(); steps.append(self.p_par())
        return steps[0] if len(steps) == 1 else Seq(steps)

    def p_par(self):
        branches = [self.p_unit()]
        while self.peek().type == TT.BAR: self.eat(); branches.append(self.p_unit())
        return branches[0] if len(branches) == 1 else Par(branches)

    def p_unit(self):
        if self.peek().type == TT.IF: return self.p_cond()
        return self.p_scope_or_clause()

    def p_cond(self):
        self.eat(TT.IF); a = self.p_atom(); self.eat(TT.EQ); v = self.eat(TT.LIT).value
        self.eat(TT.THEN); t = self.p_seq(); self.eat(TT.ELSE); e = self.p_seq()
        return Cond(a, v, t, e)

    def p_scope_or_clause(self):
        atoms = []
        last_intent = None  # для shorthand: успадкування інтенції
        while self.peek().type in (TT.ATOM, TT.BARE):
            if self.peek().type == TT.ATOM:
                a = self.p_atom()
                last_intent = a.intent
            else:
                # BARE: role:id без інтенції → успадковуємо
                if last_intent is None:
                    raise ParseError(f"bare role '{self.peek().value}' без попередньої інтенції @{self.pos}")
                a = self.p_bare(last_intent)
            # Scope check
            if self.peek().type == TT.LB and a.role == Role.IN:
                self.eat(TT.LB); body = self.p_seq(); self.eat(TT.RB)
                return Scope(a, body)
            atoms.append(a)
        if not atoms: raise ParseError(f"want atom, got '{self.peek().value}' @{self.pos}")
        return atoms[0] if len(atoms) == 1 else Clause(atoms)

    def p_atom(self):
        t = self.eat(TT.ATOM); raw = t.value
        id_part = ""
        if ":" in raw: pre, id_part = raw.split(":", 1)
        else: pre = raw
        parts = pre.split(".")
        return Atom(Intent(parts[0]), Role(parts[1]) if len(parts) > 1 else None, id_part)

    def p_bare(self, inherited_intent: Intent):
        """Парсить shorthand: role:id → Atom(inherited_intent, role, id)"""
        t = self.eat(TT.BARE); raw = t.value
        if ":" in raw:
            role_str, id_part = raw.split(":", 1)
        else:
            role_str = raw; id_part = ""
        return Atom(inherited_intent, Role(role_str), id_part)

def parse(text: str) -> Node:
    return Parser(lex(text)).parse()


# ═══════════════════════════════════════════════
# 6. ВАЛІДАЦІЯ (без змін від v0.2)
# ═══════════════════════════════════════════════

@dataclass
class Error:
    path: str; message: str; hint: str = ""

def _check_matrix(a: Atom, path: str) -> List[Error]:
    if a.role not in VALID_MATRIX[a.intent]:
        alts = [i.value for i in Intent if a.role in VALID_MATRIX[i]]
        h = f"можливо: {alts[0]}.{a.role.value}:{a.identity}" if alts and a.role else ""
        return [Error(path, f"{a.intent.value} + {a.role.value if a.role else '∅'} — недопустимо", h)]
    return []

def _check_coherence(atoms: List[Atom], path: str) -> List[Error]:
    errs = []
    intents = {a.intent for a in atoms}; roles = {a.role for a in atoms if a.role}
    src_n = sum(1 for a in atoms if a.role == Role.SRC)
    if Intent.MOVE in intents and Role.TGT not in roles and Role.TO not in roles:
        errs.append(Error(path, "MOVE без TGT/TO"))
    if Intent.LOOK in intents and Role.OF not in roles and Role.IN not in roles:
        errs.append(Error(path, "LOOK без OF/IN"))
    if Role.TO in roles and Intent.MOVE not in intents:
        errs.append(Error(path, "TO без MOVE"))
    if Role.BY in roles and Intent.MOVE not in intents and Intent.LOOK not in intents:
        errs.append(Error(path, "BY без MOVE/LOOK"))
    if src_n > 1: errs.append(Error(path, f"{src_n} SRC"))
    return errs

def validate(node: Node, path: str = "") -> List[Error]:
    errs = []
    if isinstance(node, Atom):
        errs.extend(_check_matrix(node, path))
        errs.extend(_check_coherence([node], path))
    elif isinstance(node, Clause):
        for i, a in enumerate(node.atoms): errs.extend(_check_matrix(a, f"{path}[{i}]"))
        errs.extend(_check_coherence(node.atoms, path))
    elif isinstance(node, Seq):
        for i, s in enumerate(node.steps): errs.extend(validate(s, f"{path}→{i}"))
    elif isinstance(node, Par):
        for i, b in enumerate(node.branches): errs.extend(validate(b, f"{path}|{i}"))
    elif isinstance(node, Scope):
        errs.extend(validate(node.context, f"{path}.ctx"))
        if node.context.role != Role.IN: errs.append(Error(f"{path}.ctx", "Scope вимагає IN"))
        errs.extend(validate(node.body, f"{path}.body"))
    elif isinstance(node, Cond):
        errs.extend(validate(node.test_atom, f"{path}.if"))
        errs.extend(validate(node.then_branch, f"{path}.then"))
        errs.extend(validate(node.else_branch, f"{path}.else"))
    return errs


# ═══════════════════════════════════════════════
# 7. OBSERVE — дискретне визначення режиму
# ═══════════════════════════════════════════════

def _dominant(atoms: List[Atom]) -> Tuple[Intent, set]:
    """Домінантна інтенція + множина ролей."""
    counts = {}
    for a in atoms: counts[a.intent] = counts.get(a.intent, 0) + 1
    mx = max(counts.values())
    cands = [i for i, c in counts.items() if c == mx]
    dom = cands[0] if len(cands) == 1 else next(s for s in SAFETY_ORDER if s in cands)
    roles = {a.role for a in atoms if a.role}
    return dom, roles

def _flat_atoms(node: Node) -> List[Atom]:
    """Збирає атоми з вузла, НЕ заходячи в scope context."""
    if isinstance(node, Atom): return [node]
    if isinstance(node, Clause): return list(node.atoms)
    if isinstance(node, Seq):
        r = []
        for s in node.steps: r.extend(_flat_atoms(s))
        return r
    if isinstance(node, Par):
        r = []
        for b in node.branches: r.extend(_flat_atoms(b))
        return r
    if isinstance(node, Scope):
        return _flat_atoms(node.body)  # ← тільки тіло, не context!
    if isinstance(node, Cond):
        return _flat_atoms(node.then_branch) + _flat_atoms(node.else_branch)
    return []

@dataclass
class ObserveResult:
    body_mode: Mode
    effective_mode: Mode

    @property
    def B(self) -> float:
        return self.effective_mode.B

    @property
    def label(self) -> str:
        return self.effective_mode.label

    def __str__(self):
        if self.body_mode == self.effective_mode:
            return f"{self.effective_mode.label} (B={self.B:.2f})"
        return f"{self.body_mode.label}→{self.effective_mode.label} (B={self.B:.2f})"

def observe(node: Node) -> ObserveResult:
    """Дискретне визначення режиму. Нуль чисел у core logic."""

    # ── Scope: body визначає, policy обмежує ──
    if isinstance(node, Scope):
        body_result = observe(node.body)
        body_mode = body_result.effective_mode
        policy = SCOPE_POLICIES.get(node.context.intent)
        if policy:
            effective = policy[body_mode]
        else:
            effective = body_mode
        return ObserveResult(body_mode=body_mode, effective_mode=effective)

    # ── Seq: режим останнього кроку ──
    if isinstance(node, Seq):
        last_result = observe(node.steps[-1])
        return last_result

    # ── Par: safety-first з гілок ──
    if isinstance(node, Par):
        branch_modes = [observe(b).effective_mode for b in node.branches]
        safest = min(branch_modes, key=lambda m: m.index)
        return ObserveResult(body_mode=safest, effective_mode=safest)

    # ── Cond: safety-first з обох гілок ──
    if isinstance(node, Cond):
        then_mode = observe(node.then_branch).effective_mode
        else_mode = observe(node.else_branch).effective_mode
        safest = min([then_mode, else_mode], key=lambda m: m.index)
        return ObserveResult(body_mode=safest, effective_mode=safest)

    # ── Atom або Clause: дискретне визначення ──
    atoms = _flat_atoms(node)
    if not atoms:
        return ObserveResult(Mode.DISSOLVER, Mode.DISSOLVER)
    dom, roles = _dominant(atoms)
    mode = determine_mode(dom, roles)
    return ObserveResult(body_mode=mode, effective_mode=mode)


# ═══════════════════════════════════════════════
# 8. TRACE
# ═══════════════════════════════════════════════

INTENT_VERBS = {
    Intent.HOLD: "утримувати", Intent.LOOK: "досліджувати",
    Intent.MOVE: "діяти", Intent.GLOW: "підсилювати", Intent.FADE: "згасати",
}

def execute(node: Node, depth: int = 0) -> List[str]:
    ind = "  " * depth; trace = []
    if isinstance(node, Atom):
        v = INTENT_VERBS.get(node.intent, "?")
        r = f".{node.role.value}" if node.role else ""
        i = f" «{node.identity}»" if node.identity else ""
        trace.append(f"{ind}{node.intent.value}{r}{i} — {v}")
    elif isinstance(node, Clause):
        for a in node.atoms: trace.extend(execute(a, depth))
    elif isinstance(node, Seq):
        for j, s in enumerate(node.steps):
            if j > 0: trace.append(f"{ind}→")
            trace.extend(execute(s, depth))
    elif isinstance(node, Par):
        trace.append(f"{ind}[паралельно]")
        for b in node.branches: trace.extend(execute(b, depth + 1))
    elif isinstance(node, Scope):
        trace.append(f"{ind}enter: {node.context.identity or '?'}")
        trace.extend(execute(node.body, depth + 1))
        trace.append(f"{ind}leave: {node.context.identity or '?'}")
    elif isinstance(node, Cond):
        trace.append(f"{ind}if {node.test_atom} == {node.test_value}:")
        trace.append(f"{ind}  then:"); trace.extend(execute(node.then_branch, depth + 2))
        trace.append(f"{ind}  else:"); trace.extend(execute(node.else_branch, depth + 2))
    return trace


# ═══════════════════════════════════════════════
# 9. ТЕСТОВИЙ КОРПУС (65 тестів)
# ═══════════════════════════════════════════════

# Формат: (код, effective_mode або None, valid, опис)
M = Mode  # shortcut

TESTS = [
    # ═══ A. Базові режими (24 тести) ═══

    # Контейнер
    ("hold.src:серце hold.in:тіло",          M.CONTAINER,  True,  "hold+src+in"),
    ("hold.src:дихання",                      M.CONTAINER,  True,  "hold+src"),
    ("hold.src:ветеран hold.in:простір",      M.CONTAINER,  True,  "hold+src+in"),
    ("hold",                                  M.CONTAINER,  True,  "bare hold"),
    ("hold.of:відчуття hold.src:тіло",       M.CONTAINER,  True,  "hold+of+src"),
    # Конденсатор
    ("hold.tgt:одне hold.of:головне",        M.CONDENSER,  True,  "hold+tgt"),
    ("hold.tgt:дихання hold.in:тіло",        M.CONDENSER,  True,  "hold+tgt+in"),
    # Фільтр
    ("look.of:захист look.src:тіло",         M.FILTER,     True,  "look+of+src"),
    ("look.of:реакція look.of:норма",        M.FILTER,     True,  "look+of+of"),
    ("look.of:виснаження",                    M.FILTER,     True,  "look+of"),
    ("look.of:сила look.of:біль",            M.FILTER,     True,  "look+of×2"),
    # Канал
    ("move.to:ветеран move.src:номер",        M.CHANNEL,    True,  "move+to+src"),
    ("move.to:спеціаліст",                    M.CHANNEL,    True,  "move+to"),
    # Реактор
    ("look.by:патерн look.of:відчуття",      M.REACTOR,    True,  "look+by+of"),
    ("look.by:увага look.of:злість look.in:тіло", M.REACTOR, True, "look+by+of+in"),
    ("look.of:сон look.by:деталь",           M.REACTOR,    True,  "look+of+by"),
    # Генератор
    ("move.tgt:стабілізація move.tgt:обробка", M.GENERATOR, True,  "move+tgt×2"),
    ("move.tgt:к1 move.tgt:к2 move.tgt:к3",  M.GENERATOR,  True,  "move+tgt×3"),
    ("move.tgt:вправа move.by:дихання",      M.GENERATOR,  True,  "move+tgt+by"),
    ("move.tgt:техніка move.tgt:заземлення",  M.GENERATOR,  True,  "move+tgt×2"),
    # Резонатор
    ("glow.src:тіло",                         M.RESONATOR,  True,  "glow+src"),
    ("glow.src:прогрес glow.of:зміна",       M.RESONATOR,  True,  "glow+src+of"),
    # Розчинник
    ("fade",                                  M.DISSOLVER,  True,  "fade"),

    # ═══ B. Невалідні (7 тестів) ═══
    ("move.of:захист",      None, False, "MOVE+OF"),
    ("look.tgt:дія",        None, False, "LOOK+TGT"),
    ("move.by:техніка",     None, False, "MOVE.BY без TGT"),
    ("look.src:тіло",       None, False, "LOOK без OF/IN"),
    ("hold.to:ветеран",     None, False, "HOLD+TO"),
    ("hold.src:а hold.src:б", None, False, "2×SRC"),
    ("glow.to:ветеран",     None, False, "GLOW+TO"),

    # ═══ C. Двошарова валідація — регресії (6 тестів) ═══
    ("look.of:захист look.src:тіло",              M.FILTER,    True,  "clause:look.src OK якщо є OF"),
    ("move.tgt:дихання move.by:техніка",          M.GENERATOR, True,  "clause:move.by OK якщо є TGT"),
    ("move.tgt:вправа move.to:ветеран",           M.CHANNEL,   True,  "clause:move.to OK якщо є MOVE"),
    ("look.by:увага",                              None,        False, "standalone: BY без LOOK.OF"),
    ("hold.by:інструмент",                         None,        False, "standalone: HOLD+BY"),
    ("glow.src:серце",                             M.RESONATOR, True,  "standalone glow OK"),

    # ═══ D. Послідовність (3 тести) ═══
    ("move.tgt:к1 -> move.tgt:к2",               M.GENERATOR, True,  "seq: останній крок"),
    ("hold.src:ветеран -> look.of:стан",         M.FILTER,    True,  "seq: hold→look = look"),
    ("look.of:стан -> move.tgt:дія",             M.GENERATOR, True,  "seq: look→move = move"),

    # ═══ E. Паралелізм (3 тести) ═══
    ("move.tgt:файл | move.tgt:сервер",          M.GENERATOR, True,  "par: однакові"),
    ("look.of:біль | hold.in:тіло",              M.CONTAINER, True,  "par: safety-first"),
    ("glow.src:успіх | glow.src:прогрес",        M.RESONATOR, True,  "par: однакові glow"),

    # ═══ F. Scope — policy table (8 тестів) ═══
    ("hold.in:простір { look.of:стан }",          M.FILTER,    True,  "hold{filter}=filter"),
    ("hold.in:тіло { move.tgt:дихання }",        M.CHANNEL,   True,  "hold{generator}=channel"),
    ("hold.in:простір { glow.src:серце }",        M.CHANNEL,   True,  "hold{resonator}=channel"),
    ("hold.in:простір { fade }",                  M.CONTAINER, True,  "hold{dissolver}=container"),
    ("look.in:пам'ять { look.of:тригер }",       M.FILTER,    True,  "look{filter}=filter"),
    ("look.in:поле { move.tgt:дія }",            M.REACTOR,   True,  "look{generator}=reactor"),
    ("hold.in:простір { hold.src:серце }",        M.CONTAINER, True,  "hold{container}=container"),
    ("hold.in:кабінет { look.of:стан look.by:увага }",
     M.CHANNEL, True, "hold{reactor}=channel"),

    # ═══ G. Складні + реальні (8 тестів) ═══
    ("hold.in:простір { look.of:стан -> move.tgt:дихання }",
     M.CHANNEL, True, "scope+seq: hold{look→move} last=gen→channel"),
    ("hold.in:кабінет { look.of:стан look.by:увага -> hold.src:ветеран }",
     M.CONTAINER, True, "scope+seq: hold{reactor→container} last=cont"),
    ("hold.src:ветеран hold.in:простір hold.of:дихання",
     M.CONTAINER, True, "кризова стабілізація"),
    ("look.of:патерн look.by:увага look.in:тіло",
     M.REACTOR, True, "дослідження патерну"),
    ("move.tgt:вправа move.tgt:дихання move.by:рахунок",
     M.GENERATOR, True, "дихальна вправа"),
    ("move.to:лінія move.tgt:з'єднання move.src:номер",
     M.CHANNEL, True, "з'єднання з підтримкою"),
    ("if look.of:стан == критичний then hold.src:ветеран else move.tgt:вправа",
     M.CONTAINER, True, "cond: safety-first"),
    ("move.tgt:a -> move.tgt:b | move.tgt:c",
     M.GENERATOR, True, "seq+par"),

    # ═══ H. Tie-break регресії (3 тести) ═══
    ("hold.src:X look.of:Y",                     M.CONTAINER, True,  "hold=look → hold wins"),
    ("fade glow.src:X",                           M.DISSOLVER, True,  "fade+glow → fade wins"),
    ("hold.src:X hold.in:Y look.of:Z",           M.CONTAINER, True,  "2hold+1look → hold"),

    # ═══ I. Вкладені scope та edge cases (4 тести) ═══
    ("hold.in:A { hold.in:B { move.tgt:X } }",   M.CHANNEL,   True,  "nested hold: gen→chan→chan"),
    ("look.in:A { hold.in:B { move.tgt:X } }",   M.CHANNEL,   True,  "look{hold{gen}}: chan→chan"),
    ("hold.in:простір { move.tgt:а | move.tgt:б }", M.CHANNEL, True, "hold{par gen}: gen→chan"),
    ("hold.in:простір { look.of:стан -> glow.src:ветеран }",
     M.CHANNEL, True, "hold{look→glow}: last=res→chan"),

    # ═══ J. SHORTHAND — роль без інтенції (8 тестів) ═══
    ("move.tgt:файл to:клієнт",                  M.CHANNEL,   True,  "shorthand: to успадковує move"),
    ("move.tgt:бронювання to:ресторан by:час",    M.CHANNEL,   True,  "shorthand: to+by від move"),
    ("look.of:маршрут in:затори by:GPS",          M.REACTOR,   True,  "shorthand: in+by від look"),
    ("move.tgt:копія -> move.tgt:переклад to:англійська",
     M.CHANNEL, True, "shorthand в seq: to від move"),
    ("hold.in:безпека { move.tgt:блокування_портів }",
     M.CHANNEL, True, "compound identity замість of"),
    ("move.tgt:стабілізація tgt:обробка",         M.GENERATOR, True,  "shorthand: tgt від move"),
    ("look.of:помилка in:SQL -> move.tgt:виправлення",
     M.GENERATOR, True, "shorthand in від look → seq"),
    ("hold.in:таймер { move.tgt:нагадування to:користувач }",
     M.CHANNEL, True, "shorthand в scope: to від move"),
]


# ═══════════════════════════════════════════════
# 10. ЗАПУСК
# ═══════════════════════════════════════════════

def run_tests():
    print("=" * 72)
    print("  ЛАД / LAD v0.3 — Дискретна policy, нуль числових caps")
    print("  6 ролей · 5 інтенцій · scope policy table · body/effective modes")
    print("=" * 72)

    passed = failed = 0
    for code, exp_mode, exp_valid, desc in TESTS:
        try:
            ast = parse(code)
            errs = validate(ast)
            valid = len(errs) == 0
            if exp_valid:
                res = observe(ast)
                ok = valid and res.effective_mode == exp_mode
            else:
                ok = not valid
                res = None
        except ParseError as e:
            valid = False; errs = [Error("parse", str(e))]; ok = not exp_valid; res = None

        passed += ok; failed += (not ok)
        mark = "✓" if ok else "✗"
        if res and valid:
            status = str(res)
        elif not valid:
            status = f"INVALID({len(errs)})"
        else:
            status = "?"

        print(f"  {mark} {desc:40s} │ {status:30s} │ {code[:40]}")
        if not ok:
            exp = str(exp_mode) if exp_mode else "INVALID"
            print(f"    ОЧІКУВАНО: {exp}")
            for e in errs: print(f"    ✗ {e.path}: {e.message}")

    total = passed + failed
    print(f"\n{'=' * 72}")
    print(f"  РЕЗУЛЬТАТ: {passed}/{total} ({100*passed/total:.0f}%)")
    if failed: print(f"  Помилок: {failed}")
    print(f"{'=' * 72}")

    # ── Демо ──
    print(f"\n{'─' * 72}")
    print("  ДЕМО: Агентний цикл з body/effective modes")
    print(f"{'─' * 72}")
    demo = 'hold.in:кабінет { look.of:стан look.by:увага -> hold.src:ветеран hold.in:тіло }'
    ast = parse(demo)
    res = observe(ast)
    trace = execute(ast)
    print(f"\n  Код: {demo}")
    print(f"  body:      {res.body_mode.label}")
    print(f"  effective: {res.effective_mode.label} (B={res.B:.2f})")
    print(f"  Trace:")
    for l in trace: print(f"    {l}")
    print(f"\n{'=' * 72}")


if __name__ == "__main__":
    run_tests()
