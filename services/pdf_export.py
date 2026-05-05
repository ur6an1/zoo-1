"""Генерация PDF-карточки питомца."""

import io
import logging
from datetime import datetime
from fpdf import FPDF

logger = logging.getLogger(__name__)


class PetPDF(FPDF):
    """PDF с поддержкой кириллицы."""

    def __init__(self):
        super().__init__()
        self.add_font("dejavu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        self.add_font("dejavu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)

    def header(self):
        self.set_font("dejavu", "B", 14)
        self.cell(0, 10, "ZooBuddy — Карточка питомца", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("dejavu", "", 8)
        self.cell(0, 10, f"Сгенерировано {datetime.now().strftime('%d.%m.%Y %H:%M')} | ZooBuddy Bot", align="C")


def generate_pet_pdf(
    pet_data: dict,
    vaccinations: list[dict],
    vet_visits: list[dict],
    weight_records: list[dict],
    allergies: list[dict],
) -> bytes | None:
    """Генерирует PDF с данными питомца.

    Args:
        pet_data: {"name", "species", "breed", "birth_date", "age", "weight", "target_weight"}
        vaccinations: [{"name", "date_done", "next_date", "notes"}]
        vet_visits: [{"visit_date", "diagnosis", "treatment"}]
        weight_records: [{"weight", "recorded_at"}]
        allergies: [{"allergen", "reaction"}]

    Returns:
        PDF bytes or None.
    """
    try:
        pdf = PetPDF()
        pdf.add_page()

        # Профиль
        pdf.set_font("dejavu", "B", 12)
        pdf.cell(0, 8, f"Профиль: {pet_data['name']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("dejavu", "", 10)

        fields = [
            ("Вид", pet_data.get("species", "—")),
            ("Порода", pet_data.get("breed") or "—"),
            ("Дата рождения", pet_data.get("birth_date") or "—"),
            ("Возраст", pet_data.get("age") or "—"),
            ("Вес", f"{pet_data['weight']} кг" if pet_data.get("weight") else "—"),
            ("Целевой вес", f"{pet_data['target_weight']} кг" if pet_data.get("target_weight") else "—"),
        ]
        for label, val in fields:
            pdf.cell(50, 7, f"{label}:", new_x="RIGHT")
            pdf.cell(0, 7, val, new_x="LMARGIN", new_y="NEXT")

        # Прививки
        if vaccinations:
            pdf.ln(5)
            pdf.set_font("dejavu", "B", 11)
            pdf.cell(0, 8, f"Прививки ({len(vaccinations)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("dejavu", "", 9)
            for v in vaccinations[:20]:
                line = f"  {v['date_done']} — {v['name']}"
                if v.get("next_date"):
                    line += f" (след.: {v['next_date']})"
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

        # Визиты
        if vet_visits:
            pdf.ln(5)
            pdf.set_font("dejavu", "B", 11)
            pdf.cell(0, 8, f"Визиты к ветеринару ({len(vet_visits)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("dejavu", "", 9)
            for v in vet_visits[:20]:
                pdf.cell(0, 6, f"  {v['visit_date']}", new_x="LMARGIN", new_y="NEXT")
                if v.get("diagnosis"):
                    pdf.cell(0, 6, f"    Диагноз: {v['diagnosis'][:80]}", new_x="LMARGIN", new_y="NEXT")
                if v.get("treatment"):
                    pdf.cell(0, 6, f"    Лечение: {v['treatment'][:80]}", new_x="LMARGIN", new_y="NEXT")

        # Вес
        if weight_records:
            pdf.ln(5)
            pdf.set_font("dejavu", "B", 11)
            pdf.cell(0, 8, f"История веса ({len(weight_records)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("dejavu", "", 9)
            for w in weight_records[:30]:
                pdf.cell(0, 6, f"  {w['recorded_at']} — {w['weight']} кг", new_x="LMARGIN", new_y="NEXT")

        # Аллергии
        if allergies:
            pdf.ln(5)
            pdf.set_font("dejavu", "B", 11)
            pdf.cell(0, 8, f"Аллергии ({len(allergies)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("dejavu", "", 9)
            for a in allergies:
                pdf.cell(0, 6, f"  {a['allergen']} — {a.get('reaction') or '—'}", new_x="LMARGIN", new_y="NEXT")

        buf = io.BytesIO()
        pdf.output(buf)
        return buf.getvalue()

    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        return None
