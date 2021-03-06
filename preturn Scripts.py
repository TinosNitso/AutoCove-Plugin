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
''',
'''//[UTX, Preimage, Sig, PubKey]   #'preturn...' v1.0.6 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. This update supports both P2PKH & P2SH senders! P2SH sender must have 3 or 4 data-pushes ???75B (e.g. 1of1, 1of2 or 2of2) in its unlocking sigscript ???252B. VanityTXID (compressed) sender is supported! Mof3 MULTISIG not supported.
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY    #[..., Preimage, Sig, PubKey] VERIFY DATApush=Preimage. DATASIG is 1 shorter than a SIG.
TUCK  4 SPLIT NIP  0120 SPLIT  0120 SPLIT NIP  0124 SPLIT DROP TUCK  HASH256  EQUALVERIFY    #[UTX, Preimage] VERIFY Prevouts = Outpoint. i.e. only 1 input in Preimage, or else a miner could take a 2nd return as fee. hashPrevouts is always @ position 4, & Outpoint is always 0x24 long @ position 0x44.
0120 SPLIT DROP  OVER HASH256 EQUALVERIFY    #[..., UTX, Outpoint] VERIFY UTXID = Outpoint TXID. Outpoint from prior line contains UTXID of coin being returned.
OVER SIZE 0134 SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM    #[Preimage, UTX] Obtain input value from Preimage, always @ 0x34 from its end.
OVER SIZE NIP SUB  028902 SUB  8 NUM2BIN    #[..., UTX, Amount] Subtract fee of (SIZE(UTX)+649 sats). A sat less should also always work. P2SH returns are 2B smaller than P2PKH for same SIZE(UTX).
SWAP 0129 SPLIT NIP  1 SPLIT SWAP 0100 CAT BIN2NUM  SPLIT DROP    #[..., UTX, Amount] NIP UTX-start & DROP UTX-end, isolating scriptSig. Always assumes SIZE(scriptSig)<0xfd.
1 SPLIT  SWAP BIN2NUM SPLIT NIP    #[..., scriptSig]  Always assume SIZE(data-push)<0x4c. This rules out Mof3 MULTISIG, & uncompressed VanityTXID. The "0th" data-push, "scriptSig(0)", is only final for P2PK sender, therefore NIP it off. BIN2NUM is only required for an empty data-push (has leading 0-byte).
1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(1)), scriptSig(1:)] ] Separate next data-push.
SIZE  IF  NIP    #[Preimage, Amount, scriptSig(1), [SIZE(scriptSig(2)), scriptSig(2:)] ] SIZE decides whether sender was P2SH or P2PKH. IMO it's more elegant to combine IF with a stack OpCode to simplify the stack.
        1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(2)), scriptSig(2:)] ] Separate next data-push.
        SIZE  IF  NIP	#[Preimage, Amount, scriptSig(2), [SIZE(scriptSig(3)), scriptSig(3:)] ] The next data-push is for 2of2. SIZE decides if it even exists.
                1 SPLIT  SWAP SPLIT    #[..., [SIZE(scriptCode), scriptSig(3:)] ] BIN2NUM unnecessary because the empty redeem Script isn't supported.
        ENDIF  DROP    #[..., scriptCode, 0] Assume "3rd" data-push is final & is scriptCode (i.e. redeem Script).
        HASH160  0317a914 SWAP CAT  CAT  0187    #[..., Amount, scriptCode] Predict Outputs for P2SH sender.
ELSE  DROP    #[Preimage, Amount, PubKey, 0]
        HASH160  041976a914 SWAP CAT  CAT  0288ac    #[..., Amount, PubKey] Predict Outputs for P2PKH sender.
ENDIF  CAT    #[..., SPLIT(Outputs)] From now is the same for both P2SH & P2PKH.
HASH256  SWAP SIZE 0128 SUB SPLIT NIP  0120 SPLIT DROP  EQUAL    #[Preimage, Outputs] VERIFY Outputs==Output is correct. hashOutputs is located 0x28 from Preimage end.
08030000000071d8e9 DROP    #[BOOL] Append nonce for vanity address, generated using VanityTXID-Plugin.
''',
'''//[Sig, PubKey, Preimage, UTX]    #'preturn...' v1.1.0 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. This update reduces fees by up to 18% by using a CODESEPARATOR near the end.
OVER  4 SPLIT NIP  0120 SPLIT  0120 SPLIT NIP  <36> SPLIT DROP TUCK  HASH256  EQUALVERIFY    #[..., Preimage, UTX] VERIFY Prevouts = Outpoint. i.e. only 1 input in Preimage, or else a miner could take a 2nd return as fee. hashPrevouts is always @ position 4, & Outpoint is always 36B long @ position 0x44.
0120 SPLIT DROP  OVER HASH256 EQUALVERIFY    #[..., UTX, Outpoint] VERIFY UTXID = Outpoint TXID. Outpoint from prior line contains UTXID of coin being returned.
OVER SIZE <52> SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM    #[..., Preimage, UTX] Obtain input value from Preimage, always 52B from its end.
OVER SIZE NIP SUB  <514> SUB  8 NUM2BIN    #[..., UTX, Amount] Subtract fee of (SIZE(UTX)+514 sats). A sat less should also always work. P2SH returns are 2B smaller than P2PKH for same SIZE(UTX).
SWAP <41> SPLIT NIP  1 SPLIT SWAP 0100 CAT BIN2NUM  SPLIT DROP    #[..., UTX, Amount] NIP UTX[:41] & DROP UTX-end, isolating scriptSig. Always assumes SIZE(scriptSig)<0xfd.
1 SPLIT  SWAP BIN2NUM SPLIT NIP    #[..., scriptSig]  Always assume SIZE(data-push)<0x4c. This rules out Mof3 MULTISIG, & uncompressed VanityTXID. The "0th" data-push, "scriptSig(0)", is only final for P2PK sender, therefore NIP it off. BIN2NUM is only required for an empty data-push (has leading 0-byte).
1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(1)), scriptSig(1:)] ] Separate next data-push.
SIZE  IF  NIP    #[..., scriptSig(1), [SIZE(scriptSig(2)), scriptSig(2:)] ] SIZE decides whether sender was P2SH or P2PKH. IMO it's more elegant to combine IF with a stack OpCode to simplify the stack.
        1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(2)), scriptSig(2:)] ] Separate next data-push.
        SIZE  IF  NIP	#[..., scriptSig(2), [SIZE(scriptSig(3)), scriptSig(3:)] ] The next data-push is for 2of2. SIZE decides if it even exists.
                1 SPLIT  SWAP SPLIT    #[..., [SIZE(Script), scriptSig(3:)] ] BIN2NUM unnecessary because the empty redeem Script isn't supported.
        ENDIF  DROP    #[..., Script, 0] Assume "3rd" data-push is final & is redeem Script.
        HASH160  0317a914 SWAP CAT  CAT  0187    #[..., Amount, Script] Predict Outputs for P2SH sender.
ELSE  DROP    #[..., PubKey, 0]
        HASH160  041976a914 SWAP CAT  CAT  0288ac    #[..., Amount, PubKey] Predict Outputs for P2PKH sender.
ENDIF  CAT    #[..., SPLIT(Outputs)] From now is the same for both P2SH & P2PKH.
HASH256  OVER SIZE <40> SUB SPLIT NIP  0120 SPLIT DROP  EQUALVERIFY    #[..., Preimage, Outputs] VERIFY Outputs==Output is correct. hashOutputs is located 40B from Preimage end.
SHA256  2 PICK SIZE 1SUB SPLIT DROP    #[Sig, PubKey, Preimage] DATASIG is 1 shorter than a SIG.
SWAP  2 PICK  CODESEPARATOR CHECKDATASIGVERIFY  CHECKSIG    #[Sig, PubKey, SHA256, Sig[:-1]] VERIFY DATApush=Preimage.
0801000000009ab19a DROP    #[BOOL] Append nonce for vanity address, generated using VanityTXID-Plugin. It'd be more efficient before the CODESEPARATOR, but Native Introspection should remove that altogether.
''',
'''//[Sig, PubKey, Preimage, UTX]    #'preturn...' v1.1.1 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. Compared to v1.1.0, this one has up to 2% lower fees by better placement of <Nonce>DROP & CODESEPARATOR.
08070000000345b407 DROP    #[...] Prepend nonce for vanity address, generated using VanityTXID-Plugin.
OVER  4 SPLIT NIP  0120 SPLIT  0120 SPLIT NIP  <32+4> SPLIT DROP TUCK  HASH256  EQUALVERIFY    #[..., Preimage, UTX] VERIFY Prevouts == Outpoint. i.e. only 1 input in Preimage, or else a miner could take a 2nd return as fee. hashPrevouts is always @ position 4, & Outpoint is always 36B long @ position 0x44.
0120 SPLIT DROP  OVER HASH256 EQUALVERIFY    #[..., UTX, Outpoint] VERIFY UTXID == Outpoint TXID. Outpoint from prior line contains UTXID of coin being returned.
OVER SIZE <8+4+32+4+4> SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM    #[..., Preimage, UTX] Obtain input value from Preimage, always 52B from its end.
OVER SIZE NIP SUB  <503> SUB  8 NUM2BIN    #[..., UTX, Amount] Subtract fee of (SIZE(UTX)+503 sats). A sat less should also always work. P2SH returns are 2B smaller than P2PKH for same SIZE(UTX).
SWAP <4+1+32+4> SPLIT NIP  1 SPLIT SWAP 0100 CAT BIN2NUM  SPLIT DROP    #[..., UTX, Amount] NIP UTX[:41] & DROP UTX-end, isolating scriptSig. Always assumes SIZE(scriptSig)<0xfd.
1 SPLIT  SWAP BIN2NUM SPLIT NIP    #[..., scriptSig]  Always assume SIZE(data-push)<0x4c. This rules out Mof3 MULTISIG, & uncompressed VanityTXID. The "0th" data-push, "scriptSig(0)", is only final for P2PK sender, therefore NIP it off. BIN2NUM is required for an empty data-push (has leading 0-byte).
1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(1)), scriptSig(1:)] ] Separate next data-push. Always assume data-push isn't OP_N with N>0. If send is malleable, this is an issue.
SIZE  IF  NIP    #[..., scriptSig(1), [SIZE(scriptSig(2)), scriptSig(2:)] ] SIZE decides whether sender was P2SH or P2PKH. IMO it's more elegant to combine IF with a stack OpCode to simplify the stack.
        1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(2)), scriptSig(2:)] ] Separate next data-push.
        SIZE  IF  NIP   #[..., scriptSig(2), [SIZE(scriptSig(3)), scriptSig(3:)] ] The next data-push is for 2of2. SIZE decides if it even exists.
                1 SPLIT  SWAP SPLIT    #[..., [SIZE(Script), scriptSig(3:)] ] BIN2NUM unnecessary because the empty redeem Script isn't supported.
        ENDIF  DROP    #[..., Script, 0] Assume "3rd" data-push is final & is redeem Script.
        HASH160  0317a914 SWAP CAT  CAT  0187    #[..., Amount, Script] Predict Outputs for P2SH sender.
ELSE  DROP    #[..., PubKey, 0]
        HASH160  041976a914 SWAP CAT  CAT  0288ac    #[..., Amount, PubKey] Predict Outputs for P2PKH sender.
ENDIF  CAT    #[..., SPLIT(Outputs)] From now is the same for both P2SH & P2PKH.
HASH256  OVER SIZE <32+4+4> SUB SPLIT NIP  0120 SPLIT DROP  EQUALVERIFY    #[..., Preimage, Outputs] VERIFY Outputs==Output is correct. hashOutputs is located 40B from Preimage end.
SHA256  2 PICK SIZE 1SUB SPLIT DROP    #[Sig, PubKey, Preimage] DATASIG is 1 shorter than a SIG.
SWAP  2 PICK  CHECKDATASIGVERIFY CODESEPARATOR CHECKSIG    #[Sig, PubKey, SHA256, Sig[:-1]] VERIFY DATApush==Preimage. Only 1B following CODESEPARATOR must be signed for as scriptCode (e.g. by PrivKey=1). 
''',
'''//[SIG[:-1], PubKey, Preimage[68:], UTX]    #'preturn...' v1.1.3 Script. UTX = (Unspent TX) = Parent. The starting stack [...] relevant to each line is to its right, with {...} for ALTSTACK. This update reduces the fee by up to 12% mainly by using a shorter Preimage. Return SIGHASH 0xc3 is required, & ALTSTACK is used for greater efficiency.
080000000000da5ddd DROP    #[...] Prepend nonce for vanity address, generated using VanityTXID-Plugin.
OVER 0120 SPLIT TOALTSTACK  OVER HASH256 EQUALVERIFY    #[..., Preimage[68:], UTX] VERIFY UTXID == Outpoint TXID == Preimage[68:][:32]. IMO starting with OVER is efficient.
SIZE <415> ADD    #[..., UTX] Fee is (SIZE(UTX)+415 sats). A sat less should also always work. P2SH returns are 2B smaller than P2PKH for same SIZE(UTX).
FROMALTSTACK 6 SPLIT NIP  8 SPLIT TOALTSTACK  BIN2NUM    #[...]{Preimage[0x64:]} Obtain 8B Value from Preimage, NIP off 4B Outpoint index + 2B for scriptCode '01ac'. ALTSTACK allows efficient Preimage NIPping.
SWAP SUB  8 NUM2BIN    #[..., Fee, Value] Calculate output Amount by subtracting Fee.
SWAP <4+1+32+4> SPLIT NIP    #[..., UTX, Amount] NIP off UTX nVersion, #Inputs & prior outpoint.
1 SPLIT  SWAP 0100 CAT BIN2NUM  SPLIT DROP    #[..., UTX[41:] ] DROP UTX-end, to isolate scriptSig. Always assumes SIZE(scriptSig)<0xfd. 0 padding guarantees a +ve #.
1 SPLIT  SWAP BIN2NUM SPLIT NIP    #[..., scriptSig]  Always assume SIZE(data-push)<0x4c. This rules out Mof3 MULTISIG, & uncompressed VanityTXID. The "0th" data-push, "scriptSig(0)", is only final for P2PK sender, therefore NIP it off. BIN2NUM is required for an empty data-push (has leading 0-byte).
1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(1)), scriptSig(1:)] ] Separate next data-push. Always assume data-push isn't OP_N with N>0. If send is malleable, this is an issue.
SIZE  IF  NIP    #[..., scriptSig(1), [SIZE(scriptSig(2)), scriptSig(2:)] ] SIZE decides whether sender was P2SH or P2PKH. IMO it's more elegant to combine IF with a stack OpCode to simplify the stack.
        1 SPLIT  SWAP BIN2NUM SPLIT    #[..., [SIZE(scriptSig(2)), scriptSig(2:)] ] Separate next data-push.
        SIZE  IF  NIP   #[..., scriptSig(2), [SIZE(scriptSig(3)), scriptSig(3:)] ] The next data-push is for 2of2. SIZE decides if it even exists.
                1 SPLIT  SWAP SPLIT    #[..., [SIZE(Script), scriptSig(3:)] ] BIN2NUM unnecessary because the empty redeem Script isn't supported.
        ENDIF  DROP    #[..., Script, 0] Assume "3rd" data-push is final & is redeem Script.
        HASH160  0317a914 SWAP CAT  CAT  0187    #[..., Amount, Script] Predict Output for P2SH sender.
ELSE  DROP    #[..., PubKey, 0]
        HASH160  041976a914 SWAP CAT  CAT  0288ac    #[..., Amount, PubKey] Predict Output for P2PKH sender.
ENDIF  CAT    #[..., SPLIT(Output)] From now is the same for both P2SH & P2PKH.
HASH256  FROMALTSTACK 4 SPLIT NIP  0120 SPLIT DROP  EQUALVERIFY    #[..., Output]{Preimage[-44:]} VERIFY Output is correct. NIP off 4B nSequence. hashOutputs @40B from Preimage end.
1 <4+32*2> NUM2BIN  SWAP CAT  SHA256    #[..., Preimage[68:]] Reconstruct full Preimage using nVersion 1, followed by hashSequence & hashPrevouts all zeroed out.
3DUP  SWAP CHECKDATASIGVERIFY  DROP    #[SIG[:-1], PubKey, SHA256] VERIFY Preimage is correct. 
SWAP 01c3 CAT  SWAP  CODESEPARATOR CHECKSIG    #[SIG[:-1], PubKey] VERIFY SIGHASH_SINGLE|ANYONECANPAY|FORKID (0xc3). Efficiently blocks a theoretical vulnerability where a 2nd identical send is taken as a fee instead of being returned. A SIG is 1B longer than a DATASIG, due to the SIGHASH. Only 1B following CODESEPARATOR must be signed for as scriptCode (e.g. by PrivKey=1). 

#If the 'preturn...' address is added to a watching-only wallet, this plugin will automatically broadcast the return txns.
#Sender must use a P2PKH or P2SH address, not P2PK. P2PK isn't currently supported by EC.
#P2SH sender must have 3 or 4 data pushes, ???75B each, in their unlocking sigscript ???252B. Compressed 1of1, 1of2, 2of2 & VanityTXID are all compatible.
#Sending txn SIZE must be at most 520 Bytes. 3 inputs max for P2PKH, 1 input max for 2of2.
#13 bits minimum for single input (P2PKH sender), but add a couple more bits per extra input.
#It can't return SLP tokens!
#Fee btwn 6 to 9 bits.
#21 BCH max, but only 10tBCH have been tested. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#To return from other addresses requires editing qt.py.
''']