class Response:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def iter_content(self, chunk_size=1024):
        return iter([])

def get(url, stream=False, timeout=0):
    raise NotImplementedError("requests.get is not implemented")
