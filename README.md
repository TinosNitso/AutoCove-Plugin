# AutoCove-Plugin

v1.0.0 has a bug if someone double-pays the address in the same txn, like [this](https://www.blockchain.com/bch/tx/c51e89797be1bc22342bebfd126318dc75aa3d4b0a022f8880dba4e2cd1558d5) example. In that case wallet must be restarted to detect 2nd UTXO in the same UTX. Will be fixed in next version. *ppythagoras* should be spelled *ppythag0ras*. 

It turns out there's actually a new rule I didn't think of sooner. We shouldn't send the exact same amount twice from the same address simultaneously (before confirmation of the 1st return). In that case it's conceivable a miner could take one of the payments as a fee, in a combo return. There's a one-line fix in assembly where the preimage hashSequence is equal to SHA-256d of 'feffffff' (proof of no combo-return). It fixes the degenerate case when someone pays identically simultaneously. Will be in next version of *preturn*... with slightly higher fees.

Automatic covenants forward payments without any further authorization. Parental introspection is achieved using private key=1, so that our public key is the compressed base point of secp256k1. TabIcon will change, and there will be a BCH assembly encoder/decoder in a future version. This is a minimum viable release.

The name is because I worked full-time for years at a factory named after Cathedral **Cove**, here in NZ. 'Cove' is also short for 'Covenant'!

The covenant address & Script are:

[preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4](https://www.blockchain.com/bch/address/preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4)

210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f758708060000000044434675

Another example would be address *ppythag0ras*... which only returns three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a). I don't like Spedn & CashScript, so I might not include them as compilers in the future (*spedn.exe* alone is 21MB).

In the case of *preturn*..., it will return whatever coins are sent to it, automatically, assuming a few conditions.
- Sender must use a P2PKH address.
- Sending transaction must be no more than 520B. Only 3 inputs at most.
- 14 bits minimum for only 1 input.
- 21 BCH max (theoretically), but I've only ever [tested](https://www.blockchain.com/bch/tx/c3350c09687b922c4d91d9a504b11ea9fac64e599b94975cc50d743f422eb7c4) just over a BCH. I've tested multiple inputs & outputs.
- 8 bits minimum fee.
- Total amount will be returned to *first* input.
- **Never** send SLP tokens, or they'll be burned.

bitcoincash:preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4

The private key is just 1, but that's OK.

The **source code** is as follows. First go to the Electron Cash console and enter the following:

    import electroncash
    def __(S):
        try: return bitcoin.int_to_hex(eval('electroncash.address.OpCodes.OP_'+S).value)
        except: return S
        
Hit enter a few times, then

    _=lambda String: ''.join([__(Str) for Str in String.split()])
    
_ is a virtual-machine code translator. Then copy-paste the following lines of **assembly** code:

    '210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'	#STACK IS [TXPARENT, PREIMAGE, SIG] BEFORE [, PUBKEY].
    _('3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY')	#DATA MUST BE PREIMAGE.
    _('TUCK 0144 BIN2NUM SPLIT NIP 0120 BIN2NUM SPLIT DROP')	#[TX, PREIMAGE] PREIMAGE OUTPOINT TXID.
    _('OVER HASH256 EQUALVERIFY')	#[..., TX, TXID] CHECK PARENT TXID MATCHES.
    _('OVER SIZE 0134 BIN2NUM SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM')	#[PREIMAGE, TX] CALCULATE INPUT VALUE FROM PREIMAGE.
    _('OVER SIZE NIP SUB  025402 BIN2NUM SUB  8 NUM2BIN')	#[..., TX, AMOUNT] SUBTRACT FEE OF (SIZE(TXPARENT)+596).
    _('SWAP 012a BIN2NUM SPLIT NIP  1 SPLIT  SWAP BIN2NUM SPLIT NIP')	# [..., TX, AMOUNT] NIP START & SIG OFF TX.
    _('1 SPLIT  SWAP BIN2NUM SPLIT DROP   HASH160')	#[..., TXSPLIT] 1ST INPUT TO PARENT HAS THIS ADDRESS.
    _('SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256')	#[..., AMOUNT, ADDRESS] DETERMINE NECESSARY HASHOUT.
    _('SWAP SIZE 0128 BIN2NUM SUB SPLIT NIP 0120 BIN2NUM SPLIT DROP  EQUAL')	#[PREIMAGE,HASHOUT] CHECK HASHOUT.
    '08060000000044434675'	#[BOOL] APPEND NONCE, FOR VANITY ADDRESS (SEE VANITYTXID-PLUGIN)

**Appending** line after line will yield exactly the covenant Script. The nonce was generated using the [VanityTXID-Plugin](https://github.com/TinosNitso/VanityTXID-Plugin).

SHA256 Checksum: **00000**9379d5ed71837398b6f9280074cb9e978494ec33395437be522328d41e6
