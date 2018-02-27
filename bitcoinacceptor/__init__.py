"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Or Bitcoin Cash!

Released into the public domain.
"""

import logging
from collections import namedtuple
from hashlib import md5
from time import strftime, gmtime, time

import bit
import bitcash
import requests


MAX_CONFIRMATIONS = 6
FIAT_TICKER = 'USD'
# Ideally, this should be dynamic and be based on economy TX fee
# recommendations per input.
SATOSHI_FLOOR = 10000


def fiat_per_coin(currency):
    """
    Returns the standard ticker rate of fiat per coin
    rate. For example, 10,000 if Bitcoin to USD, $1,200
    if Bitcoin Cash to USD. (Approximation at the time
    of this comment)

    'currency' is the cryptocurrency, not the fiat.
    """
    def _bitcoinaverage_time_offset(offset=0):
        return strftime('%Y-%m-%d %H:00:00', gmtime(time() - offset))

    ticker = currency.upper()

    # No try/except, we want to break badly if this breaks.
    url = 'https://apiv2.bitcoinaverage.com/indices/global/history/{}{}'\
          '?period=daily&format=json'.format(ticker, FIAT_TICKER)
    request = requests.get(url, timeout=20)
    # Throw an error is something is amiss.
    request.raise_for_status()
    price_index = request.json()
    first_price = None
    second_price = None
    # This is a list so we have to iterate.
    for price_dict in price_index:
        if price_dict['time'] == _bitcoinaverage_time_offset(3600):
            first_price = price_dict['average']
        elif price_dict['time'] == _bitcoinaverage_time_offset(7200):
            second_price = price_dict['average']
            if first_price is not None:
                break
            else:
                logging.debug('Got second price before first price?')
    if first_price is None or second_price is None:
        raise Exception('Unable to extract price at time.')
    return first_price, second_price


# FIXME: This won't work when the price is 100x. Need to switch to floating
# point then.
def satoshis_per_cent(currency='btc',
                      first_price=None,
                      second_price=None):
    """
    Returns "new" and "old" cents.
    This is designed so you don't get crossover gaps with lost payments.
    """
    if first_price is None and second_price is None:
        first_price, second_price = fiat_per_coin(currency)

    def _convert_to_satoshi_per_cent(btcusd):
        return int((1 / btcusd * 100000000 / 100))

    satoshis_per_cent_list = [_convert_to_satoshi_per_cent(first_price),
                              _convert_to_satoshi_per_cent(second_price)]

    return satoshis_per_cent_list


def _unspents(address,
              satoshis_to_try,
              unique,
              currency='btc'):
    """
    Expects a sorted list of unspents.
    """
    if currency == 'btc':
        our_bit = bit
    elif currency == 'bch':
        our_bit = bitcash
    else:
        raise ValueError('currency must be one of: btc, bch')

    if isinstance(satoshis_to_try, int):
        satoshis_to_try = [satoshis_to_try]

    unspents = our_bit.network.NetworkAPI.get_unspent(address)
    for unspent in unspents:
        # Bail out if we go back more than 6.
        if unspent.confirmations > MAX_CONFIRMATIONS:
            break
        for satoshis in satoshis_to_try:
            paid_satoshis = _satoshi_security_code(unique)
            paid_satoshis += satoshis
            if unspent.amount == paid_satoshis:
                return (unspent.txid, unspent.amount)
    # If nothing matches...
    now_satoshis = satoshis_to_try[0] + _satoshi_security_code(unique)
    return (False, now_satoshis)


def _satoshi_security_code(unique,
                           attempt=0,
                           satoshi_security=1000):
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
            currency='btc'):
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
    a payment, then attempt to steal what was paid for before the good user
    gets it.

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
                               currency)
    bitcoinacceptor_payment.txid = txid
    bitcoinacceptor_payment.satoshis = satoshis
    return bitcoinacceptor_payment


def fiat_payment(address,
                 cents,
                 unique,
                 currency='btc',
                 first_price=None,
                 second_price=None):
    """
    Should have been named fiat_denominated_payment()

    Tries to accept a payment denominated in US cents.
    """
    first_cents, second_cents = satoshis_per_cent(currency,
                                                  first_price,
                                                  second_price)
    first_satoshis = first_cents * cents
    second_satoshis = second_cents * cents

    # Minimum accepted payment on the network is roughly 10,000
    # Some clients won't even let you send that little.
    # If we optimize this to skip this from happening twice
    # there is a risk of skipping an old/crossover payment.
    # This is because the price might drop suddenly, floor
    # doesn't apply, then we skip the older, higher price
    # which the client paid at.
    if first_satoshis < SATOSHI_FLOOR:
        first_satoshis = SATOSHI_FLOOR
    if second_satoshis < SATOSHI_FLOOR:
        second_satoshis = SATOSHI_FLOOR

    if first_satoshis == second_satoshis:
        satoshi_list = [first_satoshis]
    else:
        satoshi_list = [first_satoshis, second_satoshis]

    return payment(address,
                   satoshi_list,
                   unique,
                   currency)
