# AutoCove-Plugin

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.5.WebP)

Unfortunately v1.0.5 doesn't retain highlighting properly when switching spells (like in above WebP). Next version will remember the highlighted text properly! There will be an asm & hex combo-box (instant stripping of leading blue bytes etc, works with all PUSHDATAs, 1N→OP_1N). Asm should help with CashScript compatibility, because its "bytecode" is in asm by default (currently can use `cashc --hex` for AutoCove compatibility). The next *preturn*... covenant will support P2SH (min 3 data-pushes, max 2of2 compressed & 252B sigscript, compatible with VanityTXID) returns as well as P2PKH (all correspond to 2 data-pushes). There will be an OpCount with the Byte Count. TXID lookup. Hex input can start with '0x' etc. And there'll be a new tabIcon based on a Wikimedia flag icon. Also, colors will all work in the dark color theme.

There's a bug sometimes when two or more wallets are open. The decoder loads from the other wallet's memory somehow! (Will be fixed in next update.)

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.5-macOS.png)

Fully automatic covenants forward payments without any further authorization. Parental introspection can be achieved using PrivKey=1, so that PubKey is the compressed base point of secp256k1.

I worked full-time for years at a factory named after Cathedral **Cove**, in NZ. *Cove* is also short for *Covenant*! So *AutoCove* seemed like a nice name. Its current covenant address & script is:

**v1.0.4** [preturn49xt9r8n82rr0lwmzxpgxf6hv4v3gya4qk9](https://www.blockchain.com/bch/address/preturn49xt9r8n82rr0lwmzxpgxf6hv4v3gya4qk9) ([AutoCove_pReturn#157609; 🌵](https://www.cashaccount.info/#lookup) Cash Account):
>6fad7b828c7f757ca87bbb7d547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f7581788277940239029458807c012a7f77517f7c7f77517f7c7f75a9041976a9147c7e7e0288ac7eaa7c820128947f7701207f7587080500000001e5413e75

In the case of *preturn*..., it will return whatever coins are sent to it, automatically, assuming some conditions:
- Sender must use a **P2PKH** address (starting with *q* or *1*, but not P2PK).
- Sending transaction must be no more than **520B**. Only 3 inputs at most.
- 14 bits minimum for only 1 input. **More** bits needed per extra input.
- 21 BCH max (theoretically), but I've only ever [tested](https://www.blockchain.com/bch/tx/c3350c09687b922c4d91d9a504b11ea9fac64e599b94975cc50d743f422eb7c4) just over a BCH (& 10 tBCH on a [testnet4](https://testnet4.imaginary.cash/tx/c2dbbccf399c0a4f7bfa847b95feb44d2fb56254d4a820b28325b443b6874c87)). I've tested multiple inputs & outputs, both Schnorr & ECDSA, & both compressed & uncompressed PubKeys.
- 8→12 bits fee.
- Total amount will be returned to **first** input.
- Never send **SLP** tokens, or they'll be burned.
- Sender's sigscript must not be **malleated** in any way (eg by miner). The output pkscript should have no PUSHDATA OpCodes.

Another example could be address *ppythag0ras*... which only returns three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a). I don't like Spedn & CashScript (*spedn.exe* alone is 21MB).

Vanity hashes & addresses are generated using the [VanityTXID-Plugin](https://github.com/TinosNitso/VanityTXID-Plugin).

v1.0.5 notes:
- **All** OpCodes now supported. Correct decoding & blue coloring for PUSHDATA2 & PUSHDATA4. REVERSEBYTES included as Crypto (Qt.magenta). It had its own CHIP & I've never seen it used, so I missed it in v1.0.4. Next version might use darkBlue for byte/s following a PUSHDATA, instead of blue.
- codes (Pythonic-style) & **op_codes** now selectable, as well as CODES, OP_CODES etc.
- Highlight color now set to reduce Selection HSL darkness(=255-L) by **25%**. Unfortunately 25% mightn't be enough on macOS, due to the pale blue.
- Bugfix for EC-v3.6.6. Unfortunately v1.0.4 broke backwards compatibility without me realizing, due to instant combo-box activation. **SLP Ed.** now supported.
- Bugfix for auto-decode, when unable to.
- SHA256 checksum 00000000b514a883d6f742eb82c0585a695c021fc8ca7f99e9d8f713e3c1fadb (44 kH/s · 10 mins). **Luckiest** hash yet! Updating via reinstall requires restarting EC.

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
