class TimeoffBalanceException(Exception):
    pass


class TimeoffZeroDaysException(Exception):
    pass


class ExistingTimeoffPeriodTakenException(Exception):
    pass


class ExistingTimeoffPeriodRequestException(Exception):
    pass
