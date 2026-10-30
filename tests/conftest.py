from jobradar.core.settings import Settings

# Prevent application modules imported during collection from reading the local .env.
Settings.model_config["env_file"] = None
