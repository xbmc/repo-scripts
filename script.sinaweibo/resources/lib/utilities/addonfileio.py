
class FileIO:
    @staticmethod
    def filewrite(_file, contents):
        with open(_file, "w") as f:
            f.write(contents)
        return

    @staticmethod
    def fileread(_file):
        with open(_file, "r") as f:
            contents = f.read()
        return contents
