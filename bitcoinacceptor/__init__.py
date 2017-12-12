"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Released into the public domain.
"""

from collections import namedtuple
from hashlib import md5

import bit


MAX_CONFIRMATIONS = 6


def _unspents(address,
              satoshis,
              unique,
              satoshi_security):
    """
    Moved from bitaps to bit's unspents.
    Expects a sorted list of unspents.
    """
    unspents = bit.network.NetworkAPI.get_unspent(address)
    for unspent in unspents:
        # Bail out if we go back more than 6.
        if unspent.confirmations > MAX_CONFIRMATIONS:
            break
        # range returns 0 - 6 with range(7).
        for attempt in range(7):
            paid_satoshis = _satoshi_security_code(unique,
                                                   attempt,
                                                   satoshi_security)
            paid_satoshis += satoshis
            if unspent.amount == paid_satoshis:
                return (unspent.txid, unspent.amount)
    # If nothing matches...
    now_satoshis = satoshis + _satoshi_security_code(unique,
                                                     0,
                                                     satoshi_security)
    return (False, now_satoshis)


def _satoshi_security_code(unique,
                           attempt,
                           satoshi_security):
    """
    Returns the "Satoshi security code" given the circumstances.
    We use MD5 because it's pretty fast. We strip off so many bits
    of entropy that SHA probably wouldn't matter.

    Ok, so SHA-1 is faster than MD5. Should probably use it. Meh.

    But I'm no cryptographer, so take that with a grain of salt.
    Our possible returns are 0 - satoshi_security. Pretty narrow
    range.
    """
    # Make attempt a string so we can append it to unique, which is
    # a string.
    attempt = str(attempt)
    hashable = bytes(unique + attempt, 'utf-8')
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
            satoshi_security=1000):
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
    a payment, then attempt to steal what was paid for before the good user gets
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
    txid, satoshis = _unspents(address,
                               satoshis,
                               unique,
                               satoshi_security)
    bitcoinacceptor_payment.txid = txid
    bitcoinacceptor_payment.satoshis = satoshis
    return bitcoinacceptor_payment
