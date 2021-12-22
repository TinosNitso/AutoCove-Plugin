PubKey=bitcoin.public_key_from_private_key((1).to_bytes(32,'big'),compressed=True)  #Secp256k1 generator. This section provides examples of scripts.
CovenantScripts=[
'''# 'preturn...' v1.0.0 Script source-code. I like writing the starting stack items relevant to each line, to the right of it.
21'''+PubKey+'''  #[TXParent, Preimage, Sig] before [, PubKey].
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY	#[..., Preimage, Sig, PubKey] Proof DATA = Preimage SHA256
TUCK 0144 BIN2NUM SPLIT NIP 0120 BIN2NUM SPLIT DROP	#[TX, Preimage] Preimage Outpoint TXID
OVER HASH256 EQUALVERIFY	#[..., TX, TXID] Proof TXParentID = Outpoint TXID
OVER SIZE 0134 BIN2NUM SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM	#[Preimage, TX] Calulate input value from Preimage
OVER SIZE NIP SUB  025402 BIN2NUM SUB  8 NUM2BIN	#[..., TX, Amount] Subtract fee of (SIZE(TXParent)+596).
SWAP 012a BIN2NUM SPLIT NIP  1 SPLIT  SWAP BIN2NUM SPLIT NIP	# [..., TX, Amount] NIP start & sender sig off TX.
1 SPLIT  SWAP BIN2NUM SPLIT DROP   HASH160	#[..., TXSPLIT] 1st input to parent has this address.
SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256	#[..., Amount, Address] Predict hashOutputs.
SWAP SIZE 0128 BIN2NUM SUB SPLIT NIP 0120 BIN2NUM SPLIT DROP  EQUAL	#[Preimage,hashOutputs] Proof hashOutputs EQUAL Amount & Address from Parent.
080600000000444346 DROP #[Bool] Append nonce for vanity address, generated from VanityTXID-Plugin. 
''',
'''# 'preturn...' v1.0.1 Script source-code. This update adds 1 line, a 5% fee increase, to guarantee return has only 1 input. I like writing the starting stack items relevant to each line, to the right of it.
21'''+PubKey+'''  #[TXParent, Preimage, Sig] before [, PubKey].
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY	#[..., Preimage, Sig, PubKey] Proof DATA = Preimage SHA256
TUCK 0144 BIN2NUM SPLIT NIP 0120 BIN2NUM SPLIT DROP	#[TX, Preimage] Preimage Outpoint TXID
OVER HASH256 EQUALVERIFY	#[..., TX, TXID] Proof TXParentID = Outpoint TXID
OVER SIZE 0134 BIN2NUM SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM	#[Preimage, TX] Calulate input value from Preimage
OVER SIZE NIP SUB  027902 BIN2NUM SUB  8 NUM2BIN	#[..., TX, Amount] Subtract fee of (SIZE(TXParent)+596+37).
SWAP 012a BIN2NUM SPLIT NIP  1 SPLIT  SWAP BIN2NUM SPLIT NIP	# [..., TX, Amount] NIP start & sender sig off TX.
1 SPLIT  SWAP BIN2NUM SPLIT DROP   HASH160	#[..., TXSPLIT] 1st input to parent has this address.
SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256	#[..., Amount, Address] Predict hashOutputs.
OVER SIZE 0128 BIN2NUM SUB SPLIT NIP 0120 BIN2NUM SPLIT DROP  EQUALVERIFY	#[Preimage,hashOutputs] Proof hashOutputs EQUAL Amount & Address from Parent.
4 SPLIT  0120 BIN2NUM SPLIT  0120 BIN2NUM SPLIT NIP  0124 BIN2NUM SPLIT DROP  HASH256 EQUALVERIFY #[Preimage] Proof of only 1 input in return TX.
080600000001292a86 DROP #[nVersion] Append nonce for vanity address, generated from VanityTXID-Plugin.
''',
'''#[UTX, Preimage, Sig, PubKey] 'preturn...' v1.0.2 Script. UTX = Unspent TX = Parent. This update reduces fees by 7% by eliminating the PubKey & unecessary use of BIN2NUM. Any PrivKey can be used to broadcast return. BIN2NUM must be used for leading 0-bytes & leading 1-bit. I like writing the starting stack items relevant to each line, to the right of it. 
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY	#[..., Preimage, Sig, PubKey] VERIFY DATA = Preimage SHA256
TUCK 0144 SPLIT NIP 0120 SPLIT DROP	#[UTX, Preimage] Preimage Outpoint TXID
OVER HASH256 EQUALVERIFY	#[..., UTX, UTXID] VERIFY UTXID = Outpoint TXID
OVER SIZE 0134 SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM	#[Preimage, UTX] Calulate input value from Preimage
OVER SIZE NIP SUB  023f02 SUB  8 NUM2BIN	#[..., UTX, Amount] Subtract fee of (SIZE(UTX)+596+37-58).
SWAP 012a SPLIT NIP  1 SPLIT  SWAP SPLIT NIP  1 SPLIT  SWAP SPLIT DROP   HASH160	# [..., TX, Amount] NIP start, NIP sender sig off TX, then 1st input to parent has this address.
SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256	#[..., Amount, Address] Predict hashOutputs for P2PKH.
OVER SIZE 0128 SUB SPLIT NIP 0120 SPLIT DROP  EQUALVERIFY	#[Preimage,hashOutputs] VERIFY hashOutputs EQUAL Amount & Address from Parent.
4 SPLIT  0120 SPLIT  0120 SPLIT NIP  0124 SPLIT DROP  HASH256 EQUALVERIFY #[Preimage] VERIFY only 1 input in return TX.
0803000000001cf0d6 DROP #[nVersion] Append nonce for vanity address, generated using VanityTXID-Plugin.
''',
'''#[UTX, Preimage, Sig, PubKey] 'preturn...' v1.0.3 Script. UTX = (Unspent TX) = Parent. Here is a malleability fix for when a PubKey is prepended to the sender's sigscript. I write the starting stack items relevant to each line, to the right of it.
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY    #[..., Preimage, Sig, PubKey] VERIFY DATApush=Preimage. A DATASIG is 1 shorter than a SIG.
TUCK  4 SPLIT NIP  0120 SPLIT  0120 SPLIT NIP  0124 SPLIT DROP TUCK  HASH256  EQUALVERIFY    #[UTX, Preimage] VERIFY Prevouts = Outpoint. i.e. only 1 input in Preimage, or else a miner could take a 2nd return as fee. hashPrevouts is always @ position 4, & Outpoint is always 0x24 long @ position 0x44.
0120 SPLIT DROP  OVER HASH256 EQUALVERIFY    #[..., UTX, Outpoint] VERIFY UTXID = Outpoint TXID. Outpoint from prior line contains UTXID of coin being returned.
OVER SIZE 0134 SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM    #[Preimage, UTX] Obtain input value from Preimage, always @ 0x34 from its end.
OVER SIZE NIP SUB  025302 SUB  8 NUM2BIN    #[..., UTX, Amount] Subtract fee of (SIZE(UTX)+595 sats). 1 less should also always work.
#[Preimage, UTX, Amount] Next 3 lines calculate the true HASH160 of the sender. The miner can only burn the money, never steal it, by malleating the original sigscript.
SWAP 0129 SPLIT NIP  1 SPLIT  SWAP 018b GREATERTHANOREQUAL  VERIFY    #[..., UTX, Amount] 0x29 byte if under 0x8b, is position of the sender's sigscript size if UTX format is 4+1+0x20+4+... so NIP off the start. 0x8b is the max legit sigscript size (uncompressed PubKey & ECDSA sig). If a miner adds an extra Byte to #inputs, this script should fail. It's more efficient to use 018b as -ve.
1 SPLIT  OVER 0141 GREATERTHANOREQUAL  VERIFY    #[..., UTX[0x2a:]] VERIFY sig at least 0x41 (both Schnorr & ECDSA), or else susceptible to malleability hack where this # is small and hacker's PubKey is squeezed inside a 0x8b sigscript.
SWAP SPLIT NIP  1 SPLIT  SWAP SPLIT DROP  HASH160    # [..., sig size, UTX[0x2b:]] NIP sig & DROP UTX-end, then 1st input to parent has this HASH160.
//[Preimage, Amount, HASH160] '//' comments also work. Next 2 lines use the Amount & HASH160 to VERIFY return TX.
SWAP 041976a914 CAT  SWAP CAT  0288ac CAT  HASH256    #[..., Amount, HASH160] Predict hashOutputs for P2PKH sender. Script could conceivably be shortened by 1B by obtaining HASH160 before Amount.
SWAP SIZE 0128 SUB SPLIT NIP  0120 SPLIT DROP  EQUAL    #[Preimage, hashOutputs] VERIFY hashOutputs is correct. It's located 0x28 from Preimage end.
080600000000ba7087 DROP    #[BOOL] Append nonce for vanity address, generated using VanityTXID-Plugin.
''',
'''//[UTX, Preimage, Sig, PubKey] 'preturn...' v1.0.4 Script. UTX = (Unspent TX) = Parent. I write the starting stack items relevant to each line, to the right of it. This version is simpler & smaller since malleability shouldn't be a problem. It's impossible for a miner to corrupt the P2PKH sender's sigscript. v1.0.4 is a few bytes smaller than v1.0.2. Both '//' & '#' start comments.
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY    #[..., Preimage, Sig, PubKey] VERIFY DATApush=Preimage. DATASIG is 1 shorter than a SIG.
TUCK  4 SPLIT NIP  0120 SPLIT  0120 SPLIT NIP  0124 SPLIT DROP TUCK  HASH256  EQUALVERIFY    #[UTX, Preimage] VERIFY Prevouts = Outpoint. i.e. only 1 input in Preimage, or else a miner could take a 2nd return as fee. hashPrevouts is always @ position 4, & Outpoint is always 0x24 long @ position 0x44.
0120 SPLIT DROP  OVER HASH256 EQUALVERIFY    #[..., UTX, Outpoint] VERIFY UTXID = Outpoint TXID. Outpoint from prior line contains UTXID of coin being returned.
OVER SIZE 0134 SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM    #[Preimage, UTX] Obtain input value from Preimage, always @ 0x34 from its end.
OVER SIZE NIP SUB  023902 SUB  8 NUM2BIN    #[..., UTX, Amount] Subtract fee of (SIZE(UTX)+569 sats). 1 less should also always work.
SWAP 012a SPLIT NIP  1 SPLIT  SWAP SPLIT NIP  1 SPLIT  SWAP SPLIT DROP  HASH160    #[..., UTX, Amount] 0x2a should always be position of P2PKH sender's sig. UTX format is 4+1+0x20+4+1+... so NIP UTX-start, NIP sig & DROP UTX-end, then 1st input to parent has this HASH160.
041976a914 SWAP CAT  CAT  0288ac CAT  HASH256    #[..., Amount, HASH160] Predict hashOutputs for P2PKH sender.
SWAP SIZE 0128 SUB SPLIT NIP  0120 SPLIT DROP  EQUAL    #[Preimage, hashOutputs] VERIFY hashOutputs is correct. It's located 0x28 from Preimage end. Script could conceivably be a byte shorter by using EQUALVERIFY somehow.
080500000001e5413e DROP    #[BOOL] Append nonce for vanity address, generated using VanityTXID-Plugin.

//If the 'preturn...' address is added to a watching-only wallet, this plugin will automatically broadcast the return txns.
#Sender must use a P2PKH address, not P2PK nor P2SH. Native Introspection in 2022 should enable a much simpler Script allowing any sender.
#Sending txn SIZE must be at most 520 Bytes (3 inputs max).
#14 bits minimum for single input, but greater minimum for more inputs.
#Never send it SLP tokens!
#Fee between 8 to 12 bits.
#21 BCH max, but I've only tested 5 tBCH. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#The sender must not use a PUSHDATA OpCode in the output pkscript (non-standard).
#To return from other addresses currently requires editing qt.py.
''']