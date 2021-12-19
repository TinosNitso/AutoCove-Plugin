# AutoCove-Plugin

v1.0.4-dev2 is a pre-release I've uploaded above. It has a new combo-box for Codes, CODES & OP_CODES. It stores each new decode in memory (existing combo-box).  It's got Script comment corrections. There's a bug-fix for when someone holds down delete, & BOOLAND finishes lines. The highlighting has a slightly different shade of blue. It can decode whole txns and puts all P2SH inputs in the combo-box. I might switch around yellow & brown. Unfortunately the dev1 version had a serious bug in the decoder (large data pushes which I didn't notice).

threading.Thread.isAlive() still needs improvement, along with support for larger data pushes.

There's a new EC-v4.2.6 with new OpCodes! The v1.0.3 decoder still gets them, but messes up the colors. v1.0.3 has a bad comment: "A PUSHDATA OpCode is -ve." I was thinking of 0xfd used to push a large sigscript. 0x4c, 0x4d & 0x4e are all +ve, but still can't be used to steal money using malleability. Also where the comments have UTX[0x29:] & UTX[0x2a:], it should instead be UTX[0x2a:] & UTX[0x2b:]. One future possibility is that the decoder might be able to predict the stack depth (as a #comment), but maybe being able to save .rtf is something I'll look at. The Locktime color might be a bit too green. (Aside: **BFP** is working in the SLP Ed. v3.6.7-dev7.) I figure *CODE* is the easiest to type, but *Code* might be more readable. e.g.

`OutpointTXHash OutpointIndex OutputBytecode`

`OUTPOINTTXHASH OUTPOINTINDEX OUTPUTBYTECODE`

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.3.png)

![alt text](https://github.com/TinosNitso/AutoCove-Plugin/blob/main/v1.0.3-macOS.png)

Fully automatic covenants forward payments without any further authorization. Parental introspection is achieved using private key=1, so that our public key is the compressed base point of secp256k1. The name is because I worked full-time for years at a factory named after Cathedral **Cove**, here in NZ. 'Cove' is also short for 'Covenant'! The covenant address & script is:

**v1.0.3** [preturnge52kd6s9cq2tvmheh5j5jv42cv4ahf0v42](https://www.blockchain.com/bch/address/preturnge52kd6s9cq2tvmheh5j5jv42cv4ahf0v42):
>6fad7b828c7f757ca87bbb7d547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f7581788277940253029458807c01297f77517f7c018ba269517f780141a2697c7f77517f7c7f75a97c041976a9147e7c7e0288ac7eaa7c820128947f7701207f7587080600000000ba708775

In the case of *preturn*..., it will return whatever coins are sent to it, automatically, assuming some conditions:
- Sender must use a **P2PKH** address (starting with *q* or *1*, but not P2PK).
- Sending transaction must be no more than **520B**. Only 3 inputs at most.
- Sender's sigscript must not be **malleated** in any way (eg by miner). The output pkscript should have no PUSHDATA OpCodes. Unfortunately miner's are free to add too much spam to sigscripts.
- 14 bits minimum for only 1 input. **More** bits needed for more inputs.
- 21 BCH max (theoretically), but I've only ever [tested](https://www.blockchain.com/bch/tx/c3350c09687b922c4d91d9a504b11ea9fac64e599b94975cc50d743f422eb7c4) just over a BCH. I've tested multiple inputs & outputs, both Schnorr & ECDSA, & both compressed & uncompressed PubKeys.
- 8 bits minimum fee.
- Total amount will be returned to *1st* input.
- Never send **SLP** tokens, or they'll be burned.

Another example could be address *ppythag0ras*... which only returns three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a). I don't like Spedn & CashScript (*spedn.exe* alone is 21MB).

Vanity hashes & addresses are generated using the [VanityTXID-Plugin](https://github.com/TinosNitso/VanityTXID-Plugin).

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
