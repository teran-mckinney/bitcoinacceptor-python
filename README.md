# Installation

* `pip install bitcoinacceptor`

# Testing

* `nosetests`

# Usage

```
import bitcoinacceptor
from time import sleep

# This is only important for roughly time_window / 2.
# Prevents double buys.
transactions = []

hath_spoken = False
while True:
    address = '16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq'
    payment = bitcoinacceptor.payment(address=address, satoshis=10000, unique='random_uuid')
    if payment.txid is False:
        if hath_spoken is False:
            print('Send {} Satoshis to {}'.format(payment.satoshis, address))
            hath_spoken = True
    else:
        if payment.txid not in transactions:
            print(payment.txid)
            print("Here's the product.")
            transactions.append(payment.txid)
            break
    sleep(2)
```

# What it does

The text below may be out of date and unreliable. Read the code and decide if this is right for you. Even the code comments may not be correct.

tl;dr: This is *really* weird. But I think it works in the realm of single digit transaction per second workloads. It's not perfect and it's not totally safe for you or your users, but it may be good enough for most.

Lets you somewhat reliably accept payments to a single Bitcoin address without payment forwarding and what not.

It does this by using time windows and deterministic generation of the last X Satoshis for the payment. By default, it's 10,000 Satoshis in a 300 second window. This means that if you have an item that costs 20,000 Satoshi, the user price may vary from 20,000 to 30,000 Satoshi. When the library says the item is paid, you need to track state. This does not keep state for you. As soon as you get status True, log that somewhere, somehow. This also means that for Y products at the same price, the seconds is roughly your throughput before you start getting collisions.

Potentially, anyway. You'll want to use a high poll rate with this. Probably have the user hitting you every five seconds or sooner. There's attack windows of the poll time where an attacker can try to brute force the unique between payment and polling. If your unique (this is deterministic, afterall) is exposed (like unencrypted on the wire or public in some other way), consider salting it and not disclosing the salt.

You tell them to pay the same address that you pass to bitcoinacceptor.payment(), but be sure to give them payment.satoshis as the amount.

Your clock should be kept in sync. The default time_window of 300 seconds is probably a bit much, but it should work for most low traffic sites.

There's other attacks where someone can flood your account with Bitcoins and block out transactions that way. Using bitaps, that number seems to be 100, so it would have to be like 30 transactions per second before things started getting risky at a 2 second poll rate. If it were precisely 2 seconds, that is. Either way, it might be an expensive attack to pull off which might profit you more than your normal business, unless it iritated customers enough to not come back and the attacker/donator stopped.

You probably want to only use this with base Satoshis of 10,000 or more.

This is meant for 0 confirmation transactions at a moderate to low rate. For the impatient and not endlessly successful.

Thinking about this more, an attacker can hit your endpoint enough times to build a table of all possible prices. The attacker can then wait for payments and strike with pre-computed payloads. The first request to reach the endpoint wins, more or less. So if you are giving a digital product that you don't care much about, it's probably fine. If not, the user may lose out. EDIT: We now add time to the salt and check current salt and previous salt.

You'll want to log txids for time_window /2, roughly. If the txid has been used, don't do it again. That prevents the multiple buys per transaction attack.

# Licence

[Unlicense/Public domain](LICENSE.txt)
