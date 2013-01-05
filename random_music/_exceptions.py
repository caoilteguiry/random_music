
class _Error(Exception):
    """
    Base class for for all random_music exceptions.
    """


class DirectoryNotFoundError(_Error):
    """
    The specified directory could not be found.
    """
    def __init__(self, dirname):
        """
        :param dirname: name of directory which was not found
        :type dirname: str
        """
        self.dirname = dirname
        self.value = "The '%s' directory could not be found" % dirname
        Exception.__init__(self, self.value)

    def __str__(self):
        return repr(self.value)


class MissingConfigFileError(_Error):
    """
    Config file could not be found.
    """
    def __init__(self, config_file):
        """
        :param config_file: the config file which could not be found.
        :type config_file: str
        """
        self.config_file = config_file
        self.value = "The config file '%s' could not be found" % config_file

    def __str__(self):
        return repr(self.value)


