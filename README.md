# AutoCove-Plugin

v1.0.6 is having trouble decoding all sigscript data-pushes as comments, when they're just non-0 constants like OP_1. Next version will fix it. Also the v1.0.6 covenant would fail if the P2SH sender pushes a non-0 constant like OP_1 as one of the 3 or 4 data-pushes. Brown & darkMagenta should be switched around, and on dark theme the light-blue constants needs to be lighter.

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.5.WebP)

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.6-macOS.png)

Fully automatic covenants forward payments without any further authorization. Parental introspection can be achieved using PrivKey=1, so that PubKey is the compressed base point of secp256k1.

I worked full-time for years at a factory named after Cathedral **Cove**, in NZ. *Cove* is also short for *Covenant*! So *AutoCove* seemed like a nice name. Its current covenant address & script is:

**v1.0.6** [preturn5pf0m9dnrjwqx0ttca4f8pxfvscnwwy0zl3](https://www.blockchain.com/bch/address/preturn5pf0m9dnrjwqx0ttca4f8pxfvscnwwy0zl3) ([pReturn_AutoCove#158748; 🥝](https://www.cashaccount.info/#lookup) Cash Account):
>6fad7b828c7f757ca87bbb7d547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f7581788277940289029458807c01297f77517f7c01007e817f75517f7c817f77517f7c817f826377517f7c817f826377517f7c7f6875a90317a9147c7e7e01876775a9041976a9147c7e7e0288ac687eaa7c820128947f7701207f758708030000000071d8e975

In the case of *preturn*..., it will return whatever coins are sent to it, automatically, assuming some conditions:
- Sender must use a **P2PKH** or **P2SH** address (but not P2PK).
- P2SH sender must use 3 or 4 data pushes, ≤75B each, in their unlocking sigscript ≤252B. Compressed 1of1, 1of2, 2of2 & VanityTXID are all compatible.
- Sending transaction must be no more than **520B**. Only 3 inputs at most.
- 15 bits minimum for only 1 input. ~2 bits **more** needed per extra input.
- 21 BCH max (theoretically), but I've only tested up to 10tBCH. I've tested 1of1, 2of2, multiple inputs & outputs, Schnorr & ECDSA, both compressed & uncompressed PubKeys (P2PKH) on [testnet4](https://testnet4.imaginary.cash/address/bchtest:preturn5pf0m9dnrjwqx0ttca4f8pxfvschu2rd4cd).
- 8→12 bits fee.
- Total amount will be returned to **first** (0th) input.
- Never send **SLP** tokens.
- Sender's sigscript must not be **malleated** in any way (eg by miner). The output pkscript should have no PUSHDATA OpCodes.

Another example could be address *ppythag0ras*... which only returns three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a).

Vanity hashes & addresses are generated using the [VanityTXID-Plugin](https://github.com/TinosNitso/VanityTXID-Plugin).

v1.0.6 notes:
- **asm** stripping (instant via combo-box). It works with PUSHDATA OpCodes, and highlighting. OpCodes 10-16 are given a leading 'OP_'. It's some tricky code! e.g. [Here](https://github.com/mr-zwets/RefreshContract/blob/main/refresh.json) is the RefreshTimer.cash CashScript bytecode.
- **OpCount** next to ByteCount. e.g. [Mecenas](https://www.blockchain.com/bch/tx/4b84bd37e0660203da70796e9dd76f58f37d843917694c59ede7758ded5bb05f) has 228 ops, but only <201 ever execute.
- New v1.0.6 covenant supports both P2PKH & **P2SH** (3 or 4 data pushes ≤75B, ≤252B sigscript) returns. This enables VanityTXID address compatibility, so that sending TXID may be vanitized (but a miner malleating a data-push past 75B is a vulnerability).
- *0x* & *0X* hex input now accepted, but only for decoder, raw TX & TXID.
- Decoding whole txns now includes the whole **scriptSig** of each input with data-pushes as comments (1/line). Sort of like Blockchain.com. Unfortunately the SLP Ed. causes a bug when OP_0 is a data-push (as is common with multisig Scripts), but next update should fix it.
- **TXID** lookup if user pastes it instead of the txn. A neat trick is to line up lots of TXID examples and have the EC network fetch each successful stack.
- Byte/s following a *PUSHDATA* are now gray-blue, instead of blue.
- PUSHDATA4 added to *Disabled* list. BCH disabled it as part of a malleability fix, I think.
- Selection & highlighting maintained as spells are changed between CODES & OP_CODES etc. Tracking is ok, but for multiple words the selection doesn't change size.
- **Dark theme** fully supported! Keeping colors consistent is tricky. A future version could enable live toggling between white & dark. On MX Linux the combo-boxes are strange, but still work, in the dark theme.
- macOS highlighting now darker, but it turned out too dark!
- Bugfix so that multiple wallets each have their own auto-decoder memory (combo-box).
- 21 bytes/line max target for auto-decoder, instead of 16 words/line. e.g. HASH160 requires (1+20)B. BIN2NUM no longer ends lines. Oh & indents are 8 spaces.
- New tabIcon based on a public-domain WikiMedia flag icon. Still not animated.
- SHA256 Checksum: 000000b45c129df3950971cf14608568ac8cf8bf853e4b09dde0900dda1aca72 (36 kH/s · 12 mins) Update via re-install requires restarting EC.

v1.0.5 notes:
- **All** OpCodes now supported. Correct decoding & blue coloring for PUSHDATA2 & PUSHDATA4. REVERSEBYTES included as Crypto (Qt.magenta). It had its own CHIP & I've never seen it used, so I missed it in v1.0.4. Next version might use darkBlue for byte/s following a PUSHDATA, instead of blue.
- codes (Pythonic-style) & **op_codes** now selectable, as well as CODES, OP_CODES etc.
- Highlight color now set to reduce Selection HSL darkness(=255-L) by **25%**. Unfortunately 25% mightn't be enough on macOS, due to the pale blue.
- Bugfix for EC-v3.6.6. Unfortunately v1.0.4 broke backwards compatibility without me realizing, due to instant combo-box activation. **SLP Ed.** now supported.
- Bugfix for auto-decode, when unable to.
- SHA256 checksum 00000000b514a883d6f742eb82c0585a695c021fc8ca7f99e9d8f713e3c1fadb (44 kH/s · 10 mins). **Luckiest** hash yet!

v1.0.4 notes:
- OP_CODES, CODES, Codes & Op_Codes combo-box, with **highlighted** activation!
- Auto-decodes now **saved** into a combo-box, with 'Clear all...' item.
- Bugfix for when sender's txn is **exactly** size 255B.
- Highlighting is now a slightly **different** color. Unfortunately the macOS shade I chose is too light - will be fixed next time.
- OpCodes list display improved, with purple for Native Introspection. darkCyan was a tiny bit too close to darkGreen, so Locktime can be darkYellow & Reserved words brown (dark orange). Lines broken up into nullary, unary, binary & ternary etc.
- '//' comments are now fully enabled.
- Bugfix for auto-decode when user holds in delete.
- Users can now copy-paste whole raw txns and the decoder will store all P2SH Scripts. Another decoder is at [imaginary.cash](https://testnet4.imaginary.cash/decoder).
- BOOLAND now **ends** lines (auto-decode).
- Decoding in-Script data pushes up to **255B** size now supported (instead of just 0x4b).
- Thread.isAlive renamed to Thread.is_alive, to resolve [Issue #1](https://github.com/TinosNitso/AutoCove-Plugin/issues/1). I still haven't built EC itself from source, though. Apparently builds are **deterministic**. 
- Description moved from its own box to Script comments. Improved TabIcon.
- preturn Script which is only 108B. Malleability was [fixed](https://read.cash/@BigBlockIfTrue/achievement-unlocked-bitcoin-cash-fixed-all-common-third-party-transaction-malleation-vectors-219682ef) years ago.
- SHA256 Checksum 0000001e9dba81c3416e191153644daed60081aacf24f226055db613f0abb4f7 (49 kH/s · 1min).

v1.0.3 notes:
- Hex **decoder**! Copy paste any script hex into the Script box, and it will be auto-decoded into readable form. This lets us color in any BCH Script (& hex), eg from Mecenas or Hodl plugins, using only their blockchain hex. The exact decoding rules seem subjective: 16 words/line max; data pushes >=20B get their own lines; any VERIFY, NUM2BIN or BIN2NUM ends lines; tabbing for IF, NOTIF, ELSE etc. 
- *preturn* covenant now has malleability fix which blocks miners from **stealing** the money. Both compressed & uncompressed sender PubKeys have been tested, as well as Schnorr & ECDSA sigs.
- 6 **disabled** OpCodes are now listed.
- More efficient coloring by only coloring when either hex (bytecode) or selection has changed.
- **Split**-word selection highlighting. e.g. Selecting 'R OR' highlights all instances of 'OR' in hex.
- 'New' QComboBox item, but still no memory (nor undo & save).
- Increased return broadcast **delay** to 2s.
- SHA256 Checksum 000000ed60808ac146dd2cba2c19bbcdd96c968b5be1972a440fe7c33b73494e (51 kH/s · 44 s). Restart EC if updating via re-install.

v1.0.2 notes:
- *preturn...* covenant has **7%** fee reduction by eliminating unnecessary PubKey & *BIN2NUM*. Improved comments.
- Full list of colored **OpCodes**.
- Selecting text now **highlights** all instances of it. Works with both colors & B&W. Highlighting is maintained when toggling colors. 
- Highlighting works with scriptCode **hex**, too, as a byte search. i.e. double-click OpCodes or data push to light up all instances of its hex. Should also work with testnet OpCodes which I haven't colored. If script can't be interpreted, then there's no hex highlighting. Isolate multiple lines of code in hex by selecting them.
- *Colors* option. The blue isn't accurate for PUSHDATA2 & PUSHDATA4. Adding serifs to default font is too difficult (BCH code differentiation). The assignment of colors can change in the future. Holding in space-bar with colors will max out a CPU processor.
- **Hex** coloring, too! This increases CPU lag, which was barely noticeable for script-only colors.
- Added **malleability** warning, along with P2PK & SLP warnings. Sender should use standard output (no OP_PUSHDATA), or else EC doesn't detect it.
- Bug-fix for when a new wallet imports a *preturn...* and plugin tries to re-broadcast before wallet has had time to fully analyze history.
- **TabStopDistance** reduced to 4 chars.
- SHA256 Checksum **000000**eab8901f17435840ff2a80367d035966f436219425741ec473625b71da (60 kH/s · 10s).

v1.0.1:
- Script compiler (encoder) now included. Accepts both lower & upper case opcodes. Both 'Nip' & 'OP_NIP' encode the same. Byte counter included, along with BCH address gen. A future version needs to color the different opcodes in different colors. Maybe a save feature, and decoder? The "IDE" builds the BCH address as user types opcodes etc.
- Covenants' source-code now inside plugin tab. Both are enforced simultaneously.
- Extra line of assembly -> **5%** fee increase, but guarantees return TX has only 1 input.
- No more infinite loop, instead **.history_updated_signal** is used.
- Will return multiple UTXOs in the same sent UTX (bugfix).
- New **tabIcon**, but it could be improved (wavy BCH flag?).
- EC needs to be restarted when updating using re-install. There's an issue where importing a *preturn*... address causes attempted re-broadcasting of previous txns. I forgot to mention a couple rules in the plugin tab: sender must use P2PKH address, & return is always to 1st input.
- SHA256 Checksum **000000**db889e8d14c3b992cd6f1ef75cce65d44641d9487eb066cddac46ea82d (79 kH/s · 48 s)
