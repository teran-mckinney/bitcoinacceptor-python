"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Released into the public domain.
"""

from collections import namedtuple
from hashlib import md5
from time import time

# Python 2 backwards compatibility.
try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

import yaml


TIMEOUT = 15


def _bitaps(address,
            satoshis,
            unique,
            satoshi_security):
    """
    Trying to make this modular so we can use multiple APIs if needed, but
    in general bitaps seems to be pretty reliable.

    I think this returns 100 items at most, so throughput is largely dictated
    by that and your poll rate.
    """
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
    now = int(time())
    earliest = now - 3600
    # // in Python 3 is like / in Python 2.
    period_now = now // 100
    for transaction in transactions:
        timestamp = transaction[0]
        txid = transaction[1]
        status = transaction[4]
        # tx as in transaction, not as in transmitted.
        tx_satoshis = transaction[7]
        # Transactions come to us in latest first format.
        # Bail out if we go back more than a day.
        if timestamp < earliest:
            break
        if status != 'invalid':
            # Try an hour's worth of possible satoshis for the hash.
            # The code using this needs to be tracking txid state anyway.
            # Given the sorting, this should always work in our favor.
            # range returns 0 - 35 with range(36).
            # I wonder how slow this will be.
            # Would use xrange but need range() for Python 3 compatibility.
            for possible_satoshis in range(36):
                period = period_now - possible_satoshis
                paid_satoshis = _satoshi_security_code(unique,
                                                       period,
                                                       satoshi_security)
                paid_satoshis += satoshis
                if tx_satoshis == paid_satoshis:
                    return (txid, paid_satoshis)
    # If nothing matches...
    now_satoshis = satoshis + _satoshi_security_code(unique,
                                                     period_now,
                                                     satoshi_security)
    return (False, now_satoshis)


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
    # Python 3, 2 support.
    try:
        hashable = bytes(unique + centiepoch, 'utf-8')
    except:
        hashable = unique + centiepoch
    # Get our base MD5 sum, in integer format.
    security_code = int(md5(hashable).hexdigest(), 16)
    # Modulo down to satoshi_security levels.
    security_code = security_code % satoshi_security
    # This gets rid of the L on the end, if any.
    security_code = int(security_code)
    return security_code


def payment(address,
            satoshis,
            unique,
            satoshi_security=10000):
    """
    Accepts a payment.

    These comments may be very inaccurate and out of date.

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

    Returns:
    satoshis which is the total amount that needs to be paid.
    status True/False, if payment has been finished.
    earlier_satoshis which should not be used, except for testing.

    If you get a txid, save it for at least 86400 seconds. And compare what
    this returns to your database to be certain.

    Theoretical maximum payment window is 86400 seconds. But if other users
    are transacting in that window, it's lower.
    """
    bitcoinacceptor_payment = namedtuple('bitcoinacceptor_payment',
                                         ['satoshis',
                                          'txid'])
    txid, satoshis = _bitaps(address,
                             satoshis,
                             unique,
                             satoshi_security)
    bitcoinacceptor_payment.txid = txid
    bitcoinacceptor_payment.satoshis = satoshis
    return bitcoinacceptor_payment
