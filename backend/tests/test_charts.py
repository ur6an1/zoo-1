"""Smoke tests for backend.services.charts — chart generation."""

from datetime import date, datetime

from backend.services.charts import generate_daily_timeline, generate_feeding_chart


class FakeFoodEntry:
    def __init__(self, pet_id, meal_time, food_name="Корм"):
        self.pet_id = pet_id
        self.meal_time = meal_time
        self.food_name = food_name


class FakeWaterEntry:
    def __init__(self, pet_id, recorded_at, amount_ml=200):
        self.pet_id = pet_id
        self.recorded_at = recorded_at
        self.amount_ml = amount_ml


class TestGenerateFeedingChart:
    def test_returns_none_when_no_data(self):
        result = generate_feeding_chart([], [], {})
        assert result is None

    def test_returns_bytes_with_food_data(self):
        today = date.today()
        entries = [FakeFoodEntry(1, datetime.combine(today, datetime.min.time()))]
        result = generate_feeding_chart(entries, [], {1: "Rex"})
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_returns_bytes_with_water_data(self):
        today = date.today()
        water = [FakeWaterEntry(1, datetime.combine(today, datetime.min.time()))]
        result = generate_feeding_chart([], water, {1: "Rex"})
        assert isinstance(result, bytes)

    def test_returns_bytes_with_both(self):
        today = date.today()
        food = [FakeFoodEntry(1, datetime.combine(today, datetime.min.time()))]
        water = [FakeWaterEntry(1, datetime.combine(today, datetime.min.time()))]
        result = generate_feeding_chart(food, water, {1: "Rex"})
        assert isinstance(result, bytes)


class TestGenerateDailyTimeline:
    def test_returns_none_when_no_data(self):
        result = generate_daily_timeline([], [], {})
        assert result is None

    def test_returns_bytes_with_data(self):
        today = date.today()
        now = datetime.now()
        food = [FakeFoodEntry(1, now)]
        water = [FakeWaterEntry(1, now)]
        result = generate_daily_timeline(food, water, {1: "Rex"}, target_date=today)
        assert isinstance(result, bytes)
        assert len(result) > 100
