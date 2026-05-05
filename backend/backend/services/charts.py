"""Генерация графиков питания."""

import io
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# ── Стиль графиков ──
plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.facecolor": "#f8f9fa",
    "axes.facecolor": "#ffffff",
    "axes.grid": True,
    "grid.alpha": 0.3,
})

COLORS = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4"]


def generate_feeding_chart(food_entries: list, water_entries: list, pet_names: dict, days: int = 7) -> bytes | None:
    """Генерирует комбинированный график питания за N дней.

    Включает:
    - Столбчатая: количество приёмов пищи по дням
    - Столбчатая: потребление воды по дням (мл)

    Args:
        food_entries: Список FoodEntry.
        water_entries: Список WaterEntry.
        pet_names: dict {pet_id: name}.
        days: За сколько дней строить график.

    Returns:
        PNG-изображение в байтах или None.
    """
    try:
        today = date.today()
        start_date = today - timedelta(days=days - 1)
        date_range = [start_date + timedelta(days=i) for i in range(days)]
        date_labels = [d.strftime("%d.%m") for d in date_range]

        # Подсчёт приёмов пищи по дням и питомцам
        food_by_day: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
        for entry in food_entries:
            d = entry.meal_time.date() if isinstance(entry.meal_time, datetime) else entry.meal_time
            if start_date <= d <= today:
                food_by_day[entry.pet_id][d] += 1

        # Подсчёт воды по дням и питомцам
        water_by_day: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
        for entry in water_entries:
            d = entry.recorded_at.date() if isinstance(entry.recorded_at, datetime) else entry.recorded_at
            if start_date <= d <= today:
                water_by_day[entry.pet_id][d] += entry.amount_ml

        has_food = any(food_by_day.values())
        has_water = any(water_by_day.values())

        if not has_food and not has_water:
            return None

        num_plots = (1 if has_food else 0) + (1 if has_water else 0)
        fig, axes = plt.subplots(num_plots, 1, figsize=(10, 4.5 * num_plots))
        if num_plots == 1:
            axes = [axes]

        plot_idx = 0

        # ── График приёмов пищи ──
        if has_food:
            ax = axes[plot_idx]
            plot_idx += 1

            pet_ids = sorted(food_by_day.keys())
            bar_width = 0.8 / max(len(pet_ids), 1)
            x_pos = range(len(date_range))

            for i, pid in enumerate(pet_ids):
                values = [food_by_day[pid].get(d, 0) for d in date_range]
                offset = (i - len(pet_ids) / 2 + 0.5) * bar_width
                bars = ax.bar(
                    [x + offset for x in x_pos],
                    values,
                    width=bar_width,
                    label=pet_names.get(pid, f"#{pid}"),
                    color=COLORS[i % len(COLORS)],
                    alpha=0.85,
                    edgecolor="white",
                    linewidth=0.5,
                )
                # Числа над столбцами
                for bar, val in zip(bars, values):
                    if val > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.1,
                            str(val),
                            ha="center",
                            va="bottom",
                            fontsize=8,
                            fontweight="bold",
                        )

            ax.set_title("🍽 Приёмы пищи по дням")
            ax.set_ylabel("Кол-во приёмов")
            ax.set_xticks(x_pos)
            ax.set_xticklabels(date_labels, rotation=45, ha="right")
            ax.legend(loc="upper left", fontsize=9)
            ax.set_ylim(bottom=0)
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        # ── График потребления воды ──
        if has_water:
            ax = axes[plot_idx]
            plot_idx += 1

            pet_ids = sorted(water_by_day.keys())
            bar_width = 0.8 / max(len(pet_ids), 1)
            x_pos = range(len(date_range))

            for i, pid in enumerate(pet_ids):
                values = [water_by_day[pid].get(d, 0) for d in date_range]
                offset = (i - len(pet_ids) / 2 + 0.5) * bar_width
                bars = ax.bar(
                    [x + offset for x in x_pos],
                    values,
                    width=bar_width,
                    label=pet_names.get(pid, f"#{pid}"),
                    color=COLORS[i % len(COLORS)],
                    alpha=0.85,
                    edgecolor="white",
                    linewidth=0.5,
                )
                for bar, val in zip(bars, values):
                    if val > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 5,
                            f"{val}",
                            ha="center",
                            va="bottom",
                            fontsize=8,
                        )

            ax.set_title("💧 Потребление воды по дням (мл)")
            ax.set_ylabel("Объём (мл)")
            ax.set_xticks(x_pos)
            ax.set_xticklabels(date_labels, rotation=45, ha="right")
            ax.legend(loc="upper left", fontsize=9)
            ax.set_ylim(bottom=0)

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf.read()

    except Exception as e:
        logger.error(f"Ошибка генерации графика питания: {e}")
        return None


def generate_daily_timeline(
    food_entries: list, water_entries: list, pet_names: dict, target_date: date = None,
) -> bytes | None:
    """Генерирует таймлайн питания за день.

    Горизонтальная шкала 0-24 часа, точки = приёмы пищи и воды.

    Args:
        food_entries: Записи еды за день.
        water_entries: Записи воды за день.
        pet_names: dict {pet_id: name}.
        target_date: Дата (по умолчанию — сегодня).

    Returns:
        PNG-изображение в байтах или None.
    """
    if not food_entries and not water_entries:
        return None

    if target_date is None:
        target_date = date.today()

    try:
        fig, ax = plt.subplots(figsize=(12, 4))

        y_labels = []
        y_pos = 0

        # Группируем по питомцам
        all_pet_ids = set()
        for e in food_entries:
            all_pet_ids.add(e.pet_id)
        for e in water_entries:
            all_pet_ids.add(e.pet_id)

        for i, pid in enumerate(sorted(all_pet_ids)):
            name = pet_names.get(pid, f"#{pid}")
            color = COLORS[i % len(COLORS)]

            # Еда
            pet_food = [e for e in food_entries if e.pet_id == pid]
            if pet_food:
                y_labels.append(f"🍽 {name}")
                hours = []
                labels = []
                for e in pet_food:
                    t = e.meal_time if isinstance(e.meal_time, datetime) else datetime.combine(target_date, e.meal_time)
                    h = t.hour + t.minute / 60
                    hours.append(h)
                    labels.append(e.food_name[:15])

                ax.scatter(hours, [y_pos] * len(hours), s=120, color=color, zorder=5, marker="o")
                for h, label in zip(hours, labels):
                    ax.annotate(
                        label,
                        (h, y_pos),
                        textcoords="offset points",
                        xytext=(0, 12),
                        ha="center",
                        fontsize=7,
                        rotation=30,
                    )
                y_pos += 1

            # Вода
            pet_water = [e for e in water_entries if e.pet_id == pid]
            if pet_water:
                y_labels.append(f"💧 {name}")
                hours = []
                labels = []
                for e in pet_water:
                    t = (
                        e.recorded_at if isinstance(e.recorded_at, datetime)
                        else datetime.combine(target_date, e.recorded_at)
                    )
                    h = t.hour + t.minute / 60
                    hours.append(h)
                    labels.append(f"{e.amount_ml}мл")

                ax.scatter(hours, [y_pos] * len(hours), s=100, color=color, zorder=5, marker="D", alpha=0.7)
                for h, label in zip(hours, labels):
                    ax.annotate(
                        label,
                        (h, y_pos),
                        textcoords="offset points",
                        xytext=(0, 12),
                        ha="center",
                        fontsize=7,
                    )
                y_pos += 1

        ax.set_xlim(-0.5, 24.5)
        ax.set_xticks(range(0, 25, 2))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 2)], fontsize=8)
        ax.set_xlabel("Время")

        ax.set_yticks(range(len(y_labels)))
        ax.set_yticklabels(y_labels)
        ax.set_title(f"📊 Расписание питания — {target_date.strftime('%d.%m.%Y')}")
        ax.grid(axis="x", alpha=0.3)
        ax.grid(axis="y", alpha=0.1)

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf.read()

    except Exception as e:
        logger.error(f"Ошибка генерации таймлайна: {e}")
        return None
