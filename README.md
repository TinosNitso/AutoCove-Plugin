# AutoCove-Plugin

Unfortunately there's a potential malleability **problem** with the preturn addresses! A miner could malleate the txn sending to the address, in which case my scripts aren't smart enough to figure out who sent the money. That would result in the money being burned. Miners routinely vary sigscripts to claim money sent to [this](https://www.blockchain.com/bch/address/bitcoincash:pz689gnx6z7cnsfhq6jpxtx0k9hhcwulev5cpumfk0?page=2) address for example (the empty redeem script address). Unfortunately the miners could always add a huge amount of data into the sender's sigscript, making it too difficult to return to sender! The next version of the IDE will have (optional) colors for all the opcodes, and highlight all instances of a selected word, etc.

I forgot to mention I copied the v1.0.1 tabIcon from [bitcoinbch.com](https://bitcoinbch.com).

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.1.png)

Fully automatic covenants forward payments without any further authorization. Parental introspection is achieved using private key=1, so that our public key is the compressed base point of secp256k1. The name is because I worked full-time for years at a factory named after Cathedral **Cove**, here in NZ. 'Cove' is also short for 'Covenant'! The covenant addresses & Scripts are:

**v1.0.1** [preturn3s5mpe0lna9quvgcs606pffh69g5xukl2hu](https://www.blockchain.com/bch/address/preturn3s5mpe0lna9quvgcs606pffh69g5xukl2hu): 210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794027902819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7882012881947f770120817f7588547f0120817f0120817f770124817f75aa88080600000001292a8675

**v1.0.0** [preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4](https://www.blockchain.com/bch/address/preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4): 210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f758708060000000044434675

In the case of *preturn*..., it will return whatever coins are sent to it, automatically, assuming a few conditions.
- Sender must use a P2PKH address (starting with *q*).
- Sending transaction must be no more than **520B**. Only 3 inputs at most.
- 14 bits minimum for only 1 input. **More** bits needed for more inputs.
- 21 BCH max (theoretically), but I've only ever [tested](https://www.blockchain.com/bch/tx/c3350c09687b922c4d91d9a504b11ea9fac64e599b94975cc50d743f422eb7c4) just over a BCH. I've tested multiple inputs & outputs, both Schnorr & ECDSA.
- 8 bits minimum fee.
- Total amount will be returned to *1st* input. v1.0.0 requires we don't send the exact same amount simultaneously from the same address, but charges a 4% lower fee.
- **Never** send SLP tokens, or they'll be burned.

Another example could be address *ppythag0ras*... which only returns three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a). I don't like Spedn & CashScript (*spedn.exe* alone is 21MB).

Vanity hashes & addresses are generated using the [VanityTXID-Plugin](https://github.com/TinosNitso/VanityTXID-Plugin).

The next version should be able to interpret commas & *op.*, allowing copy-pasting of many existing EC contracts.

v1.0.1 notes:
- Script compiler (encoder) now included. Accepts both lower & upper case opcodes. Both 'Nip' & 'OP_NIP' encode the same. Byte counter included, along with BCH address gen. A future version needs to color the different opcodes in different colors. Maybe a save feature, and decoder? The "IDE" builds the BCH address as user types opcodes etc.
- Covenants' source-code now inside plugin tab. Both are enforced simultaneously.
- Extra line of assembly -> **5%** fee increase, but guarantees return TX has only 1 input.
- No more infinite loop, instead **.history_updated_signal** is used.
- Will return multiple UTXOs in the same sent UTX (bugfix).
- New **tabIcon**, but it could be improved (wavy BCH flag?).
- EC needs to be restarted when updating using re-install. There's an issue where importing a *preturn*... address causes attempted re-broadcasting of previous txns. I forgot to mention a couple rules in the plugin tab: sender must use P2PKH address, & return is always to 1st input.
- SHA256 Checksum **000000**db889e8d14c3b992cd6f1ef75cce65d44641d9487eb066cddac46ea82d (79 kH/s · 48 s)
