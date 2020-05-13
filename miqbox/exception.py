class MiqBoxException(Exception):
    """Base class for miqbox exception"""

    pass


class DBConfigError(MiqBoxException):
    """Error in db configuration"""

    pass
