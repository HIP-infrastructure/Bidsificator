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
            self.data_paths = OrderedDict([
                ('main', '')
            ])
            self.subject_pattern = ''
            self.file_types = OrderedDict()
        else:
            data = self.__read_file(file_path)
            # Handle empty or invalid config file
            if not data:
                self.data_paths = OrderedDict([('main', '')])
                self.subject_pattern = ''
                self.file_types = OrderedDict()
            # Support both old and new format during transition
            elif 'data_paths' in data:
                # New format
                self.data_paths = data['data_paths']
                self.subject_pattern = data['subject_pattern']
                self.file_types = data['file_types']
            else:
                # Old format - convert to new format
                self.data_paths = data['db_path']
                self.subject_pattern = data['subject_structure']['subject_pattern']
                self.file_types = data['subject_structure']['data_types']

    def __read_file(self, file_path: str):
        """Read the content of the file."""
        with open(file_path, 'r') as file:
            config_data = ordered_load(file, yaml.SafeLoader)
        return config_data

    def save(self):
        """Save the changes to the file."""
        with open(self.file_path, 'w') as file:
            self.data = OrderedDict([
                ('data_paths', self.data_paths),
                ('subject_pattern', self.subject_pattern),
                ('file_types', self.file_types)
            ])
            ordered_dump(self.data, file, default_flow_style=False)
