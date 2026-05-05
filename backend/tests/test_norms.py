"""Tests for backend.services.norms — food/water calculations, progress bars."""

from backend.services.norms import calc_food_norm, calc_progress_bar, weight_progress


class TestCalcFoodNorm:
    def test_no_weight(self):
        result = calc_food_norm("собака", None, 12)
        assert result["food_g"] == 0
        assert result["water_ml"] == 0

    def test_zero_weight(self):
        result = calc_food_norm("собака", 0, 12)
        assert result["food_g"] == 0

    def test_negative_weight(self):
        result = calc_food_norm("собака", -1, 12)
        assert result["food_g"] == 0

    def test_dog_puppy(self):
        result = calc_food_norm("собака", 5.0, 4)
        assert result["food_g"] == 200  # 5 * 40
        assert result["meals_per_day"] == 3  # < 6 months
        assert result["water_ml"] == 250  # 5 * 50

    def test_dog_puppy_6m(self):
        result = calc_food_norm("собака", 10.0, 8)
        assert result["food_g"] == 400  # 10 * 40
        assert result["meals_per_day"] == 2  # >= 6 months

    def test_dog_small(self):
        result = calc_food_norm("собака", 5.0, 24)
        assert result["food_g"] == 150  # 5 * 30
        assert result["meals_per_day"] == 2

    def test_dog_medium(self):
        result = calc_food_norm("собака", 15.0, 36)
        assert result["food_g"] == 375  # 15 * 25

    def test_dog_large(self):
        result = calc_food_norm("собака", 40.0, 60)
        assert result["food_g"] == 800  # 40 * 20

    def test_cat_kitten(self):
        result = calc_food_norm("кошка", 2.0, 6)
        assert result["food_g"] == 100  # 2 * 50
        assert result["meals_per_day"] == 2  # >= 6 months

    def test_cat_kitten_young(self):
        result = calc_food_norm("кошка", 1.0, 3)
        assert result["meals_per_day"] == 3  # < 6 months

    def test_cat_adult(self):
        result = calc_food_norm("кошка", 4.0, 36)
        assert result["food_g"] == 120  # 4 * 30
        assert result["water_ml"] == 160  # 4 * 40

    def test_cat_adult_min(self):
        result = calc_food_norm("кошка", 1.0, 24)
        assert result["food_g"] == 40  # max(30, 40) = 40

    def test_bird(self):
        result = calc_food_norm("птица", 0.5, 12)
        assert result["food_g"] == 50  # max(0.5*100, 10)
        assert result["water_ml"] == 25

    def test_bird_tiny(self):
        result = calc_food_norm("птица", 0.05, 12)
        assert result["food_g"] == 10  # min is 10

    def test_rodent(self):
        result = calc_food_norm("грызун", 0.2, 12)
        assert result["food_g"] == 10  # max(0.2*50, 5)

    def test_unknown_species(self):
        result = calc_food_norm("рыба", 2.0, 12)
        assert result["food_g"] == 50  # 2 * 25

    def test_description_format(self):
        result = calc_food_norm("собака", 10.0, 24)
        assert "г корма/день" in result["description"]
        assert "мл воды/день" in result["description"]


class TestCalcProgressBar:
    def test_zero_target(self):
        assert calc_progress_bar(5, 0) == "▱" * 10

    def test_negative_target(self):
        assert calc_progress_bar(5, -1) == "▱" * 10

    def test_half(self):
        result = calc_progress_bar(5.0, 10.0)
        assert result.startswith("▰" * 5 + "▱" * 5)
        assert "50%" in result

    def test_full(self):
        result = calc_progress_bar(10.0, 10.0)
        assert result.startswith("▰" * 10)
        assert "100%" in result

    def test_over_100(self):
        result = calc_progress_bar(15.0, 10.0)
        assert "100%" in result

    def test_custom_length(self):
        result = calc_progress_bar(5.0, 10.0, length=20)
        assert len(result.split(" ")[0]) == 20


class TestWeightProgress:
    def test_no_current(self):
        assert weight_progress(None, 10.0) is None

    def test_no_target(self):
        assert weight_progress(5.0, None) is None

    def test_goal_reached(self):
        result = weight_progress(10.0, 10.0)
        assert "достигнут" in result

    def test_need_to_lose(self):
        result = weight_progress(12.0, 10.0)
        assert "сбросить" in result
        assert "2.0" in result

    def test_need_to_gain(self):
        result = weight_progress(8.0, 10.0)
        assert "набрать" in result
        assert "2.0" in result

    def test_close_to_goal(self):
        result = weight_progress(10.05, 10.0)
        assert "достигнут" in result
