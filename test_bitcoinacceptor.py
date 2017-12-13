from mock import patch
from time import time

import bitcoinacceptor
from bit.network.meta import Unspent


def test_security_code():
    code = bitcoinacceptor._satoshi_security_code('cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                                  0,
                                                  1000)
    assert code == 721
    code = bitcoinacceptor._satoshi_security_code('cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                                  1,
                                                  1000)
    assert code == 991


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
                                      'uuid')
    assert payment.txid == 'txid3'
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'newuuid')
    # Should be 10357, but 7 confirmations so we ignore it.
    assert payment.txid == False
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'yetanotheruuid')
    assert payment.satoshis == 10836


def test_nonematching():
    satoshis = 10000
    payment = bitcoinacceptor.payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 10721
    assert payment.txid == False


def test_empty_address():
    satoshis = 10000
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 10721
    assert payment.txid == False


# Will never confirm, so this may just work.
def test_foreverzeroconf():
    satoshis = 1001
    payment = bitcoinacceptor.payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                      satoshis,
                                      '747')
    assert payment.satoshis == 2000
    assert payment.txid == 'a95eef020a803c1bf5af59be7fea51140a33ecf502a381d06a50e3a7ea679ce3'


def test_cents():
    btc_satoshis, _ = bitcoinacceptor.satoshis_per_cent('btc')
    bch_satoshis, _ = bitcoinacceptor.satoshis_per_cent('bch')
    assert bch_satoshis > btc_satoshis


def test_nonematching_fiat():
    cents = 100
    for currency in ['btc', 'bch']:
        payment = bitcoinacceptor.fiat_payment('1coinNJHaeuAN5io49RtDfryxFLWnKR15',
                                               cents,
                                               'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                               currency)
        print(payment.satoshis)
        assert payment.txid == False


def test_empty_address_fiat():
    cents = 100
    for currency in ['btc', 'bch']:
        payment = bitcoinacceptor.fiat_payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                               cents,
                                               'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                               currency)
        assert payment.txid == False
