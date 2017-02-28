from mock import patch
from time import time

import bitcoinacceptor


def test_security_code():
    centiepoch = 14859827
    code = bitcoinacceptor._satoshi_security_code('cab41de5-ad64-446d-9ab4-6dc794162bfc',
                                                  centiepoch,
                                                  10000)
    assert code == 5838


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_determinism(mock_urlopen, mock_time):
    test_data = '[[1485982756, "txid", "", "received", "confirmed", 0, 0, 18183]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1485982756
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid == 'txid'


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_determinism_previous_payment(mock_urlopen, mock_time):
    test_data = '[[1485982756, "txid", "", "received", "confirmed", 0, 0, 17728]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1485982756
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid == 'txid'


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_newer_txid_preference(mock_urlopen, mock_time):
    """
    Test preference for first entry to second.
    """
    test = '[[1485982756, "newtxid", "", "received", "confirmed", 0, 0, 17728], ' \
           '[1485982756, "oldtxid", "", "received", "confirmed", 0, 0, 17728]]'
    mock_urlopen.return_value.read.return_value = test
    mock_time.return_value = 1485982756
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.txid == 'newtxid'


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_too_late(mock_urlopen, mock_time):
    test_data = '[[1485982787, "txid", "", "received", "confirmed", 0, 0, 18183]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 2485982787
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    print(payment.satoshis)
    assert payment.satoshis == 16420
    assert payment.txid is False


@patch('bitcoinacceptor.time')
@patch('bitcoinacceptor.urlopen')
def test_status_invalid(mock_urlopen, mock_time):
    test_data = '[[1485982756, "txid", "", "received", "invalid", 0, 0, 18183]]'
    mock_urlopen.return_value.read.return_value = test_data
    mock_time.return_value = 1485982756
    satoshis = 12345
    payment = bitcoinacceptor.payment('16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq',
                                      satoshis,
                                      'cab41de5-ad64-446d-9ab4-6dc794162bfc')
    assert payment.satoshis == 18183
    assert payment.txid is False


@patch('bitcoinacceptor.time')
def test_real_payment(mock_time):
    """
    Real payment that I made.
    """
    mock_time.return_value = 1485991002
    payment = bitcoinacceptor.payment('13tsssFsomxTqJjgz3NQAZvLRuW2LTDmcP',
                                      10000,
                                      'unique')
    assert payment.satoshis == 15512
    txid = 'a12039091ad74f30fda38520574c87c76c5a615224b2ee0db56d4fb62794e5fa'
    assert payment.txid == txid


def test_real_false_payment():
    """
    Real test for payment that never happened.
    """
    payment = bitcoinacceptor.payment('13tsssFsomxTqJjgz3NQAZvLRuW2LTDmcP',
                                      10000,
                                      'no payment')
    assert payment.txid == False


def test_real_old_payment():
    """
    Real test for payment that's just too old.
    """
    payment = bitcoinacceptor.payment('13tsssFsomxTqJjgz3NQAZvLRuW2LTDmcP',
                                      10000,
                                      'unique')
    assert payment.txid == False
