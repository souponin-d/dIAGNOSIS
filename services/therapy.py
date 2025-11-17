def generate_treatment_recommendations(
    age,
    gender,
    menopausal_status="premenopausal",  # premenopausal, perimenopausal, postmenopausal
    ER=None, # True, False
    PR=None,  # True, False
    HER2=False,  # True, False
    BRCA_status="negative",  # negative, BRCA1, BRCA2, BRCA1_and_BRCA2
    Ki67=None,  # %
    T="T1",  # e.g., T1, T2, T3, T4
    grade=2,  # 1, 2, 3
    N="N0",  # e.g., N0, N1, N2, N3
    M="M0",  # M0, M1
    e_cadherin_status=None, # True, False (positive, negative/loss)
    surgery=False, # True, False (completed, not_performed)
):
    """
    Генерирует рекомендации по адъювантной/постнеоадъвантной/неоадъвантной/паллиативной терапии РМЖ
    на основе предоставленных параметров пациента.
    Все тексты — на русском языке.
    """
    rec = {
        "diagnostic_check": [],
        "surgery": [],
        "hormone_therapy": [],
        "chemotherapy": [],
        "anti_her2_therapy": [],
        "other_therapy": [],
        "notes": []
    }

    # === 1. ОПРЕДЕЛЕНИЕ СТАДИИ И НАЛИЧИЯ МЕТАСТАЗОВ ===
    metastatic = (M == "M1")
    # Стадия определяется по TNM
    stage = "unknown"
    if M == "M1":
        stage = "IV"
    else:
        # Упрощённое определение стадии (таблица 1.2)
        if T in ["Tis"] and N == "N0" and M == "M0":
            stage = "0"
        elif T in ["T1"] and N == "N0" and M == "M0":
            stage = "IA"
        elif (T in ["T0", "T1"] and N == "N1mi" and M == "M0") or (T == "T1" and N == "N1" and M == "M0") or (T == "T2" and N == "N0" and M == "M0"):
            stage = "IIA"
        elif (T == "T2" and N == "N1" and M == "M0") or (T == "T3" and N == "N0" and M == "M0"):
            stage = "IIB"
        elif (T in ["T0", "T1", "T2"] and N == "N2" and M == "M0") or (T == "T3" and N in ["N1", "N2"] and M == "M0"):
            stage = "IIIA"
        elif (T == "T4" and N in ["N0", "N1", "N2"] and M == "M0"):
            stage = "IIIB"
        elif (T in ["T0", "T1", "T2", "T3", "T4"] and N == "N3" and M == "M0"):
            stage = "IIIC"
        else:
            stage = "early_or_locally_advanced"



    # === 2. ОПРЕДЕЛЕНИЕ МОЛЕКУЛЯРНОГО ПОДТИПА (Таблица 2) ===
    # Преобразуем значения ER, PR, HER2 в строки для сравнения, если они булевы
    ER_str = "positive" if ER else "negative" if ER is not None else None
    PR_str = "positive" if PR else "negative" if PR is not None else None
    HER2_str = "positive" if HER2 else "negative"

    if ER_str == "negative" and PR_str == "negative" and HER2_str == "negative":
        subtype = "triple_negative"
        subtype_rus = "Тройной негативный"
    elif HER2_str == "positive":
        if ER_str == "positive":
            subtype = "luminal_b_her2pos"
            subtype_rus = "Люминальный В (HER2-позитивный)"
        else:
            subtype = "her2_positive_non_luminal"
            subtype_rus = "HER2-позитивный не-люминальный"
    elif ER_str == "positive" and HER2_str == "negative":
        if Ki67 is not None and Ki67 <= 20 and PR_str == "positive":
            subtype = "luminal_a"
            subtype_rus = "Люминальный А"
        else:
            subtype = "luminal_b_her2neg"
            subtype_rus = "Люминальный В (HER2-негативный)"
    else:
        rec["diagnostic_check"].append("Ошибка: невозможно определить подтип на основе предоставленных данных.")
        # Возвращаем только непустые поля
        filtered_rec = {k: v for k, v in rec.items() if v}
        return filtered_rec

    rec["diagnostic_check"].append(f"Молекулярный подтип: {subtype_rus}.")
    rec["diagnostic_check"].append(f"Стадия: {stage}.")
    rec["diagnostic_check"].append(f"BRCA статус: {BRCA_status}.")


    # === 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    def is_high_risk():
        return (N in ['N1a', 'N1b', 'N1c', 'N2a', 'N2b', 'N3a', 'N3b', 'N3c']) or (grade == 3) or (Ki67 and Ki67 > 30)

    def n_category_implies_4plus():
        return N in ['N2a', 'N2b', 'N3a', 'N3b', 'N3c']

    def has_residual_disease():
        # Предполагаем, что ypT/ypN/RCB неизвестны, но если N > N0, то есть риск резидуальной опухоли
        # Это приближённая логика, т.к. ypT/ypN нет.
        return N in ['N1a', 'N1b', 'N1c', 'N2a', 'N2b', 'N3a', 'N3b', 'N3c']

    # === 4. ПРОВЕРКА E-CADHERIN ===
    # Преобразуем boolean e_cadherin_status в строку для внутреннего использования
    e_cadherin_str = "positive" if e_cadherin_status else "negative" if e_cadherin_status is not None else None
    is_lobular = (e_cadherin_str == "negative")

    # === 5. РЕКОМЕНДАЦИИ ПО ОПЕРАТИВНОМУ ЛЕЧЕНИЮ ===
    # Преобразуем boolean surgery в строку для внутреннего использования
    surgery_status_str = "completed" if surgery else "not_performed"

    if stage in ["0", "IA", "IIA", "IIB", "IIIA"]:
        if surgery_status_str == "not_performed":
            rec["surgery"].append("Рекомендовано хирургическое лечение: органосохраняющая операция или мастэктомия с оценкой подмышечных лимфоузлов (БСЛУ или АКС).")
            if T in ["T3", "T4"] or N in ["N2", "N3"]:
                rec["surgery"].append("При местно-распространённом раке (III стадия) может быть рекомендована неоадъювантная терапия до хирургического вмешательства.")
        elif surgery_status_str == "completed":
            rec["notes"].append("Адъювантная/постнеоадъвантная терапия планируется после хирургического вмешательства.")
    elif stage == "IIIB" or stage == "IIIC":
        rec["surgery"].append("Пациентка с местно-распространённым раком молочной железы (стадия III).")
        rec["surgery"].append("Рекомендована неоадъювантная терапия до хирургического вмешательства.")
        rec["notes"].append("Хирургическое лечение может быть выполнено после ответа на неоадъювантную терапию.")
    elif metastatic:
        rec["surgery"].append("При метастатическом раке молочной железы (стадия IV) хирургическое лечение может быть рассмотрено как паллиативное или в определённых случаях при ограниченном метастатическом поражении.")
        rec["notes"].append("Решение о хирургическом вмешательстве принимается индивидуально.")

    # === 6. ЛОГИКА ПО ПОДТИПАМ (Таблицы 3, 4, 5, 8) ===
    # --- Ранний/местно-распространённый РМЖ ---
    if not metastatic:
        if surgery_status_str == "not_performed":
            # --- Неоадъювантная терапия ---
            if subtype in ["triple_negative", "her2_positive_non_luminal"] and stage in ["IIA", "IIB", "IIIA", "IIIB", "IIIC"]:
                rec["chemotherapy"].append(f"Показана неоадъювантная химиотерапия для подтипа {subtype_rus}.")
                if subtype == "triple_negative":
                    rec["chemotherapy"].append("Рекомендуется ХТ антрациклинами и таксанами (например, AC → D или DC).")
                    if BRCA_status in ["BRCA1", "BRCA2", "BRCA1_and_BRCA2"]:
                        rec["notes"].append("Учитывая BRCA-ассоциированный РМЖ, возможно рассмотрение добавления платиновых препаратов (карбоплатин) к неоадъювантной терапии.")
                elif subtype == "her2_positive_non_luminal":
                    rec["anti_her2_therapy"].append("Трастузумаб ± пертузумаб в сочетании с ХТ (например, DC или AC → D).")
            elif subtype == "luminal_b_her2pos" and stage in ["IIA", "IIB", "IIIA", "IIIB", "IIIC"]:
                rec["anti_her2_therapy"].append("Показана неоадъювантная терапия: трастузумаб ± пертузумаб + ХТ.")
            elif subtype == "luminal_b_her2neg" and stage in ["IIA", "IIB", "IIIA"] and (grade == 3 or Ki67 > 30):
                rec["notes"].append("В отдельных случаях при люминальном B HER2-негативном высокого риска может быть рассмотрена неоадъювантная ХТ.")
            else:
                rec["notes"].append("При люминальном А и В HER2-негативном (T1N0, T2N0 без высоких факторов риска) лечение рекомендуется начинать с хирургического вмешательства.")
        elif surgery_status_str == "completed":
            # --- Адъювантная/постнеоадъвантная терапия ---
            if subtype == "luminal_a":
                # --- Гормонотерапия (Таблица 7) ---
                if menopausal_status == "premenopausal":
                    rec["hormone_therapy"].append("Тамоксифен 20 мг внутрь ежедневно в течение 5 лет.")
                    if is_high_risk():
                        factors_str = ", ".join([f for f in [N, f"G{grade}", f"Ki67 {Ki67}%" if Ki67 else None] if f])
                        rec["hormone_therapy"].append(f"У пациента есть факторы неблагоприятного прогноза ({factors_str}):")
                        rec["hormone_therapy"].append("- Тамоксифен 20 мг внутрь ежедневно в течение 10 лет.")
                        rec["hormone_therapy"].append("- Или овариальная супрессия + тамоксифен 20 мг внутрь ежедневно в течение 5 лет.")
                        rec["hormone_therapy"].append(
                            "- Или овариальная супрессия + ингибиторы ароматазы (летрозол 2,5 мг внутрь ежедневно, анастрозол 1 мг внутрь ежедневно или эксеместан 25 мг внутрь ежедневно) в течение 5 лет."
                        )
                else:  # postmenopausal
                    rec["hormone_therapy"].append("Ингибиторы ароматазы: летрозол 2,5 мг внутрь ежедневно, анастрозол 1 мг внутрь ежедневно или эксеместан 25 мг внутрь ежедневно — в течение 5 лет (предпочтительно).")
                    if is_high_risk():
                        factors_str = ", ".join([f for f in [N, f"G{grade}", f"Ki67 {Ki67}%" if Ki67 else None] if f])
                        rec["hormone_therapy"].append(f"У пациента есть факторы неблагоприятного прогноза ({factors_str}):")
                        rec["hormone_therapy"].append("- Ингибиторы ароматазы (летрозол, анастрозол, эксеместан) в течение 7 лет.")
                        rec["hormone_therapy"].append("- Тамоксифен в течение 10 лет.")
                        rec["hormone_therapy"].append("- Тамоксифен 5 лет -> ингибиторы ароматазы (летрозол, анастрозол, эксеместан) 2 года.")

                # --- Химиотерапия (Таблица 3, 4) ---
                if n_category_implies_4plus():
                    rec["chemotherapy"].append("Показана адъювантная химиотерапия (≥4 поражённых лимфоузла).")
                    rec["chemotherapy"].append("Режим DC: доцетаксел 75 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день — 4–6 циклов каждые 3 недели (предпочтительный режим).")
                    rec["chemotherapy"].append("Альтернатива: режим AC: доксорубицин 60 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день — 4 цикла каждые 3 недели.")
                else:
                    rec["chemotherapy"].append("Адъювантная химиотерапия не показана.")

            elif subtype == "luminal_b_her2neg":
                rec["hormone_therapy"].append("Адъювантная гормонотерапия: Тамоксифен 20 мг/сут или ингибитор ароматазы (летрозол 2,5 мг/сут внутрь ежедневно, анастрозол 1 мг/сут внутрь ежедневно или эксеместан 25 мг/сут внутрь ежедневно) в зависимости от менопаузального статуса.")
                if is_lobular:
                    if N in ['N0', 'N1a', 'N1b', 'N1c']:
                        rec["chemotherapy"].append("Проведение адъювантной химиотерапии нецелесообразно при инвазивном дольковом раке и N0–N1 в связи с низкой чувствительностью к ХТ.")
                    else:
                        rec["chemotherapy"].append("Несмотря на дольковый тип, при поражении ≥4 лимфоузлов (N2–N3) показана адъювантная химиотерапия.")
                else:
                    if T in ['T1a', 'T1b'] and N == 'N0':
                        rec["chemotherapy"].append("ХТ не показана (T1a-b, N0).")
                    else:
                        rec["chemotherapy"].append("Рекомендуется ХТ: DC (доцетаксел 75 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4–6 циклов каждые 3 недели (предпочтительный режим).")
                        rec["chemotherapy"].append("Альтернатива: AC (доксорубицин 60 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4 цикла каждые 3 недели.")
                        if T in ['T2', 'T3'] or N in ['N2', 'N3']:
                            rec["chemotherapy"].append("При T2–T3 или N2: DC (доцетаксел 75 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) 6 циклов или AC (4 цикла) → доцетаксел 75 мг/м2 внутривенно в 1-й день 4 цикла или паклитаксел 80 мг/м2 внутривенно еженедельно 12 введений.")

            elif subtype == "luminal_b_her2pos" or subtype == "her2_positive_non_luminal":
                # --- Анти-HER2 терапия (Таблица 5) ---
                if N in ['N2a', 'N3a', 'N3b']:
                    rec["anti_her2_therapy"].append("Трастузумаб 6 мг/кг внутривенно в 1-й день каждые 3 недели + пертузумаб 420 мг внутривенно в 1-й день каждые 3 недели — в течение 12 месяцев.")
                else:
                    rec["anti_her2_therapy"].append("Трастузумаб 6 мг/кг внутривенно в 1-й день каждые 3 недели — в течение 12 месяцев.")

                # --- ХТ ---
                if T in ['T1a'] and N == 'N0':
                    rec["chemotherapy"].append("ХТ и анти-HER2 не показаны.")
                else:
                    rec["chemotherapy"].append("Рекомендуется ХТ: DC (доцетаксел 75 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4 цикла или AC (доксорубицин 60 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4 цикла → таксаны (доцетаксел 75 мг/м2 внутривенно в 1-й день 4 цикла или паклитаксел 80 мг/м2 внутривенно еженедельно 12 введений).")
                    rec["chemotherapy"].append("Альтернатива: доцетаксел 75 мг/м2 внутривенно в 1-й день + карбоплатин AUC6 внутривенно в 1-й день — 6 циклов каждые 3 недели.")

                # --- Постнеоадъювантная терапия ---
                if has_residual_disease():
                    rec["anti_her2_therapy"].append("При резидуальной опухоли: постнеоадъювантный трастузумаб эмтанзин 3,6 мг/кг внутривенно в 1-й день каждые 3 недели — 14 циклов.")
                    rec["notes"].append("При досрочном прекращении введения трастузумаб эмтанзина следует продолжить введение трастузумаба до общей продолжительности 1 года.")

                if subtype == "luminal_b_her2pos":
                    rec["hormone_therapy"].append("Адъювантная гормонотерапия: Тамоксифен 20 мг/сут или ингибитор ароматазы (летрозол 2,5 мг/сут внутрь ежедневно, анастрозол 1 мг/сут внутрь ежедневно или эксеместан 25 мг/сут внутрь ежедневно) в зависимости от менопаузального статуса.")

            elif subtype == "triple_negative":
                if T in ['T1a'] and N == 'N0':
                    rec["chemotherapy"].append("Системная терапия не показана.")
                else:
                    rec["chemotherapy"].append("ХТ с антрациклинами и таксанами: AC (доксорубицин 60 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4 цикла → паклитаксел 80 мг/м2 внутривенно еженедельно 12 введений.")
                    rec["chemotherapy"].append("Альтернатива: DC (доцетаксел 75 мг/м2 внутривенно в 1-й день + циклофосфамид 600 мг/м2 внутривенно в 1-й день) — 4 цикла.")

                # --- Постнеоадъювантная терапия ---
                if has_residual_disease():
                    rec["chemotherapy"].append("Постнеоадъювантный капецитабин 2000 мг/м2 внутрь в 1–14-й дни каждые 3 недели в течение 6 месяцев (при резидуальной опухоли).")
                    if BRCA_status in ["BRCA1", "BRCA2", "BRCA1_and_BRCA2"]:
                        rec["other_therapy"].append("Олапариб 300 мг внутрь 2 раза в день — в течение 1 года (при BRCA+ и резидуальной болезни).")
                    else:
                        rec["notes"].append("При BRCA-негативном статусе олапариб не рекомендуется.")

    # === 7. МЕТАСТАТИЧЕСКИЙ РМЖ ===
    if metastatic:
        rec["notes"].append("Пациентка с метастатическим РМЖ. Рекомендации адаптированы под паллиативную терапию.")
        if subtype.startswith("luminal"):
            rec["hormone_therapy"].append("Гормонотерапия — метод выбора.")
            rec["hormone_therapy"].append("Ингибиторы ароматазы или фулвестрант ± ингибиторы CDK4/6 (рибоциклиб, палбоциклиб, абемациклиб).")
        elif subtype == "triple_negative":
            rec["chemotherapy"].append("Химиотерапия: таксаны, антрациклины, капецитабин, гемцитабин, платины, иксабепилон.")
            if BRCA_status in ["BRCA1", "BRCA2", "BRCA1_and_BRCA2"]:
                rec["other_therapy"].append("PARP-ингибиторы: олапариб или талазопариб (при наличии мутации BRCA).")
        elif HER2_str == "positive":
            rec["anti_her2_therapy"].append("Трастузумаб + пертузумаб + таксаны (I линия).")
            rec["anti_her2_therapy"].append("Трастузумаб эмтанзин (II линия и далее).")
            rec["anti_her2_therapy"].append("Трастузумаб дерукстекан (при прогрессировании после ≥2 линий).")

    # === 8. ОСОБЕННОСТИ У МУЖЧИН ===
    if gender == "male":
        rec["notes"].append("У мужчин с РМЖ рекомендуется генетическое тестирование на мутации BRCA1/2.")
        if subtype.startswith("luminal"):
            rec["hormone_therapy"].append("Тамоксифен 20 мг внутрь ежедневно в течение 5–10 лет.")
            rec["hormone_therapy"].append("Ингибиторы ароматазы в сочетании с аналогами ГРГ (гозерелин, трипторелин).")

    # === 9. ОСТЕОМОДИФИЦИРУЮЩИЕ АГЕНТЫ ===
    if (menopausal_status == "postmenopausal" and (subtype.startswith("luminal") or BRCA_status != "negative")):
        rec["other_therapy"].append("Золедронат 4 мг внутривенно 1 раз в 6 месяцев в течение 2–3 лет.")
        rec["other_therapy"].append("Колекальциферол 400–800 МЕ/сут. + кальция карбонат 500–1000 мг/сут. внутрь ежедневно.")
        rec["notes"].append("Контроль минеральной плотности костей (денситометрия) 1 раз в год.")

    # === 10. ОБЩИЕ ПРИМЕЧАНИЯ ===
    rec["notes"].append("Все рекомендации основаны на Практических рекомендациях RUSSCO 2023.")
    rec["notes"].append("Для точного назначения терапии необходимы патоморфологические данные (pN, ypT, RCB и др.).")
    if menopausal_status == "postmenopausal" or (menopausal_status == "premenopausal" and is_high_risk()):
        rec["notes"].append("При использовании ингибиторов ароматазы или овариальной супрессии — профилактика остеопороза: золедронат, кальций, витамин D.")

    # === 11. ВОЗВРАТ ТОЛЬКО НЕПУСТЫХ ПОЛЕЙ ===
    filtered_rec = {k: v for k, v in rec.items() if v}
    return filtered_rec


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===
if __name__ == "__main__":
    result = generate_treatment_recommendations(
        age=25,
        gender='female',
        menopausal_status="perimenopausal",
        ER=True,
        PR=False,
        HER2=False,
        BRCA_status="negative",
        Ki67=70,
        T="T3",
        grade=2,
        N="N2",
        M="M0",
        e_cadherin_status=False, # <-- Теперь boolean
        surgery=False,           # <-- Теперь boolean
    )

    for section, items in result.items():
        if items:
            section_names = {
                "diagnostic_check": "Диагностическая проверка",
                "surgery": "Хирургическое лечение",
                "hormone_therapy": "Гормонотерапия",
                "chemotherapy": "Химиотерапия",
                "anti_her2_therapy": "Анти-HER2 терапия",
                "other_therapy": "Прочая терапия",
                "notes": "Примечания"
            }
            print(f"\n{section_names.get(section, section)}:")
            for item in items:
                print(f"  - {item}")