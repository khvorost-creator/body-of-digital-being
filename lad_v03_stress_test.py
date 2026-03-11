#!/usr/bin/env python3
"""
ЛАД v0.3 — Стрес-тест: 20 універсальних сценаріїв
Перевірка: чи може LLM генерувати валідний ЛАД для довільних доменів?
"""

import sys
sys.path.insert(0, "/home/claude")
from lad_v03 import parse, validate, observe, execute, Mode

# ═══════════════════════════════════════════════
# 20 СЦЕНАРІЇВ: запит → ЛАД-код → очікуваний режим
# ═══════════════════════════════════════════════

SCENARIOS = [
    # ── Блок А: Дані та Аналітика ──
    {
        "id": 1,
        "input": "Знайди помилку в SQL-запиті та виправ її",
        "lad": "look.of:помилка look.in:запит -> move.tgt:виправлення",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "look→move: спочатку аналіз, потім дія. Seq = останній крок = Generator",
    },
    {
        "id": 2,
        "input": "Проаналізуй логи сервера за останню годину на предмет атак",
        "lad": "look.of:атаки look.in:логи",
        "expected_mode": Mode.FILTER,
        "expected_valid": True,
        "rationale": "Чистий look без by = Filter (спостереження без інструменту)",
    },
    {
        "id": 3,
        "input": "Збери всі згадки бренду, але нікому не відповідай",
        "lad": "hold.in:моніторинг { look.of:згадки look.in:twitter }",
        "expected_mode": Mode.FILTER,
        "expected_valid": True,
        "rationale": "hold scope обмежує: look=Filter, hold{Filter}=Filter",
    },
    {
        "id": 4,
        "input": "Синхронізуй базу між основним сервером та бекапом",
        "lad": "move.tgt:синхронізація move.to:бекап move.src:основний",
        "expected_mode": Mode.CHANNEL,
        "expected_valid": True,
        "rationale": "move+to+tgt = Channel (передача з контентом)",
    },
    {
        "id": 5,
        "input": "Перевір валідність JSON-файлів",
        "lad": "look.of:валідність look.in:файли",
        "expected_mode": Mode.FILTER,
        "expected_valid": True,
        "rationale": "look+of+in = Filter",
    },

    # ── Блок Б: Робота та Рутина ──
    {
        "id": 6,
        "input": "Забронюй столик у ресторані на 19:00",
        "lad": "move.tgt:бронювання move.to:ресторан",
        "expected_mode": Mode.CHANNEL,
        "expected_valid": True,
        "rationale": "move+tgt+to = Channel",
    },
    {
        "id": 7,
        "input": "Нагадай мені через годину вимкнути духовку",
        "lad": "hold.in:таймер { move.tgt:нагадування move.to:користувач }",
        "expected_mode": Mode.CHANNEL,
        "expected_valid": True,
        "rationale": "hold{move+to+tgt=Channel} → policy: Channel→Channel",
    },
    {
        "id": 8,
        "input": "Відсортуй вхідні листи: спам у кошик, важливі під зірочку",
        "lad": "look.of:тип look.in:листи -> move.tgt:сортування",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "seq: look→move, останній крок = Generator",
    },
    {
        "id": 9,
        "input": "Знайди найкоротший маршрут до офісу",
        "lad": "look.of:маршрут look.by:оптимізація",
        "expected_mode": Mode.REACTOR,
        "expected_valid": True,
        "rationale": "look+by = Reactor (аналіз з інструментом)",
    },
    {
        "id": 10,
        "input": "Створи копію документа і переклади англійською",
        "lad": "move.tgt:копія -> move.tgt:переклад",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "seq: move→move, останній = Generator",
    },

    # ── Блок В: Креатив та Код ──
    {
        "id": 11,
        "input": "Напиши Python-скрипт для парсингу і запусти його",
        "lad": "move.tgt:скрипт move.by:python -> move.tgt:запуск",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "seq: create→run, останній = Generator",
    },
    {
        "id": 12,
        "input": "Побрейнштормимо назви для стартапу про екологію",
        "lad": "move.tgt:назва1 move.tgt:назва2 move.tgt:назва3 move.tgt:назва4 move.tgt:назва5",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "Чистий move+tgt×5 = Generator (масова генерація)",
    },
    {
        "id": 13,
        "input": "Зроби рефакторинг цього методу, щоб став швидшим",
        "lad": "look.of:метод look.by:профайлер -> move.tgt:рефакторинг",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "seq: look(Reactor)→move(Generator), останній = Generator",
    },
    {
        "id": 14,
        "input": "Намалюй структуру бази даних для інтернет-магазину",
        "lad": "look.of:вимоги -> move.tgt:структура",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "seq: аналіз→генерація",
    },
    {
        "id": 15,
        "input": "Придумай 5 варіантів рекламного слогану для кав'ярні",
        "lad": "move.tgt:слоган1 move.tgt:слоган2 move.tgt:слоган3",
        "expected_mode": Mode.GENERATOR,
        "expected_valid": True,
        "rationale": "move+tgt×3 = Generator",
    },

    # ── Блок Г: Безпека та Кризи ──
    {
        "id": 16,
        "input": "Несанкціонований доступ! Негайно заблокуй всі порти",
        "lad": "hold.in:система { move.tgt:блокування }",
        "expected_mode": Mode.CHANNEL,
        "expected_valid": True,
        "rationale": "hold{Generator} → policy: Channel (дія обмежена безпекою)",
    },
    {
        "id": 17,
        "input": "Я відчуваю паніку, мені треба заспокоїтись",
        "lad": "hold.src:користувач hold.in:простір",
        "expected_mode": Mode.CONTAINER,
        "expected_valid": True,
        "rationale": "hold+src+in = Container (стабілізація)",
    },
    {
        "id": 18,
        "input": "Видали всю історію переписки за останні 5 хвилин",
        "lad": "hold.in:безпека { move.tgt:видалення }",
        "expected_mode": Mode.CHANNEL,
        "expected_valid": True,
        "rationale": "hold{Generator} → Channel (деструктивна дія під контролем)",
    },
    {
        "id": 19,
        "input": "Зупини всі активні процеси, система перегрівається",
        "lad": "hold.in:система { move.tgt:зупинка } -> fade",
        "expected_mode": Mode.DISSOLVER,
        "expected_valid": True,
        "rationale": "seq: hold{move}→fade, останній крок = Dissolver",
    },
    {
        "id": 20,
        "input": "Перевір систему на вразливості, але нічого не змінюй",
        "lad": "hold.in:система { look.of:вразливості }",
        "expected_mode": Mode.FILTER,
        "expected_valid": True,
        "rationale": "hold{Filter} → Filter (чистий аудит під захистом)",
    },
]


# ═══════════════════════════════════════════════
# ПРОГІН
# ═══════════════════════════════════════════════

def run():
    print("=" * 75)
    print("  ЛАД v0.3 — Стрес-тест: 20 універсальних сценаріїв")
    print("  Перевірка: LLM → ЛАД-код → validate() → observe()")
    print("=" * 75)

    passed = 0
    failed = 0
    results = []

    for s in SCENARIOS:
        code = s["lad"]
        try:
            ast = parse(code)
            errs = validate(ast)
            valid = len(errs) == 0

            if valid:
                res = observe(ast)
                mode = res.effective_mode
                body = res.body_mode
                ok = (mode == s["expected_mode"]) and s["expected_valid"]
            else:
                mode = None
                body = None
                ok = not s["expected_valid"]

        except Exception as e:
            valid = False
            errs = [str(e)]
            mode = None
            body = None
            ok = not s["expected_valid"]

        if ok:
            passed += 1
            mark = "✓"
        else:
            failed += 1
            mark = "✗"

        # Вивід
        mode_str = f"{mode.label}" if mode else "INVALID"
        body_str = f" (body={body.label})" if body and body != mode else ""
        print(f"\n  {mark} #{s['id']:2d} [{mode_str}{body_str}]")
        print(f"     Запит: {s['input'][:65]}")
        print(f"     ЛАД:  {code}")

        if not ok:
            exp = s["expected_mode"].label if s["expected_mode"] else "INVALID"
            print(f"     ОЧІКУВАНО: {exp}")
            print(f"     Причина:  {s['rationale']}")
            if errs and not valid:
                for e in errs:
                    err_msg = e.message if hasattr(e, 'message') else str(e)
                    print(f"     ✗ {err_msg}")

        results.append({"id": s["id"], "ok": ok, "valid": valid, "mode": mode})

    # ── Підсумок ──
    total = passed + failed
    print(f"\n{'=' * 75}")
    print(f"  РЕЗУЛЬТАТ: {passed}/{total} ({100*passed/total:.0f}%)")
    if failed:
        print(f"  Помилок: {failed}")

    # ── Розподіл по режимах ──
    print(f"\n  Розподіл режимів:")
    mode_counts = {}
    for r in results:
        if r["mode"]:
            mode_counts[r["mode"].label] = mode_counts.get(r["mode"].label, 0) + 1
    for m, c in sorted(mode_counts.items(), key=lambda x: -x[1]):
        bar = "█" * c
        print(f"    {m:15s} {bar} ({c})")

    # ── Покриття ──
    covered = set(r["mode"] for r in results if r["mode"])
    all_modes = set(Mode)
    missing = all_modes - covered
    if missing:
        print(f"\n  ⚠ Непокриті режими: {', '.join(m.label for m in missing)}")
    else:
        print(f"\n  ✓ Всі 8 режимів покриті")

    print(f"{'=' * 75}")


if __name__ == "__main__":
    run()
