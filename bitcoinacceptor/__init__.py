"""
bitcoinacceptor library

Helps you accept Bitcoins without paying to accept Bitcoins.

Or Bitcoin Cash, Bitcoin SV, or Monero!

Released into the public domain.
"""
import logging
from collections import namedtuple
from hashlib import md5, sha1

import bit
import bitcash
import bitsv
import requests
from sporestackv2 import utilities
from monero.wallet import Wallet
from monero.backends.jsonrpc import JSONRPCWallet
from monero.numbers import from_atomic

logging.basicConfig(level=logging.INFO)

# Only for BTC, BCH, and BSV
MIN_CONFIRMATIONS = 1
MAX_CONFIRMATIONS = 6
FIAT_TICKER = 'USD'
# Ideally, this should be dynamic and be based on economy TX fee
# recommendations per input.
SATOSHI_FLOOR = 10000

VALID_CURRENCIES = ('btc', 'bch', 'bsv', 'xmr')

# For Monero's fiat_per_coin
GET_TIMEOUT = 30


def validate_currency(currency):
    msg = 'currency must be one of: {}'.format(VALID_CURRENCIES)
    if currency not in VALID_CURRENCIES:
        raise ValueError(msg)
    return True


def _xmr_to_fiat():
    url = "https://min-api.cryptocompare.com/data/price?fsym=XMR&tsyms=USD"
    request = requests.get(url=url, timeout=GET_TIMEOUT)
    request.raise_for_status()
    request_dict = request.json()
    return request_dict["USD"]


def fiat_per_coin(currency):
    """
    Returns the standard ticker rate of fiat per coin
    rate. For example, 10,000 if Bitcoin to USD, $1,200
    if Bitcoin Cash to USD. (Approximation at the time
    of this comment)

    'currency' is the cryptocurrency, not the fiat.
    """
    validate_currency(currency)
    if currency == 'bch':
        BCH = bitcash.network.rates.BCH
        return float(bitcash.network.rates.satoshi_to_currency(BCH, 'usd'))
    elif currency == 'bsv':
        BSV = bitsv.network.rates.BSV
        return float(bitsv.network.rates.satoshi_to_currency(BSV, 'usd'))
    elif currency == 'btc':
        BTC = bit.network.rates.BTC
        return float(bit.network.rates.satoshi_to_currency(BTC, 'usd'))
    elif currency == 'xmr':
        return _xmr_to_fiat()


def satoshis_per_cent(currency='btc',
                      first_price=None,
                      second_price=None):
    """
    Returns "new" and "old" cents.
    This is designed so you don't get crossover gaps with lost payments.

    For Monero, returns piconero per cent.
    """
    if first_price is None and second_price is None:
        first_price = fiat_per_coin(currency)
        second_price = first_price

    if currency == 'xmr':
        # 12 decimal places for piconero.
        def _convert_to_satoshi_per_cent(crypto_usd):
            return 1 / crypto_usd * 1000000000000 / 100
    else:
        # 8 decimal places for satoshis.
        def _convert_to_satoshi_per_cent(crypto_usd):
            return 1 / crypto_usd * 100000000 / 100

    satoshis_per_cent_list = [_convert_to_satoshi_per_cent(first_price),
                              _convert_to_satoshi_per_cent(second_price)]

    return satoshis_per_cent_list


def _monero_security_code(unique):
    """
    So, there's this:
    https://monero.stackexchange.com/questions/10184/

    Monero only looks ahead 200 addresses by default. I was hoping for 64 bits
    worth of addresses.
    I guess that's too much.

    For now, let's just do 200.
    """
    hashable = bytes(unique, 'utf-8')
    unique_hash = sha1(hashable).hexdigest()
    # each part is 32 bits, so take that much.
    # security_code_major = int(unique_hash[0:7], 16)
    # security_code_minor = int(unique_hash[8:15], 16)
    security_code_major = 0
    # 0:1 wasn't giving me 0-255??? Weird.
    # 199 just in case it's 0-199 and not 0-200.
    security_code_minor = int(unique_hash[0:3], 16) % 199
    return (security_code_major, security_code_minor)


def _monero_unspents(unique,
                     piconero_to_try,
                     txids,
                     host,
                     port,
                     user,
                     password):
    """
    Get incoming transactions from Monero RPC and see if we have a winner.

    unique is used to get us a specific address for the unique.

    No satoshi security here since we have unique addresses.
    """
    proxy_url = None
    if host.endswith('.onion'):
        proxy_url = 'socks5h://127.0.0.1:9050'
    w = Wallet(JSONRPCWallet(host=host,
                             port=port,
                             user=user,
                             password=password,
                             proxy_url=proxy_url))
    security_code_major, security_code_minor = _monero_security_code(unique)
    unique_address = w.get_address(security_code_major, security_code_minor)
    return_address = str(unique_address)
    # Allow last 100 blocks. (200 minutes average)
    minimum_height = w.height() - 100
    incoming_tx = w.incoming(local_address=unique_address,
                             min_height=minimum_height,
                             confirmed=True,
                             unconfirmed=False)
    for tx in incoming_tx:
        if tx.transaction.hash not in txids:
            for piconero in piconero_to_try:
                if from_atomic(piconero) == tx.amount:
                    return (return_address, tx.transaction.hash)
    # address, txid
    return (return_address, False)


def _unspents(address,
              satoshis_to_try,
              unique,
              currency='btc',
              txids=[],
              monero_rpc=None,
              min_confirmations=MIN_CONFIRMATIONS):
    """
    txids is an optional list of txids that you have already accepted
    payment for.

    Unspents for Bitcoin, Bitcoin Cash, or Bitcoin SV.
    """
    if currency == 'btc':
        our_bit = bit
    elif currency == 'bch':
        our_bit = bitcash
    elif currency == 'bsv':
        our_bit = bitsv
    else:
        raise ValueError('_unspents is only for btc, bch, and bsv.')

    if isinstance(satoshis_to_try, int):
        satoshis_to_try = [satoshis_to_try]
    # bitsv has switched to get_unspents(). This is kind of hacky.
    # https://github.com/AustEcon/bitsv/issues/40
    if 'get_unspents' in dir(our_bit.network.NetworkAPI):
        unspents = our_bit.network.NetworkAPI('main').get_unspents(address)
    else:
        unspents = our_bit.network.NetworkAPI.get_unspent(address)
    for unspent in unspents:
        # By doing continue instead of break, it can be slower but we should
        # be able to work with unsorted unspents.
        if unspent.confirmations > MAX_CONFIRMATIONS:
            continue
        if unspent.confirmations < min_confirmations:
            continue
        for satoshis in satoshis_to_try:
            paid_satoshis = _satoshi_security_code(unique)
            paid_satoshis += satoshis
            if unspent.amount == paid_satoshis:
                if unspent.txid not in txids:
                    return (unspent.txid, unspent.amount)
    # If nothing matches...
    now_satoshis = satoshis_to_try[0] + _satoshi_security_code(unique)
    # txid, satoshis
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
            satoshis_to_try,
            unique,
            currency='btc',
            txids=[],
            monero_rpc=None,
            min_confirmations=MIN_CONFIRMATIONS):
    """
    Accepts a payment.

    txids is an optional list of txids that you have already accepted
    payment for.

    address should be None for Monero.

    **These comments are be very inaccurate and out of date.**

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
    validate_currency(currency)
    bitcoinacceptor_payment = namedtuple('bitcoinacceptor_payment',
                                         ['satoshis',
                                          'txid',
                                          'uri'])

    if currency == 'xmr':
        if address is not None:
            raise ValueError('address must be none when using Monero (XMR)')
        if not isinstance(monero_rpc, dict):
            msg = 'With currency set to xmr, monero_rpc must be a dict with '
            msg += 'host, port, user, password'
            raise ValueError(msg)
        address, txid = _monero_unspents(unique=unique,
                                         piconero_to_try=satoshis_to_try,
                                         txids=txids,
                                         host=monero_rpc['host'],
                                         port=monero_rpc['port'],
                                         user=monero_rpc['user'],
                                         password=monero_rpc['password'])
        satoshis = satoshis_to_try[0]
    else:
        txid, satoshis = _unspents(address,
                                   satoshis_to_try,
                                   unique,
                                   currency,
                                   txids,
                                   monero_rpc,
                                   min_confirmations=min_confirmations)

    bitcoinacceptor_payment.txid = txid
    bitcoinacceptor_payment.satoshis = satoshis
    bitcoinacceptor_payment.uri = utilities.payment_to_uri(address,
                                                           currency,
                                                           satoshis)
    return bitcoinacceptor_payment


def fiat_payment(address,
                 cents,
                 unique,
                 currency='btc',
                 first_price=None,
                 second_price=None,
                 txids=[],
                 monero_rpc=None,
                 min_confirmations=MIN_CONFIRMATIONS):
    """
    Should have been named fiat_denominated_payment()

    Tries to accept a payment denominated in US cents.

    address should be None for Monero.
    """
    validate_currency(currency)
    first_cents, second_cents = satoshis_per_cent(currency,
                                                  first_price,
                                                  second_price)
    first_satoshis = int(first_cents * cents)
    second_satoshis = int(second_cents * cents)

    # Only require 8 digits of precision.
    if currency == 'xmr':
        first_satoshis = (first_satoshis // 10000) * 10000
        second_satoshis = (second_satoshis // 10000) * 10000

    # Minimum accepted payment on the network is roughly 10,000
    # Some clients won't even let you send that little.
    # If we optimize this to skip this from happening twice
    # there is a risk of skipping an old/crossover payment.
    # This is because the price might drop suddenly, floor
    # doesn't apply, then we skip the older, higher price
    # which the client paid at.
    #
    # No idea what the floor is for Monero.
    if first_satoshis < SATOSHI_FLOOR:
        first_satoshis = SATOSHI_FLOOR
    if second_satoshis < SATOSHI_FLOOR:
        second_satoshis = SATOSHI_FLOOR

    if first_satoshis == second_satoshis:
        satoshis_to_try = [first_satoshis]
    else:
        satoshis_to_try = [first_satoshis, second_satoshis]

    return payment(address,
                   satoshis_to_try,
                   unique,
                   currency,
                   txids,
                   monero_rpc,
                   min_confirmations)
