from pathlib import Path

def get_settings_module():
    """
    Automatically detect whether to use development or production settings.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent


    prod_env = BASE_DIR / ".env.prod"
    dev_env = BASE_DIR / ".env.dev"

    if prod_env.is_file():
        print('-------------------------')
        print("PRODUCTION MODE")
        print('-------------------------')
        return "point_of_sale.settings_prod"

    if dev_env.is_file():
        print('-------------------------')
        print("DEVELOPMENT MODE")
        print('-------------------------')
        return "point_of_sale.settings_dev"

    raise RuntimeError(
        "\nNo environment file found.\n"
        "Expected one of:\n"
        "    .env.prod\n"
        "    .env.dev\n"
    )