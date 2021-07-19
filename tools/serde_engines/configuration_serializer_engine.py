
def serialize_toml(file, *args):
    from tools.serde_customized.toml import to_toml
    _serialize(file, to_toml, *args)


def serialize_json(file, *args):
    from tools.serde_customized.json import to_json
    _serialize(file, to_json, *args)


def serialize_yaml(file, *args):
    from tools.serde_customized.yaml import to_yaml
    _serialize(file, to_yaml, *args)


def _serialize(file, func, *args):

    config_items = {}
    for i in range(0, len(args)):
        config_items[f"ConfigItem{i}"] = args[i]

    file.write(func(config_items))
