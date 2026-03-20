import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "neis_meal_cli.py"
SPEC = importlib.util.spec_from_file_location("neis_meal_cli", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Failed to load neis_meal_cli module for tests")
cli = importlib.util.module_from_spec(SPEC)
sys.modules["neis_meal_cli"] = cli
SPEC.loader.exec_module(cli)


class MealCliTests(unittest.TestCase):
    def test_format_meal_text_removes_allergy_numbers(self):
        raw = "쌀밥<br/>미역국 (5.6.13.)<br/>제육볶음 (5.10.)"
        dishes = cli.format_meal_text(raw)
        self.assertEqual(dishes, ["쌀밥", "미역국", "제육볶음"])

    def test_get_meals_for_day_sorted(self):
        school = cli.School(name="테스트고", office_code="B10", school_code="7010569")
        payload = {
            "meals": [
                {"name": "석식", "dishes_raw": "돈까스<br/>샐러드"},
                {"name": "중식", "dishes_raw": "쌀밥<br/>된장국"},
            ]
        }

        with mock.patch.object(cli, "proxy_get", return_value=payload):
            meals = cli.get_meals_for_day(school, "20260319")

        self.assertEqual([m["name"] for m in meals], ["중식", "석식"])
        self.assertEqual(meals[0]["dishes"], ["쌀밥", "된장국"])

    def test_get_meals_for_day_groups_same_meal_type(self):
        school = cli.School(name="테스트고", office_code="B10", school_code="7010569")
        payload = {
            "meals": [
                {"name": "중식", "dishes_raw": "쌀밥<br/>된장국"},
                {"name": "중식", "dishes_raw": "돈까스<br/>샐러드"},
                {"name": "석식", "dishes_raw": "볶음밥"},
            ]
        }

        with mock.patch.object(cli, "proxy_get", return_value=payload):
            meals = cli.get_meals_for_day(school, "20260319")

        self.assertEqual([m["name"] for m in meals], ["중식", "석식"])
        self.assertEqual(meals[0]["dishes"], ["쌀밥", "된장국", "돈까스", "샐러드"])

    def test_find_schools_raises_on_invalid_proxy_payload(self):
        with mock.patch.object(cli, "proxy_get", return_value={"schools": "invalid"}):
            with self.assertRaises(cli.NeisError):
                cli.find_schools("테스트고")

    def test_get_timetable_for_day_sorted(self):
        school = cli.School(name="테스트고", office_code="B10", school_code="7010569")
        payload = {
            "timetable": [
                {"grade": "2", "class_name": "1", "period": "2", "subject": "영어"},
                {"grade": "1", "class_name": "3", "period": "1", "subject": "국어"},
                {"grade": "1", "class_name": "3", "period": "2", "subject": "수학"},
            ]
        }

        with mock.patch.object(cli, "proxy_get", return_value=payload):
            timetable = cli.get_timetable_for_day(school, "20260319")

        self.assertEqual(
            timetable,
            [
                {"grade": "1", "class_name": "3", "period": "1", "subject": "국어"},
                {"grade": "1", "class_name": "3", "period": "2", "subject": "수학"},
                {"grade": "2", "class_name": "1", "period": "2", "subject": "영어"},
            ],
        )

    def test_week_dates_from_returns_monday_to_friday(self):
        self.assertEqual(
            cli.week_dates_from("20260319"),
            ["20260316", "20260317", "20260318", "20260319", "20260320"],
        )

    def test_command_timetable_rejects_invalid_calendar_date(self):
        args = cli.build_parser().parse_args(["timetable", "--date", "20260230"])

        with mock.patch("builtins.print") as mocked_print:
            result = cli.command_timetable(args)

        self.assertEqual(result, 1)
        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("유효하지 않은 날짜", printed)

    def test_command_timetable_first_run_prompts_school_and_saves(self):
        args = cli.build_parser().parse_args(["timetable", "--date", "20260319"])
        selected_school = cli.School("테스트고", "B10", "7010569")
        timetable_rows = [{"grade": "1", "class_name": "1", "period": "1", "subject": "국어"}]

        with mock.patch.object(cli, "config_path", return_value=Path("/tmp/missing-config.json")):
            with mock.patch.object(cli, "find_schools", return_value=[selected_school]):
                with mock.patch.object(cli, "save_school") as mocked_save:
                    with mock.patch.object(cli, "save_grade") as mocked_save_grade:
                        with mock.patch.object(cli, "get_timetable_for_day", return_value=timetable_rows):
                            with mock.patch("builtins.input", side_effect=["테스트고", "1"]):
                                result = cli.command_timetable(args)

        self.assertEqual(result, 0)
        mocked_save.assert_called_once_with(selected_school)
        mocked_save_grade.assert_called_once_with("1")

    def test_command_timetable_uses_saved_grade_and_filters(self):
        args = cli.build_parser().parse_args(["timetable", "--date", "20260319"])
        school = cli.School("테스트고", "B10", "7010569")
        timetable_rows = [
            {"grade": "1", "class_name": "1", "period": "1", "subject": "국어"},
            {"grade": "2", "class_name": "1", "period": "1", "subject": "수학"},
        ]

        with mock.patch.object(cli, "get_or_setup_school", return_value=school):
            with mock.patch.object(cli, "load_grade", return_value="1"):
                with mock.patch.object(cli, "get_timetable_for_day", return_value=timetable_rows):
                    with mock.patch("builtins.print") as mocked_print:
                        result = cli.command_timetable(args)

        self.assertEqual(result, 0)
        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("학년: 1", printed)
        self.assertIn("국어", printed)
        self.assertNotIn("수학", printed)

    def test_command_timetable_week_mode_fetches_all_weekdays(self):
        args = cli.build_parser().parse_args(["timetable", "--date", "20260319", "--week"])
        school = cli.School("테스트고", "B10", "7010569")

        def fake_rows(_school, date):
            return [{"grade": "1", "class_name": "1", "period": "1", "subject": f"과목-{date}"}]

        with mock.patch.object(cli, "get_or_setup_school", return_value=school):
            with mock.patch.object(cli, "load_grade", return_value="1"):
                with mock.patch.object(cli, "get_timetable_for_day", side_effect=fake_rows) as mocked_day:
                    with mock.patch("builtins.print") as mocked_print:
                        result = cli.command_timetable(args)

        self.assertEqual(result, 0)
        self.assertEqual(mocked_day.call_count, 5)
        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("주간: 20260316 ~ 20260320", printed)
        self.assertIn("과목-20260316", printed)
        self.assertIn("과목-20260320", printed)

    def test_set_grade_and_load_grade(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": temp_dir}, clear=False):
                cli.save_grade("2")
                grade = cli.load_grade()

        self.assertEqual(grade, "2")

    def test_command_meals_rejects_invalid_calendar_date(self):
        args = cli.build_parser().parse_args(["meals", "--date", "20260230"])

        with mock.patch.object(cli, "load_school", return_value=cli.School("테스트고", "B10", "7010569")):
            with mock.patch("builtins.print") as mocked_print:
                result = cli.command_meals(args)

        self.assertEqual(result, 1)
        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("유효하지 않은 날짜", printed)

    def test_command_set_school_lists_all_matches_when_duplicate(self):
        duplicates = [
            cli.School("테스트고", "B10", "1001"),
            cli.School("테스트고", "B10", "1002"),
            cli.School("테스트고", "B10", "1003"),
        ]
        args = cli.build_parser().parse_args(["set-school", "테스트고"])

        with mock.patch.object(cli, "find_schools", return_value=duplicates):
            with mock.patch("builtins.print") as mocked_print:
                result = cli.command_set_school(args)

        self.assertEqual(result, 1)
        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("1. 테스트고 (B10/1001)", printed)
        self.assertIn("3. 테스트고 (B10/1003)", printed)

    def test_command_meals_first_run_prompts_school_and_saves(self):
        args = cli.build_parser().parse_args(["meals", "--date", "20260319"])
        selected_school = cli.School("테스트고", "B10", "7010569")
        meals_data = [{"name": "중식", "dishes": ["쌀밥", "된장국"]}]

        with mock.patch.object(cli, "config_path", return_value=Path("/tmp/missing-config.json")):
            with mock.patch.object(cli, "find_schools", return_value=[selected_school]):
                with mock.patch.object(cli, "save_school") as mocked_save:
                    with mock.patch.object(cli, "get_meals_for_day", return_value=meals_data):
                        with mock.patch("builtins.input", return_value="테스트고"):
                            result = cli.command_meals(args)

        self.assertEqual(result, 0)
        mocked_save.assert_called_once_with(selected_school)

    def test_command_meals_first_run_duplicate_school_requires_index(self):
        args = cli.build_parser().parse_args(["meals", "--date", "20260319"])
        schools = [
            cli.School("테스트고", "B10", "1001"),
            cli.School("테스트고", "B10", "1002"),
        ]

        with mock.patch.object(cli, "config_path", return_value=Path("/tmp/missing-config.json")):
            with mock.patch.object(cli, "find_schools", return_value=schools):
                with mock.patch.object(cli, "save_school") as mocked_save:
                    with mock.patch.object(cli, "get_meals_for_day", return_value=[]):
                        with mock.patch("builtins.input", side_effect=["테스트고", "2"]):
                            result = cli.command_meals(args)

        self.assertEqual(result, 0)
        mocked_save.assert_called_once_with(schools[1])

    def test_save_and_load_school(self):
        school = cli.School(name="테스트중", office_code="D10", school_code="1234567")
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": temp_dir}, clear=False):
                cli.save_school(school)
                loaded = cli.load_school()
        self.assertEqual(loaded, school)

    def test_save_school_raises_on_io_error(self):
        school = cli.School(name="테스트중", office_code="D10", school_code="1234567")
        with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with self.assertRaises(cli.NeisError):
                cli.save_school(school)

    def test_load_school_raises_on_io_error(self):
        fake_path = Path("/tmp/fake-config.json")
        with mock.patch.object(cli, "config_path", return_value=fake_path):
            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch.object(Path, "read_text", side_effect=OSError("permission denied")):
                    with self.assertRaises(cli.NeisError):
                        cli.load_school()


if __name__ == "__main__":
    unittest.main()
