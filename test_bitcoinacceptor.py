from mock import patch

import bitcoinacceptor


def test_payment_zero_satoshi_security():
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      satoshi_security=0)
    assert satoshis == payment.satoshis


def test_determinism():
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 14322


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_okay(mock_urlopen, mock_time):
    test_data = '[[1000, "txid", "", "received", "confirmed", 0, 0, 14322]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1000
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid == 'txid'


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_too_late(mock_urlopen, mock_time):
    test_data = '[[1000, "txid", "", "received", "confirmed", 0, 0, 14322]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1031
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      time_window=30)
    assert payment.txid is False


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_too_early(mock_urlopen, mock_time):
    test_data = '[[1000, "txid", "", "received", "confirmed", 0, 0, 14322]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 969
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                      time_window=30)
    assert payment.txid is False


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_status_invalid(mock_urlopen, mock_time):
    test_data = '[[1000, "txid", "", "received", "invalid", 0, 0, 14322]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1000
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid is False
