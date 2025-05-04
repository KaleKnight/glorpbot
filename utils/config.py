import logging
import yaml

def get_config(filename="config.yaml"):
    try:
        with open(filename, "r") as file:
            config = yaml.safe_load(file)
            if config is None:
                logging.error(f"Config file {filename} is empty or invalid.")
                raise ValueError("Config file is empty or invalid")
            if not isinstance(config, dict):
                logging.error(f"Config file {filename} did not load as a dictionary.")
                raise ValueError("Config file did not load as a dictionary")
            return config
    except FileNotFoundError:
        logging.error(f"Config file {filename} not found.")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config file {filename}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading config file {filename}: {e}")
        raise