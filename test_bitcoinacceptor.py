from mock import patch

import bitcoinacceptor
import pytest
from bit.network.meta import Unspent

# These are a bit of a mess, not consistent through all currencies. Should be redone.

# This is a testnet Monero RPC wallet service for tests.
# You can also just use localhost and run your own.
monero_rpc = {"host": "ssjulcg5dmz7itglkx2bdms7cdjfxtd2gjfqmooadehcbziogq7bvwqd.onion",
              "port": 6799,
              "user": "demouser",
              "password": "demopassword"}


def test_validate_currency():
    assert bitcoinacceptor.validate_currency('btc') is True
    assert bitcoinacceptor.validate_currency('bch') is True
    assert bitcoinacceptor.validate_currency('bsv') is True
    assert bitcoinacceptor.validate_currency('xmr') is True
    with pytest.raises(ValueError):
        bitcoinacceptor.validate_currency('eth')


def test_security_code():
    code = bitcoinacceptor._satoshi_security_code('cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                                  0,
                                                  1000)
    assert code == 721
    code = bitcoinacceptor._satoshi_security_code('cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                                  1,
                                                  1000)
    assert code == 991


def test_monero_security_code():
    codes = bitcoinacceptor._monero_security_code('foo')
    # Looks like we can't do 64 bits of codes...
    # assert codes[0] == 12512379
    # assert codes[1] == 245625085
    assert codes[0] == 0
    assert codes[1] == 190
    codes = bitcoinacceptor._monero_security_code('foo2')
    assert codes[0] == 0
    assert codes[1] == 143


def test_fiat_per_coin():
    first_price_btc, _ = bitcoinacceptor.fiat_per_coin('btc')
    first_price_bch, _ = bitcoinacceptor.fiat_per_coin('bch')
    first_price_bsv, _ = bitcoinacceptor.fiat_per_coin('bsv')
    first_price_xmr, _ = bitcoinacceptor.fiat_per_coin('xmr')
    assert first_price_btc > first_price_bch
    assert first_price_bch > first_price_bsv
    assert first_price_bsv > first_price_xmr


def test_satoshis_per_cent():
    first, second = bitcoinacceptor.satoshis_per_cent('btc', 10000, 5000)
    assert first == 100
    assert second == 200
    first, second = bitcoinacceptor.satoshis_per_cent('bch', 100000, 50000)
    assert int(first) == 10
    assert int(second) == 20
    first, second = bitcoinacceptor.satoshis_per_cent('bsv', 100000, 50000)
    assert int(first) == 10
    assert int(second) == 20


def test_fiat_payment_basic():
    cents = 100
    payment = bitcoinacceptor.fiat_payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'btc',
                                           10000,
                                           10001)
    assert payment.satoshis == 10721
    assert payment.uri == 'bitcoin:16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq?amount=0.00010721'
    payment = bitcoinacceptor.fiat_payment('bitcoincash:qqwmyjjplsqwltkcgyeagqpjspaaksz3qggnfug7gy',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bch',
                                           1000,
                                           1001)
    assert payment.satoshis == 100721
    payment = bitcoinacceptor.fiat_payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bsv',
                                           1000,
                                           1001)
    assert payment.satoshis == 100721
    payment = bitcoinacceptor.fiat_payment(None,
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'xmr',
                                           1000,
                                           1001,
                                           monero_rpc=monero_rpc)
    assert payment.uri == 'monero:Bec1iqCvhkEEm4EsnztUyo71gApFLpDyD44vHg1GHg8DHAEyeAVkDhV5StqRw8FCL5RrFwoDbntgT6wUgX4etYrMA8Bm7Ey?tx_amount=0.001000000000'
    assert payment.satoshis == 1000000000

def test_real_payment_monero():
    payment = bitcoinacceptor.payment(address=None,
                                      satoshis_to_try=[11078414401, 5],
                                      unique='a70f3f796e7b88fb9a7619cc10dd6a7739ca1e0a183bd2ac888f655af98c444d',
                                      currency='xmr',
                                      txids=[],
                                      monero_rpc=monero_rpc)
    assert payment.uri == 'monero:Be1BiC1kFfmUbCWGALpwKw2w8ZJL4aYuz1jNXEHM5LSRaAAHRzJwPHD8LBax3gnnJ2g9FhG9eQhCF7gbX9sVAMjbTgQgAqy?tx_amount=0.011078414401'
    assert payment.satoshis == 11078414401
    assert payment.txid == '42f612c0d44fca305de41aa00c3bd704297bad9d5c9350cacfd992bd92aa4548'
    # txid already paid for
    payment = bitcoinacceptor.payment(address=None,
                                      satoshis_to_try=[11078414401, 5],
                                      unique='a70f3f796e7b88fb9a7619cc10dd6a7739ca1e0a183bd2ac888f655af98c444d',
                                      currency='xmr',
                                      txids=['42f612c0d44fca305de41aa00c3bd704297bad9d5c9350cacfd992bd92aa4548'],
                                      monero_rpc=monero_rpc)
    assert payment.uri == 'monero:Be1BiC1kFfmUbCWGALpwKw2w8ZJL4aYuz1jNXEHM5LSRaAAHRzJwPHD8LBax3gnnJ2g9FhG9eQhCF7gbX9sVAMjbTgQgAqy?tx_amount=0.011078414401'
    assert payment.satoshis == 11078414401
    assert payment.txid == False
    # Opposite order, has been paid.
    payment = bitcoinacceptor.payment(address=None,
                                      satoshis_to_try=[5, 11078414401],
                                      unique='a70f3f796e7b88fb9a7619cc10dd6a7739ca1e0a183bd2ac888f655af98c444d',
                                      currency='xmr',
                                      txids=[],
                                      monero_rpc=monero_rpc)
    assert payment.uri == 'monero:Be1BiC1kFfmUbCWGALpwKw2w8ZJL4aYuz1jNXEHM5LSRaAAHRzJwPHD8LBax3gnnJ2g9FhG9eQhCF7gbX9sVAMjbTgQgAqy?tx_amount=0.000000000005'
    assert payment.satoshis == 5
    assert payment.txid == '42f612c0d44fca305de41aa00c3bd704297bad9d5c9350cacfd992bd92aa4548'
    # No satoshis has been paid for this one.
    payment = bitcoinacceptor.payment(address=None,
                                      satoshis_to_try=[91078414401,5],
                                      unique='a70f3f796e7b88fb9a7619cc10dd6a7739ca1e0a183bd2ac888f655af98c444d',
                                      currency='xmr',
                                      txids=[],
                                      monero_rpc=monero_rpc)
    assert payment.uri == 'monero:Be1BiC1kFfmUbCWGALpwKw2w8ZJL4aYuz1jNXEHM5LSRaAAHRzJwPHD8LBax3gnnJ2g9FhG9eQhCF7gbX9sVAMjbTgQgAqy?tx_amount=0.091078414401'
    assert payment.satoshis == 91078414401
    assert payment.txid == False


@patch('bitcoinacceptor.bit.network.NetworkAPI.get_unspent')
def test_determinism(mock_get_unspent):
    test_data = [Unspent(amount=10721, confirmations=0, script='script', txid='txid1', txindex=1),
                 Unspent(amount=10721, confirmations=1, script='script', txid='txid2', txindex=1),
                 Unspent(amount=10081, confirmations=2, script='script', txid='txid3', txindex=1),
                 Unspent(amount=10357, confirmations=7, script='script', txid='txid4', txindex=1)]
    mock_get_unspent.return_value = test_data
    satoshis = 10000
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid == 'txid1'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      txids=['txid1'])
    assert payment.txid == 'txid2'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'uuid')
    assert payment.txid == 'txid3'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'newuuid')
    # Should be 10357, but 7 confirmations so we ignore it.
    assert payment.txid is False
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'yetanotheruuid')
    assert payment.satoshis == 10836


@patch('bitcoinacceptor.bitcash.network.NetworkAPI.get_unspent')
def test_determinism_bch(mock_get_unspent):
    test_data = [Unspent(amount=10721, confirmations=0, script='script', txid='txid1', txindex=1),
                 Unspent(amount=10721, confirmations=1, script='script', txid='txid2', txindex=1),
                 Unspent(amount=10081, confirmations=2, script='script', txid='txid3', txindex=1),
                 Unspent(amount=10357, confirmations=7, script='script', txid='txid4', txindex=1)]
    mock_get_unspent.return_value = test_data
    satoshis = 10000
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      'bch')
    assert payment.txid == 'txid1'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      'bch',
                                      txids=['txid1'])
    assert payment.txid == 'txid2'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'uuid',
                                      'bch')
    assert payment.txid == 'txid3'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'newuuid',
                                      'bch')
    # Should be 10357, but 7 confirmations so we ignore it.
    assert payment.txid is False
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'yetanotheruuid',
                                      'bch')
    assert payment.satoshis == 10836


def test_nonematching():
    satoshis = 10000
    payment = bitcoinacceptor.payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 10721
    assert payment.txid is False


def test_empty_address():
    satoshis = 10000
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 10721
    assert payment.txid is False


def test_cents():
    btc_satoshis, _ = bitcoinacceptor.satoshis_per_cent('btc')
    bch_satoshis, _ = bitcoinacceptor.satoshis_per_cent('bch')
    assert bch_satoshis > btc_satoshis
    bsv_satoshis, _ = bitcoinacceptor.satoshis_per_cent('bsv')
    assert bsv_satoshis > bch_satoshis


def test_nonematching_fiat():
    """
    Test addresses that have had transactions, but none are what we are looking for.
    """
    cents = 100
    payment = bitcoinacceptor.fiat_payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'btc')
    assert payment.txid is False
    payment = bitcoinacceptor.fiat_payment('bitcoincash:qq9gh20y2vur63tpe0xa5dh90zwzsuxagyhp7pfuv3',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bch')
    assert payment.txid is False
    payment = bitcoinacceptor.fiat_payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bsv')
    assert payment.txid is False


def test_empty_address_fiat():
    cents = 100
    payment = bitcoinacceptor.fiat_payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'btc')
    assert payment.txid is False
    payment = bitcoinacceptor.fiat_payment('bitcoincash:qpkp8gwqen8ydlmj5ajuqvd7xt8kj8rpay029ef9z9',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bch')
    assert payment.txid is False
    payment = bitcoinacceptor.fiat_payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                           cents,
                                           'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                           'bsv')
    assert payment.txid is False
