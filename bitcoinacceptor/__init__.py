"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Released into the public domain.
"""

from collections import namedtuple
from hashlib import md5
from time import time
from urllib2 import urlopen

import yaml


TIMEOUT = 15


def _bitaps(address,
            satoshis,
            time_window):
    """
    Trying to make this modular so we can use multiple APIs if needed, but
    in general bitaps seems to be pretty reliable.

    I think this returns 100 items at most, so throughput is largely dictated
    by that.
    """
    url = 'https://bitaps.com/api/address/transactions/{}/0/received/all'
    url = url.format(address)
    http_return = urlopen(url, timeout=TIMEOUT)
    transactions = yaml.safe_load(http_return.read())
    now = int(time())
    earliest = now - time_window
    latest = now + time_window
    for transaction in transactions:
        timestamp = transaction[0]
        status = transaction[4]
        tx_satoshis = transaction[7]
        # Transactions come to us in latest first format. As soon as we
        # are out of the time range, we bail out.
        if timestamp > latest:
            return False
        if timestamp < earliest:
            return False
        if tx_satoshis == satoshis:
            if status != 'invalid':
                return True
    # If nothing matches...
    return False


def payment(address,
            satoshis,
            unique,
            satoshi_security=10000,
            time_window=300):
    """
    Accepts a payment.

    unique is something that you associate with the particular payment.
    Hopefully, a UUID. If there is any risk of the unique being captured by
    an attacker in the payment window, you may wish to add a salt to the
    unique.  Like: unique=uuid+salt. salt would be some long secure string
    that you keep safe.  If you change your salt, you will break active
    payments.

    satoshi_security will tend to give you 50% of its value in extra payment.
    Perhaps, users may also not want to pay that much. It's a number, 0-X, of
    padding satoshis that help prevent cases where a malicious user may detect
    a payment, then try to steal what was paid for before the good user gets
    it.

    time_window is a window in seconds, plus or minus, that we allow
    transactions from. This, combined with satoshi_security, help improve
    potential throughput. Except, the lower the number the more throughput we
    have before we start having collisions. Clock sync is important here! Not
    all API clocks are in sync, either!

    Returns:
    satoshis which is the total amount that needs to be paid.
    status True/False, if payment has been finished.

    If you get a True, move on and do something. That status
    doesn't last long. Don't rely on this for state tracking.
    """
    if satoshi_security != 0:
        # Deterministically generate our padding.
        satoshi_padding = int(md5(unique).hexdigest(), 16) % satoshi_security
        satoshi_padding = int(satoshi_padding)  # Strip off L on end.
    else:
        satoshi_padding = 0
    # If you tend to have fixed rate prices, this makes the number more
    # unique and thus harder to predict.
    satoshis = satoshis + satoshi_padding
    bitcoinacceptor_payment = namedtuple('bitcoinacceptor_payment',
                                         ['satoshis'
                                          'status'])
    bitcoinacceptor_payment.satoshis = satoshis
    bitcoinacceptor_payment.status = _bitaps(address, satoshis, time_window)
    return bitcoinacceptor_payment
