from PyQt5.QtCore         import Qt
from PyQt5.QtGui          import QIcon, QMovie, QColor
from PyQt5.QtWidgets      import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit, QCheckBox, QPushButton, QFileDialog
from electroncash         import bitcoin
from electroncash.plugins import BasePlugin, hook
import electroncash, zipfile, shutil, threading, time, json

Codes={'Constants': '0 False  PushData1 PushData2 PushData4 1Negate  1 True '+''.join(' '+str(N) for N in range(2,17))}   #Codes dict is used for colors & lower-case conversion.
Codes['Flow control']='NOp If NotIf Else EndIf Verify Return'
Codes['Stack']='ToAltStack FromAltStack 2Drop 2Dup 3Dup 2Over 2Rot 2Swap IfDup Depth Drop Dup Nip Over Pick Roll Rot Swap Tuck'
Codes['Splice']='Cat Split Num2Bin  \nBin2Num Size' #Binary & unary.
Codes['Bitwise logic']='Invert And Or XOr Equal EqualVerify'    #Unary & binary.
Codes['Arithmetic']='1Add 1Sub 2Mul 2Div Negate Abs Not 0NotEqual  \nAdd Sub Mul Div Mod LShift RShift BoolAnd BoolOr NumEqual NumEqualVerify NumNotEqual LessThan GreaterThan LessThanOrEqual GreaterThanOrEqual Min Max  \nWithin' #Unary, binary & ternary.
Codes['Crypto']='RIPEMD160 SHA1 SHA256 Hash160 Hash256 CodeSeparator  \nCheckSig CheckSigVerify CheckMultiSig CheckMultiSigVerify CheckDataSig CheckDataSigVerify ReverseBytes'
Codes['Locktime']='CheckLocktimeVerify NOp2  CheckSequenceVerify NOp3'  #Unary

codesPythonic='pushData1 pushData2 pushData4  nOp notIf endIf  toAltStack fromAltStack ifDup  xOr equalVerify 0notEqual lShift rShift boolAnd boolOr numEqual numEqualVerify numNotEqual lessThan greaterThan lessThanOrEqual greaterThanOrEqual  codeSeparator checkSig checkSigVerify checkMultiSig checkMultiSigVerify checkDataSig checkDataSigVerify reverseBytes  checkLocktimeVerify nOp2 checkSequenceVerify nOp3  verIf verNotIf nOp1 nOp4 nOp5 nOp6 nOp7 nOp8 nOp9 nOp10  '
OpCodesMembers=electroncash.address.OpCodes.__members__.keys()  #Not all EC versions have Native Introspection. May fit in-between Locktime & Reserved words.
if 'OP_TXLOCKTIME' in OpCodesMembers:
    Codes['Native Introspection']='InputIndex ActiveBytecode TXVersion TXInputCount TXOutputCount TXLocktime  \nUTXOValue UTXOBytecode OutpointTXHash OutpointIndex InputBytecode InputSequenceNumber OutputValue OutputBytecode'   #Nullary & unary.
    codesPythonic               +='inputIndex activeBytecode txVersion txInputCount txOutputCount txLocktime utxoValue utxoBytecode outpointTxHash outpointIndex inputBytecode inputSequenceNumber outputValue outputBytecode'
Codes['Reserved words']='Reserved Ver VerIf VerNotIf Reserved1 Reserved2 NOp1 NOp4 NOp5 NOp6 NOp7 NOp8 NOp9 NOp10'  #Nullary

Codes['BCH']='\nCAT SPLIT NUM2BIN BIN2NUM AND OR XOR DIV MOD CHECKDATASIG CHECKDATASIGVERIFY REVERSEBYTES' #'MS Shell Dlg 2' is default font but doesn't seem to allow adding serifs (e.g. for BCH codes).
Codes['Disabled']='PUSHDATA4 INVERT 2MUL 2DIV MUL LSHIFT RSHIFT'
Codes1N = {str(N) for N in range(10,17)}   #Codes1N is the set of OpCode names which are hex when 'OP_' is stripped from them, which isn't allowed in Asm.
#Test line (copy-paste for spectrum): PUSHDATA2 0100ff RETURN TOALTSTACK NUM2BIN INVERT MAX CHECKSIGVERIFY CHECKLOCKTIMEVERIFY TXLOCKTIME RESERVED 
#Brown (here) is dark-orange. Sky-blue & Purple (here) stem from blue. darkCyan (aka teal) appears too close to darkGreen. Byte/s following a PUSHDATA are gray+blue. darkYellow is aka olive. Orange looks like red when I look up at my LCD, but looks like yellow when I look down. Green pixels may be projecting upwards. darkCyan is clearer from above, & can be re-introduced in the future.
Colors = {'Constants':Qt.blue,'Flow control':QColor(128,64,0),'Stack':Qt.darkGreen,'Splice':Qt.red,'Bitwise logic':QColor(255,128,0),'Arithmetic':QColor(0,128,255),'Crypto':Qt.magenta,'Locktime':Qt.darkYellow,'Reserved words':Qt.darkMagenta,'Native Introspection':QColor(128,0,255),'SelectionForeground':Qt.white,'PushData':QColor(128,128,255),'Data':Qt.black}

DarwinBool = False  #Keep track of whether or not macOS.
if 'nt' in shutil.os.name:                  Color=QColor(0,120,215) #WIN10 is strong blue. This section determines highlighting color. There may not be a command to get this automatically.
elif 'Darwin' in shutil.os.uname().sysname: Color, Colors['SelectionForeground'], DarwinBool = QColor(179,215,255), Qt.black, True  #macOS Catalina is pale blue with black foreground. Windows & MX Linux have white foreground.
else:                                       Color=QColor(48,140,198)    #MX Linux is medium blue.
ColorLightness = Color.lightness()
if ColorLightness < 128: ColorLightness = .75*ColorLightness + 64   #This formula decreases darkness of highlighting by 25%. Max lightness is 255, but MSPaint has max luminosity at 240.
else:                    ColorLightness*= .875   #In this case, decrease lightness by an eighth. A quarter is too much on macOS, but an eighth isn't enough on Windows!
Color.setHsl(Color.hslHue(),Color.hslSaturation(),ColorLightness)
Colors['SelectionBackground'] = Color

ColorDict, CaseDict = {}, {}    #OpCode dictionaries. ColorDict maps CODE to Color, & CaseDict maps CODE to Code. All dicts could be combined into one master dict, but that may not be as fast and elegant, except during initialization. CodeDict & CaseDict don't have to be as fast.
for key in Codes.keys()-{'BCH','Disabled'}:
    for Code in Codes[key].split():
        CODE = Code.upper()
        ColorDict[CODE], CaseDict[CODE] = Colors[key], Code
HexDict, CodeDict, DepthDict = {}, {}, {}  #CodeDict is used by the decoder as a reversed HexDict. HexDict maps each CODE to hex. DepthDict maps CODE to ΔDEPTH.
for OP_CODE in OpCodesMembers:    #There might be more OpCodes than what's typed here.
    CODE=OP_CODE[3:]
    HexDict[CODE], DepthDict[CODE] = bitcoin.int_to_hex(electroncash.address.OpCodes[OP_CODE].value), 0 #DepthDict is updated from 0 later.
    CodeDict[HexDict[CODE]] = CODE
    try:    ColorDict[CODE]    #Check whether code's been typed out.
    except: ColorDict[CODE], CaseDict[CODE] = Qt.gray, CODE  #Ensure ColorDict & CaseDict well-defined for all OpCodes.
for CODE in '0 1 CHECKLOCKTIMEVERIFY CHECKSEQUENCEVERIFY'.split(): CodeDict[HexDict[CODE]] = CODE   #I prefer the ones spelled here.

for code in codesPythonic.split():  #This section converts CaseDict from CODE→Code mapping, into CODE → Code, code mapping. 
    CODE = code.upper()
    CaseDict[CODE] = CaseDict[CODE], code
for CODE in CaseDict.keys()-codesPythonic.upper().split(): CaseDict[CODE] = CaseDict[CODE], CODE.lower()  #Ensure CaseDict tuple is valid for all CODEs.

for CODE in Codes['Constants'].upper().split(): DepthDict[CODE]=1   #This section maps CODE to Δdepth. Δ is just a variable.
Δ = 'IF -1 NOTIF -1 VERIFY -1 '
Δ+= 'TOALTSTACK -1 FROMALTSTACK 1 2DROP -2 2DUP 2 3DUP 3 2OVER 2 DEPTH 1 DROP -1 DUP 1 NIP -1 OVER 1 TUCK 1 '   #IFDUP is 0 or 1.
Δ+= 'CAT -1 NUM2BIN -1 SIZE 1 '
Δ+= 'AND -1 OR -1 XOR -1 EQUAL -1 EQUALVERIFY -2 '
Δ+= 'ADD -1 SUB -1 MUL -1 DIV -1 MOD -1 LSHIFT -1 RSHIFT -1 BOOLAND -1 BOOLOR -1 NUMEQUAL -1 NUMEQUALVERIFY -2 NUMNOTEQUAL -1 LESSTHAN -1 GREATERTHAN -1 GREATERTHANOREQUAL -1 MIN -1 MAX -1 '
Δ+= 'WITHIN -2 '
Δ+= 'CHECKSIG -1 CHECKSIGVERIFY -2 CHECKDATASIG -2 CHECKDATASIGVERIFY -3 '    #CHECKMULTISIG is <-2 & CHECKMULTISIGVERIFY<-3.
Δ+= 'INPUTINDEX 1 ACTIVEBYTECODE 1 TXVERSION 1 TXINPUTCOUNT 1 TXOUTPUTCOUNT 1 TXLOCKTIME 1 '
Δ = Δ.split()
for N in range(len(Δ)>>1): DepthDict[Δ[2*N]] = int(Δ[2*N+1])
for CODE in {'IFDUP', 'CHECKMULTISIG', 'CHECKMULTISIGVERIFY'}: DepthDict[CODE] = None   #These aren't supported.

CovenantScripts=[   #This section can provide examples of Scripts.
'''#Copy-paste one of the following TXIDs into this box (when empty) to see examples of P2SH sigscripts.
//9b91b2c8afb3caca4e98921cb8b7d6131a8087ee524018d1154b609b92e92b30        #RefreshTimer.cash State 0.
//4377faca0d82294509e972f711957e95a843c01119320a3e2b0b4daf26afca28        #HODL plugin.
//0000000e0ad818cf6600060b5ee4cf75e6f4292204af77aceb2f95bbf9fc1194        #VanityTXID plugin.
//92e84abf278e13f5a398e431c970ed86caed4280d2d3c51692912b9ccdacf9ee        #AutoCove plugin, pReturn...
//4b84bd37e0660203da70796e9dd76f58f37d843917694c59ede7758ded5bb05f        #Mecenas plugin, protege spend. (Set time>0)
//a1018135011451d569183e6e327b37bb2600ac7001b1b918fc6121ad3e4bcf78        #Last Will plugin, cold ended with Schnorr sig. (Cold & Refresh wallets should be separate.)
//83b045c46418d0dd1922d52d6b0c2b35366e77cb9d20647e43b13cfcb78ec58c        #1of1 multisig.
//fccebdc8fcf556bebeb91ded0339756e568b254a6aa797f22a74ec3787f8a5d0        #3of5, 20 inputs, 5th on BCH rich-list with over 1% of all BCH.
//1fcd75baedf6cc609e6d0c66059fc3937a1d185fb50a15d812d0747544353e5d        #2of3, 121 inputs, 89 kBCH. Inputs can be compared by scrolling through them.

#Copy-paste a redeem Script to decode without the full sigscript.
//820140877c7500c0879a00c900879a51c951879a00c851c8879a00cd00c7879a        #Native Introspection "teaser" by u/bitcoincashautist, requires EC v4.2.6+. It's TXIDs are on testnet4, which would require running 'Electron-Cash --testnet4'.
//6321026644cb387614f66421d14da3596c21cffa239011416c9adf3f351ee8551a9fc767029000b27521029654f80732769d7c435a184a3559f12178315526c53bbf003349390811c7590a68ac        #BTC-testnet to_local LightNing HTLC.

#CashScript hex can also be decoded. The following is the smartBCH SHA-Gate cc_covenant_v1.cash demo, without Native Introspection. cashc compiles to asm by default (in that case select 'asm', above, before inserting).
//5379547f7701207f01207f7701247f61007f77820134947f587f547f7701207f75597a5a796e7c828c7f755c7aa87bbbad060400000000145a7a7e5379011a7f777e587a8101117a635979a9597988029600b2757603e09304967802307597a269675f79009c635979a95b795d797e5e797ea9597988765c7987785e79879b785f79879b697803e09304965279023075979f63022c01b2756875675d79547f7701257f75a914282711cb97968c8674a46b5564ce3549f5782ea48855795e79aa7e5f797eaa5779885d7960797f7701247f7556798860796376023075937767768b7768547854807e5579557f777e7b757c6853798102d007945880760317a9147e5379a97e01877e76aa5579886d686d6d6d6d6d6d6d6d7551
#A few more follow, with artifacts from James Cramer. slp_dollar.artifact is for issuer freezable SLP tokens, with dust notifications, which can only ever be sent from & to freezable addresses. Unfortunately slp_dollar.cash v0.1 is different to the v0.1 source in the .artifact, whose own source doesn't compile with cashc v0.6.5 to the v0.5.3 bytecode (there's a 'NOP 0168' vs '016b' discrepancy near the beginning). There's a bug since DEPTH+Δ>1 on all branches.
//5579009c635679016b7f77820134947f5c7f7701207f75527902010187916959798277589d5a79827701219d5b798277589d170000000000000000406a04534c500001010453454e4420577a7e587e59797e587e5b797e7b01207f77082202000000000000760317a9147e5156797e587e5c7a7e01147e5c79a97e53797ea97e01877e780317a9147e51577a7e587e5d7a7e01147e58797e547a7ea97e01877e7b041976a9147e5a7aa97e0288ac7e727e7b7e7c7e577a7eaa885579a97b88716e7c828c7f75577aa87bbbac77777767557a519d55796101687f77820134947f5c7f7701207f75587951876352790100886758790100876352795188686851597a7e7b527f777e082202000000000000760317a9147e7ba97e01877e7c041976a9147e557a7e0288ac7e170000000000000000376a04534c500001010453454e4420577a7e587e557a7e537a7c537a7e7b7e557a7eaa88537a7b6e7c828c7f75557aa87bbbac7768
#cashc -h slp_vault.cash aims to avoid accidental burning of SLP tokens. Equivalent to asm bytecode in slp_vault.artifact, & has no CODESEPARATORs. Both cashc v0.6.5 & v0.5.3 -h output are identical for the following 2 Scripts.
//78009c635279820134947f77587f75547f7581022202a1635379587f7508000000000000000088685379547a827752947f770288ac885379a988726e7c828c7f75557aa87bbbac77677c519d7801447f7701247f820134947f77587f547f7701207f757c547f7581022202a163765579aa885479587f750800000000000000008868557a56797e577a7eaa7b01207f7588716e7c828c7f75567aa87bbbac77777768
#slp_mint_guard.artifact. Equivalent to 'cashc -h slp_mint_guard.cash' + 2 CODESEPARATORs. There's a bug since DEPTH+Δ>2 for all branches.
//5479009c635579820128947f7701207f755779827701219d707c7e030102087e0800000000000000007e0822020000000000000317a9147e01145a7aa97e01207e567a7e01177e557a7e01207e54797e5a797ea97e01877e7c577a7e7c7e5679040000000087646e58797eaa88676eaa8868577aa8537a885679a9537a88567a567a6e7c828c7f75577aa87babbbad6d6d5167547a519d5479820128947f7701207f75707c7e030102087e577a7e0822020000000000000317a9147e011457797e01207e567a7e01177e557a7e01207e54797e59797ea97e01877e7c567a7e7c7e5579040000000087646e57797eaa88676eaa8868567aa8537a885579a9537a88716e7c828c7f75567aa87babbbac77777768
#And there's 'cashc -h yieldContract.cash', yield-farming CashScript from github.com/mazetoken/SLP-smart-contract-tokens. There's a bug due to +4Δ (>+1Δ is invalid).
//52796101687f77820134947f5c7f7701207f75567a56796e7c828c7f75587aa87bbbad02e8030222020222025879537aa269080000000000000000016a04534c5000827c7e7e51827c7e7e044d494e548276014ba063014c7c7e687c7e7e577a8276014ba063014c7c7e687c7e7e53827c7e7e0800000000000186a0827c7e7e827c7e7e7b5880041976a9147e567aa97e0288ac7e567a5880041976a9147e567a7e0288ac7e537a58800317a9147e557aa97e01877e727e7b7e7c7eaa87
''',
''.join(Codes[key].upper()+'    #'+key+'\n' for key in Codes.keys())+'//Native Introspection & MUL OpCodes will be enabled in 2022.\n//Converting to asm allows the hex below to be decoded.',    #List all the OpCodes.
'''//[Sig, PubKey, Preimage, UTX]    #'preturn...' v1.1.1 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. This update reduces fees by up to another 2% by placing <Nonce>DROP @Start, & CODESEPARATOR in-btwn CHECKs.
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
        SIZE  IF  NIP	#[..., scriptSig(2), [SIZE(scriptSig(3)), scriptSig(3:)] ] The next data-push is for 2of2. SIZE decides if it even exists.
                1 SPLIT  SWAP SPLIT    #[..., [SIZE(Script), scriptSig(3:)] ] BIN2NUM unnecessary because the empty redeem Script isn't supported.
        ENDIF  DROP    #[..., Script, 0] Assume "3rd" data-push is final & is redeem Script.
        HASH160  0317a914 SWAP CAT  CAT  0187    #[..., Amount, Script] Predict Outputs for P2SH sender.
ELSE  DROP    #[..., PubKey, 0]
        HASH160  041976a914 SWAP CAT  CAT  0288ac    #[..., Amount, PubKey] Predict Outputs for P2PKH sender.
ENDIF  CAT    #[..., SPLIT(Outputs)] From now is the same for both P2SH & P2PKH.
HASH256  OVER SIZE <32+4+4> SUB SPLIT NIP  0120 SPLIT DROP  EQUALVERIFY    #[..., Preimage, Outputs] VERIFY Outputs==Output is correct. hashOutputs is located 40B from Preimage end.
SHA256  2 PICK SIZE 1SUB SPLIT DROP    #[Sig, PubKey, Preimage] DATASIG is 1 shorter than a SIG.
SWAP  2 PICK  CHECKDATASIGVERIFY CODESEPARATOR CHECKSIG    #[Sig, PubKey, SHA256, Sig[:-1]] VERIFY DATApush==Preimage. Only 1B following CODESEPARATOR must be signed for by PrivKey=1. 

#If the 'preturn...' address is added to a watching-only wallet, this plugin will automatically broadcast the return txns.
#Sender must use a P2PKH or P2SH address, not P2PK. P2PK isn't currently supported by EC.
#P2SH sender must have 3 or 4 data pushes, ≤75B each, in their unlocking sigscript ≤252B. Compressed 1of1, 1of2, 2of2 & VanityTXID are all compatible.
#Sending txn SIZE must be at most 520 Bytes (3 inputs max).
#13 bits minimum for single input (P2PKH sender), but add a couple more bits per extra input.
#It can't return SLP tokens!
#Fee between 7 & 10 bits.
#21 BCH max, but I haven't tested over 10tBCH. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#The sender shouldn't use a PUSHDATA OpCode in the output pkscript (non-standard).
#To return from other addresses requires editing qt.py.
''',
''] #Blanks for 'New' & 'Clear all below'.
CovenantScripts[1]=CovenantScripts[1].replace('Bitwise logic','Bitwise logic (unary & binary)').replace('Locktime','Locktime (unary)').replace('Reserved words','Reserved words (nullary)').replace('BCH','BCH (binary, unary & ternary)')   #This section provides some commentary to OpCodes list.
CovenantScripts[1]=CovenantScripts[1].replace('Splice','Splice (unary)').replace('NUM2BIN  ','NUM2BIN    #Splice (binary)')
CovenantScripts[1]=CovenantScripts[1].replace('Arithmetic','Arithmetic (ternary)').replace('MAX  ','MAX    #Arithmetic (binary)').replace('0NOTEQUAL','0NOTEQUAL    #Arithmetic (unary)')
CovenantScripts[1]=CovenantScripts[1].replace('Crypto','Crypto (binary, multary & unary)').replace('CODESEPARATOR  ','CODESEPARATOR    #Crypto (unary & nullary)')
CovenantScripts[1]=CovenantScripts[1].replace('#Native Introspection','#Native Introspection (unary)').replace('TXLOCKTIME  ','TXLOCKTIME    #Native Introspection (nullary)')

ReturnScripts='''
08070000000345b4077578547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f75817882779402f7019458807c01297f77517f7c01007e817f75517f7c817f77517f7c817f826377517f7c817f826377517f7c7f6875a90317a9147c7e7e01876775a9041976a9147c7e7e0288ac687eaa78820128947f7701207f7588a85279828c7f757c5279bbabac
'''.splitlines()[1:]    #The covenant script hex is only needed by the watching-only wallet. Adding another line here allows wallet to also return from that Script's address, if the fee is correct.
ReturnAddresses=[electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)) for Script in ReturnScripts]

def push_script(script):    #Bugfix for script size 255B.
        if len(script)>>1!=255: return bitcoin.push_script(script)
        else:                   return '4cff'+script
class Plugin(BasePlugin):
    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.windows, self.tabs, self.UIs = {}, {}, {}  #Initialize plugin wallet dictionaries.
  
        Dir=self.parent.get_external_plugin_dir()+'/AutoCove/'
        self.WebP=Dir+'Icon.webp'    #QMovie only supports GIF & WebP. GIF appears ugly. Animating a flag looks too difficult for me.
        if shutil.os.path.exists(Dir): Extract=False   #Only ever extract zip (i.e. install) once.
        else:
            Extract=True
            Zip=zipfile.ZipFile(Dir[:-1]+'-Plugin.zip')
            Zip.extract('AutoCove/Icon.webp',Dir[:-9])
        if Extract: Zip.close()
        self.Icon=QIcon()   #QMovie waits for init_qt. self.Icon isn't necessary, but I suspect it's more efficient than calling QIcon for all wallets.
    def on_close(self):
        """BasePlugin callback called when the wallet is disabled among other things."""
        del self.Movie  #Movies are special and must be deleted.
        {self.close_wallet(window.wallet) for window in self.windows.values()}
        shutil.rmtree(self.parent.get_external_plugin_dir()+'/AutoCove')
    @hook
    def init_qt(self, qt_gui):
        """Hook called when a plugin is loaded (or enabled)."""
        if self.UIs: return # We get this multiple times.  Only handle it once, if unhandled.
        self.Movie=QMovie(self.WebP)    
        self.Movie.frameChanged.connect(self.setTabIcon), self.Movie.start()
        {self.load_wallet(window.wallet, window) for window in qt_gui.windows}  # These are per-wallet windows.
    @hook
    def load_wallet(self, wallet, window):
        """Hook called when a wallet is loaded and a window opened for it."""
        wallet_name = wallet.basename()
        self.windows[wallet_name] = window
        l = UI(window, self)
        tab = window.create_list_tab(l)
        self.tabs[wallet_name],self.UIs[wallet_name] = tab,l
        window.tabs.addTab(tab,self.Icon, 'AutoCove') #Add Icon instantly in case WebP frame rate is slow.
    @hook
    def close_wallet(self, wallet):
        wallet_name = wallet.basename()
        del self.UIs[wallet_name]   #Delete UI now to stop Movie's tab connection, before tab removed.
        window = self.windows[wallet_name]
        window.tabs.removeTab(window.tabs.indexOf(self.tabs[wallet_name]))
        del self.tabs[wallet_name]
    def setTabIcon(self):
        self.Icon.addPixmap(self.Movie.currentPixmap())
        for wallet_name in self.UIs.keys():
            Tabs=self.windows[wallet_name].tabs
            Tabs.setTabIcon(Tabs.indexOf(self.tabs[wallet_name]),self.Icon)
class UI(QDialog):
    def __init__(self, window, plugin):
        QDialog.__init__(self, window)
        self.window, self.plugin = window, plugin
        self.Scripts, self.Colors, self.ColorDict = (Object.copy() for Object in (CovenantScripts, Colors, ColorDict) )  #Create new copy for each wallet's memory.

        self.Thread, self.UTXOs, self.Selection = threading.Thread(), {}, ''    #Empty thread, set of UTXOs to *skip* over, & *previous* Selection for highlighting. A separate thread delays auto-broadcasts so wallet has time to analyze history. If main thread is delayed, then maybe it can't analyze the wallet's history.
        window.history_updated_signal.connect(self.history_updated) #This detects preturn UTXOs. A password is never necessary to loop over UTXOs.
        window.addr_converter_button.clicked.connect(self.ConverterClicked)   #Toggle CashAddr.
        
        self.HiddenBox=QTextEdit()  #HiddenBox connection allows broadcasting from sub-thread, after sleeping.
        self.HiddenBox.textChanged.connect(self.broadcast_transaction)

        self.ColorsBox = QCheckBox('Colors')
        self.ColorsBox.setToolTip('Slows down typing, selections, etc.\nNot sure how colors should be assigned.')
        self.ColorsBox.setChecked(True), self.ColorsBox.toggled.connect(self.ColorsToggled)
        
        self.BlackBox = QCheckBox('Black')
        self.BlackBox.setToolTip('Background color toggle.')
        
        self.CaseBox=QComboBox()
        self.CaseBox.addItems('codes Codes CODES OP_CODES Op_Codes op_codes'.split())
        self.CaseBox.setCurrentIndex(2)
        self.CaseBox.activated.connect(self.CaseBoxActivated), self.CaseBox.highlighted.connect(self.CaseBoxHighlighted)

        self.AsmBox, self.AsmBool, self.AsmIndex = QComboBox(), False, 0  #AsmBool remembers whether 'hex' or 'asm' was already selected. AsmIndex is more general (2 for <dec>). A future update could combine these, if more elegant.
        self.AsmBox.addItems('hex asm <±dec> <±0b...> <±0o...> <±0x...>'.split())
        self.AsmBox.setToolTip('Select asm before inserting CashScript bytecode.\nNot all data can be converted to <dec>.\nDisable colors for more speed.\nTo convert 1→<1> etc, choose <dec> & OP_CODES.\nSpecial <#>s can be observed.\ndec, bin, oct & hex are supported.')
        self.AsmBox.activated.connect(self.AsmBoxActivated), self.AsmBox.highlighted.connect(self.AsmBoxHighlighted)
        
        self.FontBox = QComboBox()
        self.FontBox.addItems('Default font,Consolas'.split(','))
        self.FontBox.setToolTip("Font.\nConsolas is Notepad's default, PointSize(11), & has no kerning.")
        self.FontBox.activated.connect(self.FontBoxActivated), self.FontBox.highlighted.connect(self.FontBoxHighlighted)

        Title=QLabel('v1.1.1')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)
        
        SaveButton = QPushButton('Save HTML')
        SaveButton.clicked.connect(self.SaveButtonClicked)
        
        LineButton = QPushButton('1 line')
        LineButton.setToolTip('Strips out all comments.\nConvert to OP_CODES & asm to generate CashScript bytecode.\nTemporarily enables LineWrap.\nDisable colors for more speed.')
        LineButton.clicked.connect(self.LineButtonClicked)
        
        self.ScriptsBox = QComboBox()
        self.ScriptsBox.setToolTip('New auto-decodes are stored here.\nasm form not stored.\nDisable colors for more speed.')
        self.ScriptsBox.addItems('New,OpCodes List,preturn... v1.1.1,Clear all below'.split(','))
        self.ScriptsBox.activated.connect(self.ScriptActivated), self.ScriptsBox.highlighted.connect(self.ScriptsBoxHighlighted)
        self.KeepScriptsIndex = False   #Normally False. Whenever text changes, combo-box switches to 'New'.

        HBoxTitle=QHBoxLayout()
        {HBoxTitle.addWidget(Widget) for Widget in (self.ColorsBox, self.BlackBox, self.CaseBox, self.AsmBox)}
        if not DarwinBool: HBoxTitle.addWidget(self.FontBox) #Consolas isn't working on macOS.
        {HBoxTitle.addWidget(Widget) for Widget in (LineButton, SaveButton, self.ScriptsBox, Title)}
        
        InfoLabel = QLabel("Decode P2SH redeem Script hex by pasting it below. Paste txn or its TXID (or URL) to decode. Drag & drop .artifact &/or .txn files.") 
        InfoLabel.setToolTip("Only P2SH sigscripts are ever decoded.\nIf file is too large (e.g. 1GB) EC crashes.\nURL needs a TXID in its .split('/')\nAuto-indents are 8 spaces.\nΔ is the stack's depth change for each line, unavailable for IFDUP & CHECKMULTISIGs.\nUndo & Redo unavailable.")
        
        self.ScriptBox=QTextEdit()
        self.ScriptBox.setUndoRedoEnabled(False)    #Undo etc can be enabled in a future version, using QTextDocument. IDE is unsafe without both save & undo. Unfortunately clicking btwn 2 lines often moves the cursor to line end.
        self.ScriptBox.setAcceptRichText(False), self.ScriptBox.setTabStopWidth(24) # 3=default space-bar-width, so 24=8 spaces. Don't allow copy-paste of colors or font into box (so font is permanently default).
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)
        
        DefaultFont = self.ScriptBox.font()
        self.Family, self.PointSize = DefaultFont.family(), DefaultFont.pointSize()
        
        self.HexBox=QTextEdit()
        self.HexBox.setReadOnly(True)

        self.AddressLabel=QLabel()
        self.AddressLabel.setToolTip("Start Electron-Cash with --testnet or --testnet4 to generate bchtest addresses.")
        self.CountLabel=QLabel()
        HBoxAddress=QHBoxLayout()
        {HBoxAddress.addWidget(Widget) for Widget in (self.AddressLabel, self.CountLabel)}
        self.CountLabel.setAlignment(Qt.AlignRight)
        self.CountLabel.setToolTip("Limits are 201 Ops & 520 Bytes.\nops with values ≤0x60 don't count.")
        
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, InfoLabel, self.CountLabel, self.AddressLabel}}
        self.BlackBox.toggled.connect(self.BlackToggled)    #This section initializes starting Script.
        try: 
            if 'dark' not in window.config.user_config['qt_gui_color_theme']: raise

            self.Dark, self.pColor = True, '<font color=lightblue>'  #RTF string is used whenever calculating the BCH address with p (or 3) Color.
            self.BlackBox.setChecked(True)  #Black by default. 
        except: self.Dark, self.pColor = False, '<font color=blue>'
        self.ScriptActivated()    #Assembly Script dumped onto HexBox, to set labels.

        VBox=QVBoxLayout()
        VBox.addLayout(HBoxTitle), VBox.addWidget(InfoLabel)
        VBox.addWidget(self.ScriptBox,10), VBox.addWidget(self.HexBox,1)  #Script bigger than hex. Dunno how to set a dynamic or adjustable height on HexBox.
        VBox.addLayout(HBoxAddress)
        
        self.setLayout(VBox)
        self.setAcceptDrops(True), self.ScriptBox.setAcceptDrops(False)    #Drag & drop. Don't want "file: URI" inserted into ScriptBox, instead.
    def history_updated(self):
        if self.Thread.is_alive(): return    #Don't double broadcast the same return.
        self.Thread=threading.Thread(target=self.ThreadMethod)
        self.Thread.start()
    def ThreadMethod(self):
        time.sleep(2)   #1sec may not be long enough for wallet to fully analyze newly imported 'preturn...'.
        window=self.window
        if not window.network.is_connected(): return
        
        wallet=window.wallet
        for UTXO in wallet.get_utxos():
            if (UTXO['prevout_hash'], UTXO['prevout_n']) in self.UTXOs.items(): continue    #UTXOs to skip over.
            self.UTXOs[UTXO['prevout_hash']]=UTXO['prevout_n']
        
            try: index=ReturnAddresses.index(UTXO['address'])
            except: continue    #Not an AutoCove UTXO.
            UTX=electroncash.Transaction(wallet.storage.get('transactions')[UTXO['prevout_hash']])
            
            SInput = UTX.inputs()[0]    #Spent Input. The sender demands their money returned. Covenant assumes input 0 is sender.
            if 'unknown' in SInput['type']: ReturnAddress=electroncash.address.Address.from_multisig_script(bitcoin.bfh(electroncash.address.Script.get_ops(bitcoin.bfh(SInput['scriptSig']))[-1][-1].hex()))   #Calculate return address from scriptSig.
            else:                           ReturnAddress=SInput['address'] #EC appears to have trouble resolving 'unknown' senders.
            
            Amount = UTXO['value']-(503+UTX.estimated_size())
            if Amount<546: continue #Dust limit
            
            TX=UTX  #Copy nLocktime.
            TX.inputs().clear(), TX.outputs().clear()
            TX.outputs().append((0,ReturnAddress,Amount))    #Covenant requires this exact output, and that it's the only one.
            
            UTXO['type'], UTXO['scriptCode'] = 'unknown', HexDict['CHECKSIG']  #scriptCode is the B following the only CODESEPARATOR.
            TX.inputs().append(UTXO)    #Covenant requires return TX have only 1 input.

            PreImage=TX.serialize_preimage(0)
            PrivKey=(1).to_bytes(32,'big')
            PubKey=bitcoin.public_key_from_private_key(PrivKey,compressed=True)  #Secp256k1 generator. 
            Sig=electroncash.schnorr.sign(PrivKey,bitcoin.Hash(bitcoin.bfh(PreImage)))
            TX.inputs()[0]['scriptSig']=push_script(Sig.hex()+'41')+push_script(PubKey)+push_script(PreImage)+push_script(UTX.raw)+push_script(ReturnScripts[index])
            TX=TX.serialize()
            if TX!=self.HiddenBox.toPlainText(): self.HiddenBox.setPlainText(TX)    #Don't double broadcast!
    def broadcast_transaction(self): self.window.broadcast_transaction(electroncash.Transaction(self.HiddenBox.toPlainText()),None)  #description=None.
    def textChanged(self):  #Whenever users type, attempt to re-compile.
        if self.ScriptBox.lineWrapMode(): self.ScriptBox.setLineWrapMode(QTextEdit.NoWrap)
        
        Script, ScriptsIndex =self.ScriptBox.toPlainText(), self.ScriptsBox.currentIndex()
        if self.ScriptsBox.currentIndex() and Script!=self.Scripts[ScriptsIndex]:
            if self.KeepScriptsIndex: self.KeepScriptsIndex = False   #Reset, i.e. when converting to asm.
            else: self.ScriptsBox.setCurrentIndex(0)     #New script.
        Bytes=b''   #This section is the decoder. Start by checking if input is only 1 word & fully hex. Then check if an URL containing TXID, TX or TXID.
        if '\n' not in Script and 1==len(Script.split()):    #Only attempt to decode a single word (bugfix for e.g. '00 NIP')
            ScriptLow = Script.lower().replace('0x','') #Accept 0x hex code, as well. 
            for String in ScriptLow.split('/'):    #This section can extract 1st TXID from URL, as long as its the only len 64 (or 66 with 0x) hex sub-string in .split('/').
                if 64==len(String) and all(Char in '0123456789abcdef' for Char in String):
                    ScriptLow = String
                    break
            ScriptHex=ScriptLow.split()[0]  #.split allows accepting input containing a tab, e.g. TXID from a list in notepad.
            try:    #Check if hex.
                Bytes=bitcoin.bfh(ScriptHex)
                try:
                    TX=electroncash.Transaction(ScriptHex)
                    Inputs=TX.inputs()
                    Inputs[0] and TX.outputs()[0]   #Check there's at least 1 input & output, or else not a TX.
                    TXID, ColorsBool = TX.txid_fast(), self.ColorsBox.isChecked()
                    self.ColorsBox.setChecked(False)    #Disable colors for decoding loop, then re-enable.
                    self.InputN, self.TXIDComment = 0, '/'+str(len(Inputs))+' from TXID '+TXID  #Remember input # & TXID for auto-comment. Could also state locktime (last 4B). To get each input value, TX.fetch_input_data & TX.fetched_inputs could be used but that required a time.sleep delay to download all input txns.
                    for Input in Inputs:
                        self.InputN += 1    #Start counting from 1.
                        if Input['type'] in {'p2sh','unknown'}:    #'p2sh' is usually multisig, but 'unknown' also has a Script.
                            self.get_ops = electroncash.address.Script.get_ops(bitcoin.bfh(Input['scriptSig']))
                            self.ScriptBox.setPlainText(self.get_ops[-1][-1].hex())  #Script to decode.
                    del self.TXIDComment    #Or else Script decoder may think it's decoding a TX.
                    self.ColorsBox.setChecked(ColorsBool)
                    if Script==self.ScriptBox.toPlainText(): self.ScriptBox.setText('#No P2SH sigscript for TXID '+TXID), self.setTextColor()   #gray out comment.
                    return
                except:    #Not a TX, so check if TXID.
                    network=self.window.network
                    if 64==len(ScriptHex) and network.is_connected():
                        Get = network.get_raw_tx_for_txid(ScriptHex)   #This can cause a hang or crash if network is disconnected but can't tell. Threading seems too complicated.
                        if Get[0]:  #TXID==ScriptHex
                            self.ScriptBox.setPlainText(Get[1])
                            return
            except: pass    #Not hex.
        if Bytes:
            endlEither = 'IF NOTIF ELSE ENDIF RETURN VER VERIF VERNOTIF'.split()   #New line before & after these OpCodes.
            endlBefore = endlEither+['CODESEPARATOR']   #CODESEPARATOR often appears in a triple preceding a CHECKDATASIG & a CHECKSIG.
            endlAfter  = endlEither+'NUM2BIN BOOLAND'.split()    #NUM2BIN & BOOLAND may look good at line ends.
            Script, endl, IndentSize = '', '\n', 8 #endl gets tabbed after IFs (IF & NOTIF) etc. Try 8 spaces, because default font halves the space size.
            Size, SizeSize, Count, OpCount, Δ = 0, 0, 0, 0, 0  #Size count-down of "current" data push. SizeSize is the "remaining" size of Size (0 for 0<Size<0x4c). Count is the # of Bytes on the current line. Target min of 1 & max of 21, bytes/line. OpCount is for the current line. Δ counts the change in stack depth.
            try:
                for Tuple in self.get_ops[:-1]:
                    Script += '//'
                    try:
                        if not Tuple[1]: raise  #To be consistent with Blockchain.com, list empty push as OP_0.
                        Script   += Tuple[1].hex()    #Show full stack leading to redeem Script as asm comments when decoding a scriptSig.
                        ByteCount = ', '+str(len(Tuple[1]))+'B push'
                    except:   #Sigscript may push OP_N instead of data.
                        try:    Int = Tuple[0]
                        except: Int = Tuple   #SLP Ed.
                        Script   += 'OP_'+CodeDict[bitcoin.int_to_hex(Int)]
                        ByteCount = ''  
                    Script += ' '*IndentSize+'#+1Δ, 0 ops'+ByteCount+endl #No OP_EXEC means never any ops from push-only data-pushes.
                self.get_ops=[] #Delete per input.
            except: pass    #Not decoding a scriptSig with more than a redeem Script.
            
            def endlComment(Script,Δ,OpCount,Count,endl): #This method is always used to end lines in the redeem Script, when decoding.
                if Δ==None: ΔStr = ''
                else:       ΔStr = (Δ>=0)*'+'+str(Δ)+'Δ, '  #+ indicates 
                ops  = ' op'+'s'*(OpCount!=1)+', '
                return Script+' '*(IndentSize-1)+'#'+ΔStr+str(OpCount)+ops+str(Count)+'B'+endl, 0, 0, 0    #Reset Δ, OpCount & Count to 0.
            endlAfterDROP = True    #A Script may start with <Nonce>DROP for a vanity address. endlBefore <Nonce>DROP would be trickier. If Script starts with DROP, it still ends the 1st line due to implied malleability.
            for Byte in Bytes:
                Hex=bitcoin.int_to_hex(Byte)  #Byte is an int.
                if SizeSize or Size: Count+=1
                if SizeSize:    #This section is for PUSHDATA1,2&4.
                    SizeSize-=1
                    SizeHex +=Hex
                    if not SizeSize:    #SizeHex is complete.
                        Size = int(bitcoin.rev_hex(SizeHex),16) #This is the data-push size.
                        Script+=SizeHex
                    continue
                if Size:  #This section is for all data pushes. 
                    Size  -=1
                    Script+=Hex
                    if not Size: #End of data push.
                        Script+=' '
                        if Count>=21: Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount,Count,endl)   #Large data pushes (e.g. HASH160) get their own line.  At most 21B per line. A HASH160 requires 1+20 bytes.
                    endlAfterDROP = True
                    continue
                try:    #OpCode or else new data push.
                    CODE=CodeDict[Hex]
                    if CODE in {'ENDIF','ELSE'}:
                        endl='\n'+endl[ 1+IndentSize : ] #Subtract indent for ENDIF & ELSE.
                        if not Count and Script[-IndentSize:]==' '*IndentSize: Script=Script[:-IndentSize]    #Subtract indent back if already on a new line.
                    if Count and (CODE in endlBefore or 'RESERVED' in CODE or 'PUSHDATA' in CODE): Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount, Count, endl)    #New line before any RESERVED or PUSHDATA.
                    if CODE in {'VERIF', 'VERNOTIF'}: Script=Script.rstrip(' ')   #No tab before these since script will fail no matter what.
                    Script  += CODE+' '
                    Count   += 1
                    OpCount += Byte>0x60 #Only these count towards 201 limit.
                    try:   Δ+= DepthDict[CODE]
                    except:Δ = None
                    if CODE in {'ELSE', 'IF', 'NOTIF'}: endl+=' '*IndentSize #Add indent after ELSE, IF & NOTIF.
                    elif 'PUSHDATA' in CODE: SizeHex, SizeSize = '', 2**(Byte-0x4c)  #0x4c is SizeSize=1. SizeHex is to be the little endian hex form of Size.
                    if Count>=21 or CODE in endlAfter or any(Word in CODE for Word in {'RESERVED', 'VERIFY'}) or (endlAfterDROP and CODE=='DROP'): Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount,Count,endl)   #New line *after* any VERIFY or RESERVED. A <Nonce>DROP also demands its own endlAfter (& maybe endlBefore).
                except:
                    Size = Byte
                    if Count and Count+Size>=21: Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount,Count,endl)  #New line before too much data.
                    Script += Hex
                    Count  += 1
                    try: Δ += 1
                    except: pass    #Δ may be None.
                if endlAfterDROP: endlAfterDROP = False
            if Count: Script = endlComment(Script,Δ,OpCount,Count,'')[0]
            Script = Script.rstrip(' ')+'\n'*(Count>0)+'#Auto-decode'   #Final comment shows up like a VERIF.
            try: Script += ' of input '+str(self.InputN)+self.TXIDComment    #Txn inputs get a longer comment than plain redeem Script.
            except: pass
            
            if not (Size or SizeSize):   #Successful decode is plausible if all data-pushes completed successfully.
                try:  #No exact duplicates stored in memory.
                    ScriptsIndex = self.Scripts.index(Script)
                    self.ScriptsBox.setCurrentIndex(ScriptsIndex)
                except: #This section adds the Auto-decode to memory in the combo-box.
                    self.Scripts.append(Script)
                    self.ScriptsBox.addItem(''), self.ScriptsBox.setCurrentText('') #Don't know what address yet to use as Script name.
                    ScriptsIndex = self.ScriptsBox.currentIndex()   #Keep track of this because activating the Script can cause it to change to 0 due to Asm-conversion.
                self.HexBox.clear(), self.ScriptActivated()   #Clearing HexBox ensures new colors, in case the same Script is being decoded.
                self.ScriptsBox.setItemText(ScriptsIndex, self.Address)
                return  #textChanged signal will return to below this point. Decoder ends here.
        if self.ColorsBox.isChecked():  #This section greys out typed '#' even though they don't change bytecode.
            Cursor=self.ScriptBox.textCursor()
            Format=Cursor.charFormat()
            position=Cursor.position()
            if Script and '#'==Script[position-1] and Qt.gray!=Format.foreground():
                Format.setForeground(Qt.gray)
                Cursor.setPosition(position-1), Cursor.setPosition(position,Cursor.KeepAnchor), Cursor.setCharFormat(Format), Cursor.clearSelection()
                self.ScriptBox.setTextCursor(Cursor)
                return  #signal brings us back to below here.
        Script, OpCount = self.ScriptToHex(Script,False)    #OpCount could also be calculated using EC's .get_ops
        if Script and Script==self.HexBox.toPlainText(): return    #Do nothing if no hex change, unless empty (not much work).
        self.HexBox.setPlainText(Script)
        
        OpCount, ByteCount = str(OpCount)+' Op'+(OpCount!=1)*'s'+' & ', str(len(Script)>>1)+' Bytes' #Set Count QLabels.
        self.CountLabel.setText('is the BCH address for the redeem Script above (if valid) with              '+OpCount+ByteCount)
        
        try:    #Set Address QLabel.
            Bytes = bitcoin.bfh(Script)
            self.Address=electroncash.address.Address.from_multisig_script(Bytes).to_ui_string()
        except: self.Address = '_'*42   #42 chars typically in CashAddr. Script invalid.
        self.SetAddress()
        if self.ColorsBox.isChecked(): self.setTextColor()
    def ScriptToHex(self,Script,BypassErrors):
        Assembly=''.join(Line.split('#')[0].split('//')[0].upper()+' ' for Line in Script.splitlines()).split()    #This removes all line breaks & comments from assembly code, to start encoding. Both # & // supported.
        Hex, OpCount = '', 0
        for Str in Assembly:
            try:
                if self.AsmBool and Str in Codes1N: raise #1N in Asm means 011N.
                ByteHex =HexDict[Str.replace('OP_','')]
                Hex    +=    ByteHex
                OpCount+=int(ByteHex,16)>0x60
            except:
                if Str.startswith('<') or Str.endswith('>'): #<dec>
                    Hex += self.DecToHex(Str,BypassErrors)
                    continue
                if BypassErrors: #Must be hex to return. e.g. selecting 'R OR' highlights all instances of 0x85.
                    try: bitcoin.bfh(Str)
                    except: continue
                if self.AsmBool: Hex+=push_script(Str.lower())
                else:            Hex+=            Str.lower()
        return Hex, OpCount
    def DecToHex(self,Str,BypassErrors):
        Str = Str.replace('<','').replace('>','')
        try:    #dec
            Int = eval(Str)
            if  -1==Int:     return HexDict['1NEGATE']   #e.g. 0181 can't (or shouldn't, I haven't checked) happen.
            elif -1<Int<=16: return HexDict[str(Int)]    #0→16. 00 becomes 0. e.g. 0110 can't ever happen.
            else:   #Data-push.
                Str = hex(abs(Int))[2:]
                if   len(Str)%2:        Str = '0' +Str  #Even # of digits.
                elif int(Str[0],16)>=8: Str = '00'+Str  #Big # needs leading '00' or else -ve.
                if Int<-1: Str=hex(int(Str[0],16)+8)[-1]+Str[1:]  #Activate leading bit. I think Bitcoin's -ve bytecode is non-standard.
                return push_script(bitcoin.rev_hex(Str))    #Little endian.
        except:    #Not dec.
            if BypassErrors: return ''
            else:            return Str.lower()
    def ScriptsBoxHighlighted(self,Index):
        Box = self.ScriptsBox
        if Index>=len(CovenantScripts) and Index!=Box.currentIndex(): Box.setCurrentIndex(Index), self.ScriptActivated()   #Highlighted → Activated, but only if current & future Scripts are from decoder memory.
    def ScriptActivated(self):    #Change redeem script with correct case.
        Index, self.AsmBool, self.AsmIndex = self.ScriptsBox.currentIndex(), False, 0    #Loading into asm or <dec> requires artificially toggling since memory is always in hex.
        if Index==3:   #This section is for 'Clear below'. Maybe gc.collect() could fit in.
            {self.ScriptsBox.removeItem(4) for ItemN in range(4,len(self.Scripts))}
            self.Scripts, Index = self.Scripts[:4], 0   #0 sets to 'New'.
        self.ScriptBox.setPlainText((self.Scripts[Index])), self.ScriptsBox.setCurrentIndex(Index), self.CaseBoxActivated(), self.AsmBoxActivated()
        if self.ColorsBox.isChecked(): self.setTextColor()   #Color even if no change in bytecode or hex/asm.
    def SetAddress(self):
        if self.Address and self.ColorsBox.isChecked(): self.AddressLabel.setText(self.pColor+self.Address[0]+"</font>"+self.Address[1:])
        else:                                           self.AddressLabel.setText(                                      self.Address)
    def setTextColor(self):
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Format, CursorPos = Cursor.charFormat(), Cursor.position()
        Format.setForeground(self.Colors['Data']), Format.setBackground(Qt.transparent)
        
        Cursor.setPosition(0), Cursor.movePosition(Cursor.End,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All black. This line guarantees fully transparent background.
        HexCursor.setPosition(0), HexCursor.movePosition(HexCursor.End,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)
        if self.ColorsBox.isChecked():   #This can max out a CPU core when users hold in a button like '0'. A future possibility is only coloring the current word, unless copy/paste detected.
            StartPosit, HexPos, SizeSize = 0, 0, 2    #Line's absolute position, along with HexBox position. SizeSize is the # of hex digits which are colored in blue, by default.
            ForegroundColor = self.Colors['Constants']   #This tracks whether a PUSHDATA color should be used for the data-push size.
            for Line in Text.splitlines():
                LineCode=Line.split('#')[0].split('//')[0].upper()
                CommentPos, Pos, lenLine = len(LineCode), StartPosit, len(Line)  #Comment posn, virtual cursor position.
                for Word in LineCode.split():
                    Find, lenWord = LineCode.find(Word), len(Word)
                    Pos+=Find
                    Cursor.setPosition(Pos), HexCursor.setPosition(HexPos)   #This removes Anchor.
                    try:    #to color in Word as OpCode
                        if self.AsmBool and Word in Codes1N: raise #1N not an OpCode in Asm.
                        else: Format.setForeground(self.ColorDict[Word.replace('OP_','')])
                        Pos+=lenWord
                        Cursor   .setPosition(   Pos,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)
                        HexPos+=2
                        HexCursor.setPosition(HexPos,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        
                        if 'PUSHDATA' in Word:
                            ForegroundColor = self.Colors['PushData']
                            if   Word.endswith('2'): SizeSize = 4  # of blue digits to follow.
                            elif Word.endswith('4'): SizeSize = 8
                    except: #Assume data push
                        Format.setForeground(ForegroundColor)   #Color 1st SizeSize chars blue if not an opcode.
                        if ForegroundColor!=self.Colors['Constants']: ForegroundColor=self.Colors['Constants']  #Reset
                        
                        lenHex = lenWord
                        if Word.startswith('<') or Word.endswith('>'): #<dec>
                            lenHex = len(self.DecToHex(Word,False))
                            if 2==lenHex: Cursor.setPosition(Pos+lenWord,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All blue, since an OpCode.
                            else:   #< & > turn blue!
                                Cursor.setPosition(Pos+1,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                                if Word.endswith('>'): Cursor.setPosition(Pos+lenWord-1), Cursor.setPosition(Pos+lenWord,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                        elif self.AsmBool:
                            if   lenWord > 0xff<<1: SizeSize = 6    #4d____ is 4 extra digits, on top of 2. 6 total only happens for Asm.
                            elif lenWord > 0x4b<<1: SizeSize = 4    #4c__   is 2 extra digits.
                            lenHex+=SizeSize   #Asm jumps ahead in HexPos.
                        else: Cursor.setPosition(Pos+SizeSize,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #No leading blue bytes for Asm.
                        HexCursor.setPosition(HexPos+SizeSize,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        Pos   +=lenWord
                        HexPos+=lenHex
                        if SizeSize!=2: SizeSize=2  #Reset to coloring in 2 digits as blue.
                    LineCode=LineCode[Find+lenWord:]
                Cursor.setPosition(StartPosit+CommentPos)   #This section greys out the comments. '//' & '#' are the same, but Qt.darkGray or Qt.lightGray could also work for '//'.
                StartPosit+=lenLine
                if CommentPos<lenLine:
                    Format.setForeground(Qt.gray)
                    Cursor.setPosition(StartPosit,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                StartPosit+=1 #'\n' is 1 Byte. Do this last in case '#' is on last line.
        Cursor.setPosition(CursorPos), HexCursor.setPosition(0)
        self.ScriptBox.setTextCursor(Cursor), self.HexBox.setTextCursor(HexCursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)
    def selectionChanged(self): #Highlight all instances of selected word. Also does byte search of hex. Method is a bit weak without bracket detection, like in Notepad++.
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText().upper(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Format, Selection, CursorPos, selectionStart, selectionEnd = Cursor.charFormat(), Cursor.selectedText().upper(), Cursor.position(), Cursor.selectionStart(), Cursor.selectionEnd()
        
        if Selection==self.Selection: return    #Do nothing if Selection hasn't changed.
        else: self.Selection=Selection

        Format.setForeground(Colors['SelectionForeground']), Format.setBackground(Colors['SelectionBackground'])
        self.setTextColor() #Undo any previous highlighting, & disconnect.
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        
        Find, Pos, lenSelection = Text.find(Selection), 0, len(Selection)   #Virtual cursor position.
        while Selection and Find>=0:    #Ignore empty selection.
            Pos+=Find
            Cursor.setPosition(Pos)
            Pos+=lenSelection
            Cursor.setPosition(Pos,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
            Text=Text[Find+lenSelection:]
            Find=Text.find(Selection)
        if CursorPos>selectionStart: Cursor.setPosition(selectionStart)
        else:                        Cursor.setPosition(selectionEnd) #Right-to-left selection.
        Cursor.setPosition(CursorPos,Cursor.KeepAnchor), self.ScriptBox.setTextCursor(Cursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        SelectionHex = self.ScriptToHex(Selection,True)[0]  #[1] is OpCount.
        try: Bytes, SelectionBytes = bitcoin.bfh(self.HexBox.toPlainText()), bitcoin.bfh(SelectionHex)
        except: return  #Don't do anything if HexBox ain't valid.
        Find, Pos, lenSelectionHex, lenSelectionBytes = Bytes.find(SelectionBytes), 0, len(SelectionHex), len(SelectionBytes)
        while SelectionBytes and Find>=0:
            Pos+=Find*2
            HexCursor.setPosition(Pos)
            Pos+=lenSelectionHex
            HexCursor.setPosition(Pos,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)
            Bytes=Bytes[Find+lenSelectionBytes:]
            Find=Bytes.find(SelectionBytes)
        HexCursor.setPosition(0), self.HexBox.setTextCursor(HexCursor)
    def ColorsToggled(self):
        self.Selection=None   #Force re-selection, now w/ or w/o Colors.
        self.SetAddress(), self.selectionChanged(), self.ScriptBox.setFocus()   #QCheckBox steals focus.
    def CaseBoxHighlighted(self,Index): self.CaseBox.setCurrentIndex(Index), self.CaseBoxActivated()   #Highlighted → Activated.
    def CaseBoxActivated(self):   #Change btwn Codes, CODES & OP_CODES using QTextCursor. This is more complicated but possibly quicker than editing strings directly.
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()   #disconnect & connect isn't necessary.
        Script, Cursor, Index = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.CaseBox.currentIndex()
        CursorPos, StartPosit, selectionStart, selectionEnd = Cursor.position(), 0, Cursor.selectionStart(), Cursor.selectionEnd()    #StartPosit is each line's starting posn. Retain selection highlighting.
        lenChangeSum, CursorFound = 0, False    #To re-locate CursorPos after changing many words.
        for Line in Script.splitlines():
            LineCode=Line.split('#')[0].split('//')[0].upper()
            Pos, lenLine = StartPosit, len(Line)  #Comment posn, virtual cursor position.
            if not CursorFound and Pos>=CursorPos+lenChangeSum: CursorFound=True    #Sometimes a new line finds the cursor. It'd be slightly more efficient to make a new variable CursorPosNew=CursorPos+lenChangeSum
            for Word in LineCode.split():
                Find, lenWord = LineCode.find(Word), len(Word)
                Pos+=Find
                Cursor.setPosition(Pos)
                Pos+=lenWord
                Cursor.setPosition(Pos,Cursor.KeepAnchor)

                CODE=Word.replace('OP_','')
                try:
                    if self.AsmBool and CODE in Codes1N:
                        if Word.startswith('OP_'): insertWord = (Index in {2,3})*'OP_' + (Index in {1,4})*'Op_' + (Index in {0,5})*'op_' + CODE   #Asm requires leading _1N.
                        else:                      insertWord = Word #Bugfix for 1N → OP_1N when it's actually 011N
                    elif Index>=3 and 2==self.AsmIndex and CODE.isdecimal() and 0<=int(CODE)<=16: insertWord = '<'+CODE+'>'   #<DEC> is fewer characters than OP_DEC. <DEC> instead of DEC is OK, though.
                    else: insertWord = (Index==3)*'OP_' + (Index==4)*'Op_' + (Index==5)*'op_' + (Index in {2,3})*CODE + (Index in {1,4})*CaseDict[CODE][0] + (Index in {0,5})*CaseDict[CODE][1]
                    lenChange=len(insertWord)-lenWord
                    Cursor.insertText(insertWord)
                    Pos       +=lenChange
                    StartPosit+=lenChange
                    if not CursorFound: lenChangeSum+=lenChange #Keep track of changing cursor position.
                except: pass    #Word isn't an OpCode.
                if not CursorFound and Pos>=CursorPos+lenChangeSum: CursorFound=True
                LineCode=LineCode[Find+lenWord:]
            StartPosit+=lenLine+1
        CursorPos     +=lenChangeSum    #This section just re-selects what was started with. Extra code would be needed to track multi-word selections, since the selection size changes with OP_ etc.
        selectionStart+=lenChangeSum
        selectionEnd  +=lenChangeSum
        if CursorPos>selectionStart: Cursor.setPosition(selectionStart)
        else:                        Cursor.setPosition(selectionEnd) #Right-to-left selection.
        Cursor.setPosition(CursorPos,Cursor.KeepAnchor), self.ScriptBox.setTextCursor(Cursor)

        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)    #Reconnect before re-selecting.
        self.Selection=None #Force re-selection after changing spells.
        self.selectionChanged(), self.ScriptBox.setFocus()    #Return focus to Selection.
    def AsmBoxHighlighted(self,Index): self.AsmBox.setCurrentIndex(Index), self.AsmBoxActivated()   #Highlighted → Activated.
    def AsmBoxActivated(self):  #This method strips out blue leading bytes (asm), or else puts them back in. QTextCursor is used. <dec>, bin & oct conversion, via hex, also. Doesn't maintain selection.
        Index = self.AsmBox.currentIndex()
        AsmBool = 1==Index
        if Index == self.AsmIndex: return   #Do nothing if untoggled.
        if Index:   #Always fully convert to hex before attempting to convert to asm or <dec>.
            ColorsBool = self.ColorsBox.isChecked() #Disable colors for intermediate conversion.
            if not self.AsmIndex: self.AsmIndex = None
            self.ColorsBox.setChecked(False), self.AsmBoxHighlighted(0), self.AsmBox.setCurrentIndex(Index), self.ColorsBox.setChecked(ColorsBool)
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Script, Cursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor()
        CursorPos, StartPosit, SizeSize = Cursor.position(), 0, 2    #StartPosit is each line's starting posn. SizeSize is the # of leading digits (in a data-push) to delete for coversion to asm.
        
        def FromDec(Dec):
            if   Index==3: return bin(Dec) #→<±0b...>
            elif Index==4: return oct(Dec) #→<±0o...>
            elif Index==5: return hex(Dec) #→<±0x...>
        for Line in Script.splitlines():
            LineCode=Line.split('#')[0].split('//')[0]
            Pos, lenLine = StartPosit, len(Line)  #Comment posn, virtual cursor position.
            for Word in LineCode.split():
                Find, lenWord, insertWord = LineCode.find(Word), len(Word), Word
                Pos+=Find
                Cursor.setPosition(Pos)
                Pos+=lenWord
                Cursor.setPosition(Pos,Cursor.KeepAnchor)

                try:
                    WordUp = Word.upper().replace('OP_','')
                    HexDict[WordUp] #If OpCode, usually do nothing.
                    if Index and 'PUSHDATA' in WordUp:
                        insertWord = ''  #Strip PUSHDATA OpCodes for asm or <dec> conversion. For <dec>, if data isn't a #, re-insert PUSHDATA later on.
                        if   WordUp.endswith('2'):  SizeSize = 4  # of leading digits to delete for Asm.
                        elif WordUp.endswith('4'):  SizeSize = 8
                    elif                      AsmBool and Word in Codes1N: insertWord = 'OP_'+WordUp #e.g. map 10 to OP_10 in Asm.
                    elif self.AsmBool and not AsmBool and Word in Codes1N: insertWord = '01' +Word   #This is data, not an OpCode. Map 10 to 0110 in hex.
                    if Index>=2:
                        if   WordUp=='FALSE'  : insertWord = '0'    #These 3 are same for dec, bin, oct & hex. So don't have to always be converted.
                        elif WordUp=='1NEGATE': insertWord = '<-1>'
                        elif WordUp=='TRUE'   : insertWord = '1'
                        try:
                            if Index>2: insertWord = '<'+FromDec(int(WordUp))+'>'   #Decimal names should be converted to bin, oct or hex.
                        except: pass
                except:    #Word isn't an OpCode.
                    if Word.startswith('<') or Word.endswith('>'): insertWord = self.DecToHex(Word,False) #<dec>→hex
                    if not Index:   #→hex
                        if self.AsmBool and Word==insertWord: insertWord = push_script(Word)   #asm→hex, when not <dec>.
                        else:
                            try:    insertWord = CodeDict[insertWord]       #'00' is '0' & '77' is 'NIP', etc. 
                            except: pass
                    elif Index>=2:    #hex→<dec>, when possible. "Leading" 0 bytes (e.g. 0100) can't convert, nor can 0181, or 0110 etc.
                        try:
                            Hex = bitcoin.rev_hex(insertWord[SizeSize:])
                            Int = int(Hex[0],16)    #Leading digit.
                            if Int>=8: Dec = -int(hex(Int-8)[-1]+Hex[1:],16)    #Active leading bit.
                            else:      Dec =  int(               Hex    ,16)
                            if Index>2: Dec = FromDec(Dec)
                            insertWord, Hex  = '<'+str(Dec)+'>', push_script(insertWord[SizeSize:])
                            if Hex!=self.DecToHex(insertWord,False): insertWord = Hex  #Data may not be a # in BCH VM. 
                        except: pass    #Can't convert.
                    if AsmBool: insertWord = insertWord[SizeSize:]    #hex→asm.
                    elif insertWord.startswith('4c') and len(insertWord) > 0x4d*2: insertWord = 'PUSHDATA1 '+insertWord[2:]
                    elif insertWord.startswith('4d') and len(insertWord) > 0x4e*2: insertWord = 'PUSHDATA2 '+insertWord[2:]  #PUSHDATA4 can't be minimal.
                    if SizeSize!=2: SizeSize=2  #Reset to only 2 leading digits.
                if Word!=insertWord: Cursor.insertText(insertWord)
                lenChange=len(insertWord)-lenWord
                if not insertWord:  #Delete extra space when stripping a PUSHDATA. Either is a single B.
                    Cursor.deleteChar()
                    lenChange -= 1
                Pos       +=lenChange
                StartPosit+=lenChange
                LineCode=LineCode[Find+lenWord:]
            StartPosit+=lenLine+1
        Cursor.setPosition(CursorPos), self.ScriptBox.setTextCursor(Cursor)
        self.AsmBool, self.AsmIndex = AsmBool, Index #Remember for next time.
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        self.CaseBoxActivated() #Change spelling as required (OP_ or op_ etc).
        if Index:  #Converting to asm or <dec> deletes incorrect leading bytes, which are impossible to restore.
            self.KeepScriptsIndex = True
            self.textChanged()
        if Index!=1 and self.ColorsBox.isChecked(): self.setTextColor() #Color leading blue bytes for hex or <> for <dec>.
    def BlackToggled(self):
        if self.BlackBox.isChecked():   #Want equivalent clarity from a distance. Lighten blues. Strengthen green & yellow. Increase brightness of sky-blue, brown, purple & darkMagenta. +32 & +64 sacrifice color purity for readability.
            self.Colors.update( {'Constants':QColor(+128+64,+128+64,255),'Flow control':QColor(128+64,64+64,+64), 'Stack':Qt.green,'Bitwise logic':QColor(255,128+32,0),'Arithmetic':QColor(0,128+64,255),'Locktime':Qt.yellow,'Native Introspection':QColor(128+64,+128,255),'Reserved words':QColor(128+64,0+64,128+64),'PushData':QColor(128+0,128+0,255),'Data':Qt.white} )
            if self.Dark: StyleSheet = 'background: black'    #StyleSheet for QTextEdit. I prefer black to dark. 'background: black; color: white' could also work.
            else:         StyleSheet = 'background: black; color: white'    #'selection-background-color: blue' could also work. There's a ContextMenu problem.
        else:
            self.Colors.update( {'Constants':Qt.blue,'Flow control':QColor(128,64,0),'Stack':Qt.darkGreen,'Bitwise logic':QColor(255,128,0),'Arithmetic':QColor(0,128,255),'Crypto':Qt.magenta,'Locktime':Qt.darkYellow,'Reserved words':Qt.darkMagenta,'Native Introspection':QColor(128,0,255),'PushData':QColor(128,128,255),'Data':Qt.black} )
            if self.Dark: StyleSheet = 'background: white; color: black'    #'color: black' is needed for ContextMenu.
            else:         StyleSheet = ''   #Default
        for key in Codes.keys()-{'BCH','Disabled'}:
                for Code in Codes[key].split(): self.ColorDict[Code.upper()] = self.Colors[key]
        {Box.setStyleSheet(StyleSheet) for Box in {self.ScriptBox, self.HexBox} }
        self.Selection = None   #This forces re-coloring without losing actual selection.
        self.selectionChanged(), self.ScriptBox.setFocus()
    def dragEnterEvent(self,Event): Event.accept()  #Must 1st accept drag before drop. More rigorous code should reject drag if file extension incorrect.
    def dropEvent(self,Event):
        Event.accept()
        fileNames=(URL.toLocalFile() for URL in Event.mimeData().urls())
        ColorsBool, AsmIndex = self.ColorsBox.isChecked(), self.AsmIndex   #Remember Colors & AsmIndex for later on.
        self.ScriptBox.clear(), self.ColorsBox.setChecked(False)    #Disable colors for intermediate insertion.
        for fileName in fileNames:
            if fileName.endswith('.artifact'):  #Decode hex from CashScript asm bytecode.
                try:
                    Script = json.loads(open(fileName,'r').read())['bytecode']
                    self.AsmBox.setCurrentIndex(1), self.AsmBoxActivated()  #artifact bytecodes are in asm.
                    self.ScriptBox.setPlainText(Script)
                    self.ScriptBox.setPlainText(self.HexBox.toPlainText())
                except: self.ScriptBox.setPlainText('#Unable to read artifact.')
                continue
            try: self.ScriptBox.setPlainText(self.window.read_tx_from_file(fileName=fileName).raw)  #Decode all P2SH sigscripts. This crashes if file is too large (e.g. GB).
            except: pass    #EC reports error.
        self.AsmBox.setCurrentIndex(AsmIndex), self.AsmBoxActivated(), self.ColorsBox.setChecked(ColorsBool)   #Return colors etc.
    def LineButtonClicked(self):    #Convert to CashScript bytecode (in case of OP_CODES & asm).
        self.ScriptBox.setPlainText(' '.join(Word for Word in ' '.join(Line.split('#')[0].split('/')[0] for Line in self.ScriptBox.toPlainText().splitlines()).split()))
        self.setTextColor(), self.ScriptBox.setLineWrapMode(True)
    def ConverterClicked(self):
        try:
            self.Address = electroncash.address.Address.from_string(self.Address).to_ui_string()
            self.SetAddress()
        except: pass
    def FontBoxHighlighted(self,Index): self.FontBox.setCurrentIndex(Index), self.FontBoxActivated()   #Highlighted → Activated.
    def FontBoxActivated(self):
        Font = self.ScriptBox.font()
        if self.FontBox.currentIndex(): Font.setFamily('Consolas'), Font.setPointSize(11), self.ScriptBox.setFont(Font), self.HexBox.setFont(Font)  #'Consolas' Size(11) is Windows Notepad default. O'wise default is 'MS Shell Dlg 2' Size(8) which makes spaces half as big, and forces kerning (e.g. multisig PubKeys have different widths & hex digits from different bytes are squeezed together), and Size may be too small. An option is to kern only OpCodes, but I tried & varying font is a bit ugly.
        else:              Font.setFamily(self.Family), Font.setPointSize(self.PointSize), self.ScriptBox.setFont(Font), self.HexBox.setFont(Font)
    def SaveButtonClicked(self):    #Save HTML. A tabIcon isn't needed. LineWrap & background-color edited manually.
        HTML = '<title>'+self.Address+'</title>\n'+self.ScriptBox.toHtml()  #Can use address as title.
        if self.BlackBox.isChecked(): HTML = HTML.replace('style="','style=" background-color:#000000;',1)    #Black background.
        HTML+= '<br>\n'+self.HexBox.toHtml().replace('p style="','p style="white-space: pre-wrap; word-break: break-word;',1)+'\n'    #The big hex word always gets broken word-wrap.
        
        Box=QTextEdit() #Append address & count info to HTML output.
        Box.setTextColor(self.Colors['Data']), Box.setText('\n'+self.Address+'\n'+self.CountLabel.text())
        if self.ColorsBox.isChecked():  #Leading p or 3 can be blue.
            Cursor = Box.textCursor()
            Format = Cursor.charFormat()
            Cursor.setPosition(1), Cursor.setPosition(2, Cursor.KeepAnchor), Format.setForeground(self.Colors['Constants']), Cursor.setCharFormat(Format), Box.setTextCursor(Cursor)
        if not self.ScriptBox.lineWrapMode(): HTML+= Box.toHtml().replace('-wrap','',1)    #No -wrap. It turns out only the last declaration counts in general.
        else                                : HTML+= Box.toHtml()

        try: open(QFileDialog.getSaveFileName(self,'','','*.html')[0], 'w', encoding='utf-8').write(HTML)
        except: pass    #User cancelled.
