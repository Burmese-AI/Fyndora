class BaseFileExporter:
    def __init__(self, filename_prefix: str, columns: list[tuple], data: list[dict]):
        self.filename_prefix = filename_prefix
        self.columns = columns
        self.data = data

    def export(self):
        pass
