import configparser
import copy
import os.path


class ConfigError(ValueError):
    pass


def get_config_path(config_path):

    if config_path is not None:
        return os.path.realpath(config_path)

    maybe_config_dir = os.path.realpath(".")

    while True:

        maybe_config_path = os.path.join(
            maybe_config_dir,
            "locald.ini",
        )

        if os.path.exists(maybe_config_path):
            return maybe_config_path

        if maybe_config_dir == "/":
            raise Exception("Unable to locate configuration file")

        maybe_config_dir, _ = os.path.split(maybe_config_dir)


def get_config(config_path):

    config_path = get_config_path(config_path)
    config_dir, _ = os.path.split(config_path)

    parser = configparser.ConfigParser()
    parser.read(config_path)

    config = copy.deepcopy(parser._sections)

    if "locald" in config:
        key = "locald"
    elif "service" in config:
        key = "service"
    else:
        raise ConfigError(
            "incorrectly structured config file '{}' {}"
            .format(config_path, config)
        )

    config[key]["config_path"] = config_path
    config[key]["config_dir"] = config_dir

    return config
