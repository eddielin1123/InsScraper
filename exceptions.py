class NotFound(Exception):
    '''Post, page or profile not found / doesn't exist / deleted'''
    pass


class TemporarilyBanned(Exception):
    '''User account rate limited'''
    pass


class AccountDisabled(Exception):
    '''User account disabled, with option to appeal'''
    pass

class ItemTransferError(Exception):
    '''failed to turn json data to item class'''
    pass