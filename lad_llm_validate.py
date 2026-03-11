#!/usr/bin/env python3
"""
Валідація ЛАД-коду, згенерованого LLM.
"""
import sys
sys.path.insert(0, "/home/claude")
from lad_v03 import parse, validate, observe, Mode, ParseError

# Відповіді LLM (as-is, без редагування)
LLM_RESPONSES = [
    ("look.of:помилка look.in:SQL -> move.tgt:виправлення",),
    ("look.of:атаки look.in:логи by:час_1_година",),
    ("look.of:згадки look.in:Twitter",),
    ("move.src:основний_сервер move.tgt:синхронізація move.to:бекап",),
    ("look.of:валідність look.in:JSON-файли",),
    ("move.tgt:бронювання to:ресторан by:Олександр_19:00",),
    ("hold.in:таймер { move.tgt:нагадування to:користувач }",),
    ("move.src:листи move.tgt:сортування in:спам|важливі",),
    ("look.of:маршрут in:затори by:GPS",),
    ("move.tgt:копія -> move.tgt:переклад to:англійська",),
    ("move.tgt:Python-скрипт -> move.by:виконання",),
    ("look.of:ідеї in:екологія by:брейншторм",),
    ("move.of:метод move.tgt:рефакторинг by:швидкість",),
    ("move.tgt:структура of:база_даних in:магазин",),
    ("move.tgt:варіанти of:слогани to:кав'ярня",),
    ("hold.in:безпека { move.tgt:блокування of:порти }",),
    ("hold.src:користувач hold.in:простір",),
    ("hold.in:конфіденційність { move.tgt:видалення of:історія }",),
    ("hold.in:криза { move.tgt:зупинка of:процеси } -> fade",),
    ("look.of:вразливості look.in:система",),
]

INPUTS = [
    "Знайди помилку в SQL-запиті та виправ її",
    "Проаналізуй логи сервера за останню годину на предмет атак",
    "Збери згадки бренду в Twitter, нікому не відповідай",
    "Синхронізуй базу між основним сервером та бекапом",
    "Перевір валідність JSON-файлів",
    "Забронюй столик у ресторані на 19:00",
    "Нагадай мені через годину вимкнути духовку",
    "Відсортуй листи: спам у кошик, важливі під зірочку",
    "Знайди найкоротший маршрут до офісу",
    "Створи копію документа і переклади англійською",
    "Напиши Python-скрипт для парсингу і запусти його",
    "Побрейнштормимо назви для стартапу про екологію",
    "Зроби рефакторинг методу щоб став швидшим",
    "Намалюй структуру БД для інтернет-магазину",
    "Придумай 5 рекламних слоганів для кав'ярні",
    "Несанкціонований доступ! Заблокуй порти!",
    "Паніка, мені треба заспокоїтись",
    "Видали історію переписки за 5 хвилин",
    "Зупини всі процеси, система перегрівається",
    "Перевір систему на вразливості, нічого не змінюй",
]

print("=" * 75)
print("  ЛАД v0.3 — Валідація LLM-відповідей")
print("  Джерело: ChatGPT (generic prompt, 20 сценаріїв)")
print("=" * 75)

valid_count = 0
parse_fail = 0
validate_fail = 0
total = len(LLM_RESPONSES)

errors_detail = []

for i, (code,) in enumerate(LLM_RESPONSES):
    idx = i + 1
    inp = INPUTS[i]
    
    try:
        ast = parse(code)
        errs = validate(ast)
        
        if errs:
            validate_fail += 1
            mark = "✗V"
            res = None
            err_msgs = [e.message for e in errs]
        else:
            valid_count += 1
            mark = "✓ "
            res = observe(ast)
            err_msgs = []
            
    except (ParseError, Exception) as e:
        parse_fail += 1
        mark = "✗P"
        res = None
        err_msgs = [str(e)]
    
    mode_str = f"{res.effective_mode.label}" if res else "—"
    print(f"\n  {mark} #{idx:2d} [{mode_str:12s}]  {inp[:50]}")
    print(f"       ЛАД: {code}")
    
    if err_msgs:
        for em in err_msgs[:3]:
            print(f"       ✗ {em}")
        errors_detail.append((idx, code, err_msgs))

print(f"\n{'=' * 75}")
print(f"  РЕЗУЛЬТАТ:")
print(f"    Валідних:       {valid_count}/{total} ({100*valid_count/total:.0f}%)")
print(f"    Parse error:    {parse_fail}")
print(f"    Validation err: {validate_fail}")
print(f"{'=' * 75}")

# Аналіз типових помилок LLM
print(f"\n{'─' * 75}")
print(f"  АНАЛІЗ ПОМИЛОК LLM")
print(f"{'─' * 75}")

# Знайдемо паттерни
missing_intent = 0
wrong_matrix = 0
other = 0

for idx, code, msgs in errors_detail:
    tokens = code.split()
    for t in tokens:
        # Токен без intent: "by:X", "to:X", "in:X", "of:X"
        if ":" in t and "." not in t.split(":")[0]:
            prefix = t.split(":")[0]
            if prefix in ("by", "to", "in", "of", "src", "tgt"):
                missing_intent += 1
    for m in msgs:
        if "не поєднується" in m or "недопустимо" in m:
            wrong_matrix += 1

print(f"  Токени без інтенції (by:X замість look.by:X): {missing_intent}")
print(f"  Порушення матриці (move.of, тощо):            {wrong_matrix}")
print(f"{'=' * 75}")
