import yaml
from collections import OrderedDict
from pathlib import Path

# Custom loader to preserve order
def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        lambda loader, node: object_pairs_hook(loader.construct_pairs(node))
    )
    return yaml.load(stream, OrderedLoader)

# Custom dumper to preserve order
def ordered_dump(data, stream=None, Dumper=yaml.SafeDumper, **kwds):
    class OrderedDumper(Dumper):
        pass
    OrderedDumper.add_representer(OrderedDict,
        lambda dumper, data: dumper.represent_dict(data.items()))
    return yaml.dump(data, stream, OrderedDumper, **kwds)

class OptionFile:
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not Path(file_path).exists():
            self.db_path = OrderedDict([
                ('anatomical', ''),
                ('functional', '')
            ])
            self.subject_pattern = ''
            self.data_types = OrderedDict()
        else:
            data = self.__read_file(file_path)
            self.db_path = data['db_path']
            self.subject_pattern = data['subject_structure']['subject_pattern']
            self.data_types = data['subject_structure']['data_types']

    def __read_file(self, file_path: str):
        """Read the content of the file."""
        with open(file_path, 'r') as file:
            config_data = ordered_load(file, yaml.SafeLoader)
        return config_data

    def save(self):
        """Save the changes to the file."""
        with open(self.file_path, 'w') as file:
            self.data = OrderedDict([
                ('db_path', self.db_path),
                ('subject_structure', OrderedDict([
                    ('subject_pattern', self.subject_pattern),
                    ('data_types', self.data_types)
                ]))
            ])
            ordered_dump(self.data, file, default_flow_style=False)
