class Tag:
    def __init__(self):
        self.tag = []

    def set_tag(self, tag):
        self.tag = tag

    def __str__(self):
        return '|'.join(self.tag)
