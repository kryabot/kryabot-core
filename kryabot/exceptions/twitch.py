
class ExpiredAuthToken(Exception):
    def __init__(self, err):
        super().__init__()
        self.resp_error = err

    def __str__(self):
        return str(self.resp_error)

