"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Released into the public domain.
"""

from collections import namedtuple
from hashlib import md5
from time import time
from urllib2 import urlopen, HTTPError

import yaml


TIMEOUT = 15


def _bitaps(address,
            satoshis,
            earlier_satoshis,
            time_window):
    """
    Trying to make this modular so we can use multiple APIs if needed, but
    in general bitaps seems to be pretty reliable.

    I think this returns 100 items at most, so throughput is largely dictated
    by that and your poll rate.
    """
    # Determine the current time first, in case the API query is slow.
    now = int(time())
    url = 'https://bitaps.com/api/address/transactions/{}/0/received/all'
    url = url.format(address)
    # bitaps returns 404 on addresses with no transactions. urlopen
    # throws an exception when that's the case.
    # This could be much better.
    try:
        http_return = urlopen(url, timeout=TIMEOUT)
        transactions = yaml.safe_load(http_return.read())
    except HTTPError:
        return False
    earliest = now - time_window
    latest = now + time_window
    for transaction in transactions:
        timestamp = transaction[0]
        txid = transaction[1]
        status = transaction[4]
        # tx as in transaction, not as in transmitted.
        tx_satoshis = transaction[7]
        # Transactions come to us in latest first format. As soon as we
        # are out of the time range, we bail out.
        if timestamp > latest:
            return False
        if timestamp < earliest:
            return False
        if status != 'invalid':
            if tx_satoshis == satoshis:
                    return txid
            if tx_satoshis == earlier_satoshis:
                    return txid
    # If nothing matches...
    return False


def _satoshi_security_code(unique,
                           centiepoch,
                           satoshi_security):
    """
    Returns the "Satoshi security code" given the circumstances.
    We use MD5 because it's pretty fast. We strip off so many bits
    of entropy that SHA probably wouldn't matter.

    But I'm no cryptographer, so take that with a grain of salt.
    Our possible returns are 0 - satoshi_security. Pretty narrow
    range.
    """
    # Make centiepoch a string so we can append it to unique, which is
    # a string.
    centiepoch = str(centiepoch)
    # Get our base MD5 sum, in integer format.
    security_code = int(md5(unique + centiepoch).hexdigest(), 16)
    # Modulo down to satoshi_security levels.
    security_code = security_code % satoshi_security
    # This gets rid of the L on the end, if any.
    security_code = int(security_code)
    return security_code


def payment(address,
            satoshis,
            unique,
            satoshi_security=10000,
            time_window=120):
    """
    Accepts a payment.

    unique is something that you associate with the particular payment.
    Hopefully, a UUID. If there is any risk of the unique being captured by
    an attacker in the payment window, you may wish to add a salt to the
    unique. Like: unique=uuid+salt. salt would be some long secure string
    that you keep safe. If you change your salt, you will break active
    payments.

    satoshi_security will tend to give you 50% of its value in extra payment.
    Perhaps, users may also not want to pay that much. It's a number, 0-X, of
    padding satoshis that help prevent cases where a malicious user may detect
    a payment, then try to steal what was paid for before the good user gets
    it.

    We have a time modifier for the hash function so that malcious users
    should not as easier be able to precompute uuid to satoshi tables before
    hand to more easily be able to snipe goods from under paying customers.
    Sniping would be defined as making a request to receive the good/service
    after the user has made payment, but before the user has received it.

    time_window is a window in seconds, plus or minus, that we allow
    transactions from. This, combined with satoshi_security, help improve
    potential throughput. Except, the lower the number the more throughput we
    have before we start having collisions. Clock sync is important here! Not
    all API clocks are in sync, either!

    time_window greater than 200 won't really do anything beneficial.

    Returns:
    satoshis which is the total amount that needs to be paid.
    status True/False, if payment has been finished.
    earlier_satoshis which should not be used, except for testing.

    If you get a True, move on and do something. That status
    doesn't last long. Don't rely on this for state tracking.
    """
    bitcoinacceptor_payment = namedtuple('bitcoinacceptor_payment',
                                         ['satoshis',
                                          'earlier_satoshis',
                                          'txid'])
    # Deterministically generate our padding.
    now = int(time()) / 100
    earlier = now - 1
    now_satoshis = satoshis + _satoshi_security_code(unique,
                                                     now,
                                                     satoshi_security)
    earlier_satoshis = satoshis + _satoshi_security_code(unique,
                                                         earlier,
                                                         satoshi_security)
    bitcoinacceptor_payment.txid = _bitaps(address,
                                           now_satoshis,
                                           earlier_satoshis,
                                           time_window)
    if bitcoinacceptor_payment.txid is False:
        bitcoinacceptor_payment.earlier_satoshis = earlier_satoshis
        bitcoinacceptor_payment.satoshis = now_satoshis
    else:
        # Try to help prevent plausible double payment cases.
        bitcoinacceptor_payment.earlier_satoshis = 0
        bitcoinacceptor_payment.satoshis = 0
    return bitcoinacceptor_payment
