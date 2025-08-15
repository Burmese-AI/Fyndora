class BaseFileExporter:
    def __init__(self, filename_prefix: str, blocks: list[dict]):
        self.filename_prefix = filename_prefix
        self.blocks = blocks

    def export(self):
        raise NotImplementedError("Subclasses must implement export()")
