"""Safety-contract tests for the WH-M01 database helper."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from big_data_example.labs.retail_sales.wh_m01_database import (
    LAB_DATABASE,
    LAB_LAYER_RESET_ORDER,
    LAB_SCHEMAS,
    PostgresConfig,
    drop_lab_database,
    make_engine,
    repository_root,
)


class MedallionLabDatabaseSafetyTest(TestCase):
    def test_targets_are_fixed_to_the_lab_database_and_schemas(self) -> None:
        self.assertEqual(LAB_DATABASE, "week3_medallion_lab")
        self.assertEqual(LAB_SCHEMAS, ("gold", "silver", "bronze"))
        self.assertNotIn("week3_hw", LAB_SCHEMAS)
        self.assertNotIn("bigdata", LAB_SCHEMAS)
        self.assertEqual(LAB_LAYER_RESET_ORDER["gold"], ("gold",))
        self.assertEqual(LAB_LAYER_RESET_ORDER["silver"], ("gold", "silver"))
        self.assertEqual(LAB_LAYER_RESET_ORDER["schemas"], LAB_SCHEMAS)

    def test_wrong_destructive_confirmation_is_refused_before_configuration(self) -> None:
        with patch(
            "big_data_example.labs.retail_sales.wh_m01_database.load_postgres_config"
        ) as load_config:
            with self.assertRaisesRegex(ValueError, "no database was removed"):
                drop_lab_database("week3_hw")

        load_config.assert_not_called()

    def test_engine_refuses_homework_database(self) -> None:
        config = PostgresConfig(
            user="example-user",
            password="not-a-real-password",
            maintenance_database="bigdata",
            port=5432,
        )
        with patch(
            "big_data_example.labs.retail_sales.wh_m01_database.load_postgres_config",
            return_value=config,
        ):
            with self.assertRaisesRegex(ValueError, "Refusing connection"):
                make_engine("week3_hw", Path("/unused"))


if __name__ == "__main__":
    from unittest import main

    main()
