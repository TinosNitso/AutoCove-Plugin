from PyQt5.QtCore         import Qt
from PyQt5.QtGui          import QIcon, QMovie, QColor, QKeySequence
from PyQt5.QtWidgets      import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QComboBox, QPushButton, QTextEdit, QPlainTextEdit, QFileDialog, QSplitter
from electroncash         import bitcoin
from electroncash.plugins import BasePlugin, hook, daemon_command
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
OpCodesMembers=electroncash.address.OpCodes.__members__.keys()
if 'OP_TXLOCKTIME' in OpCodesMembers:  #Not all EC versions have Native Introspection. May fit in-between Locktime & Reserved words.
    Codes['Native Introspection']='InputIndex ActiveBytecode TXVersion TXInputCount TXOutputCount TXLocktime  \nUTXOValue UTXOBytecode OutpointTXHash OutpointIndex InputBytecode InputSequenceNumber OutputValue OutputBytecode'   #Nullary & unary.
    codesPythonic               +='inputIndex activeBytecode txVersion txInputCount txOutputCount txLocktime utxoValue utxoBytecode outpointTxHash outpointIndex inputBytecode inputSequenceNumber outputValue outputBytecode'
Codes['Reserved words']='Reserved Ver VerIf VerNotIf Reserved1 Reserved2 NOp1 NOp4 NOp5 NOp6 NOp7 NOp8 NOp9 NOp10'  #Nullary

Codes['BCH']='\nCAT SPLIT NUM2BIN BIN2NUM AND OR XOR DIV MOD CHECKDATASIG CHECKDATASIGVERIFY REVERSEBYTES' #'MS Shell Dlg 2' is default font but doesn't seem to allow adding serifs (e.g. for BCH codes).
Codes['Disabled']='PUSHDATA4 INVERT 2MUL 2DIV MUL LSHIFT RSHIFT'
Codes1N = {str(N) for N in range(10,17)}   #Codes1N is the set of OpCode names which are hex when 'OP_' is stripped from them, which isn't allowed in Asm. 

Colors = {'Splice':Qt.red,'Crypto':Qt.magenta,'SelectionForeground':Qt.white}   #These colors are the same for B&W. UI.BlackToggled method creates the rest.
if 'nt' in shutil.os.name:                  Color=QColor(0,120,215) #WIN10 is strong blue. This section determines highlighting color. There may not be a command to get this automatically.
elif 'Darwin' in shutil.os.uname().sysname: Color, Colors['SelectionForeground'] = QColor(179,215,255), Qt.black  #macOS Catalina is pale blue with black foreground. Windows & MX Linux have white foreground.
else:                                       Color=QColor(48,140,198)    #MX Linux is medium blue.
ColorLightness = Color.lightness()
if ColorLightness < 128: ColorLightness = .75*ColorLightness + 64   #This formula decreases darkness of highlighting by 25%. Max lightness is 255, but MSPaint has max luminosity at 240.
else:                    ColorLightness*= .875   #In this case, decrease lightness by an eighth. A quarter is too much on macOS, but an eighth isn't enough on Windows!
Color.setHsl(Color.hslHue(),Color.hslSaturation(),ColorLightness)
Colors['SelectionBackground'] = Color

HexDict, CodeDict, DepthDict, ColorDict, CaseDict = {}, {}, {}, {}, {}  #CodeDict is used by the decoder as a reversed HexDict. HexDict maps each CODE → hex. DepthDict maps CODE → ΔDEPTH. ColorDict maps CODE → Color, & CaseDict maps CODE → [Code,code].
for OP_CODE in OpCodesMembers:    #There might be more OpCodes than what's been typed here.
    CODE = OP_CODE[3:]
    HexDict[CODE], DepthDict[CODE], ColorDict[CODE] = bitcoin.int_to_hex(electroncash.address.OpCodes[OP_CODE].value), 0, Qt.darkCyan   #DepthDict is updated from 0 later, & darkCyan is for any codes which haven't been spelled out here.
    CodeDict[HexDict[CODE]], CaseDict[CODE] = CODE, [CODE, CODE.lower()]    #Define CaseDict for all OpCodes, to be updated later.
for CODE in '0 1 CHECKLOCKTIMEVERIFY CHECKSEQUENCEVERIFY'.split(): CodeDict[HexDict[CODE]] = CODE   #I prefer the ones spelled here.

for key in Codes.keys()-{'BCH','Disabled'}: #This section for CaseDict.
    for Code in Codes[key].split(): CaseDict[Code.upper()][0] = Code
for code in codesPythonic.split(): CaseDict[code.upper()][1] = code

for CODE in Codes['Constants'].upper().split(): DepthDict[CODE]=1   #This section for DepthDict: CODE → Δdepth. Δ below is just a variable.
Δ = 'IF -1 NOTIF -1 VERIFY -1 '
Δ+= 'TOALTSTACK -1 FROMALTSTACK 1 2DROP -2 2DUP 2 3DUP 3 2OVER 2 DEPTH 1 DROP -1 DUP 1 NIP -1 OVER 1 ROLL -1 TUCK 1 '   #IFDUP is 0 or 1.
Δ+= 'CAT -1 NUM2BIN -1 SIZE 1 '
Δ+= 'AND -1 OR -1 XOR -1 EQUAL -1 EQUALVERIFY -2 '
Δ+= 'ADD -1 SUB -1 MUL -1 DIV -1 MOD -1 LSHIFT -1 RSHIFT -1 BOOLAND -1 BOOLOR -1 NUMEQUAL -1 NUMEQUALVERIFY -2 NUMNOTEQUAL -1 LESSTHAN -1 GREATERTHAN -1 LESSTHANOREQUAL -1 GREATERTHANOREQUAL -1 MIN -1 MAX -1 '
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
//616e1e6d0d411d7a7aaf62bb1b3801c32184b8b23f366084967f0aae06b38be6        #AutoCove plugin, pReturn...
//4b84bd37e0660203da70796e9dd76f58f37d843917694c59ede7758ded5bb05f        #Mecenas plugin, protege spend. (Set time>0)
//a1018135011451d569183e6e327b37bb2600ac7001b1b918fc6121ad3e4bcf78        #Last Will plugin, cold ended with Schnorr sig. (Cold & Refresh wallets should be separate.)
//83b045c46418d0dd1922d52d6b0c2b35366e77cb9d20647e43b13cfcb78ec58c        #1of1 multisig.
//fccebdc8fcf556bebeb91ded0339756e568b254a6aa797f22a74ec3787f8a5d0        #3of5, 20 inputs, 5th on BCH rich-list with over 1% of all BCH.
//1fcd75baedf6cc609e6d0c66059fc3937a1d185fb50a15d812d0747544353e5d        #2of3, 121 inputs, 89 kBCH. Inputs can be compared by scrolling through them.

#CashScript hex can also be decoded. The following is the smartBCH SHA-Gate cc_covenant_v1.cash demo, without Native Introspection. cashc compiles to asm by default (in that case select 'asm', above, before inserting).
//5379547f7701207f01207f7701247f61007f77820134947f587f547f7701207f75597a5a796e7c828c7f755c7aa87bbbad060400000000145a7a7e5379011a7f777e587a8101117a635979a9597988029600b2757603e09304967802307597a269675f79009c635979a95b795d797e5e797ea9597988765c7987785e79879b785f79879b697803e09304965279023075979f63022c01b2756875675d79547f7701257f75a914282711cb97968c8674a46b5564ce3549f5782ea48855795e79aa7e5f797eaa5779885d7960797f7701247f7556798860796376023075937767768b7768547854807e5579557f777e7b757c6853798102d007945880760317a9147e5379a97e01877e76aa5579886d686d6d6d6d6d6d6d6d7551
#A few more follow, with artifacts from James Cramer. slp_dollar.artifact is for issuer freezable SLP tokens, with dust notifications, which can only ever be sent from & to freezable addresses. Unfortunately slp_dollar.cash v0.1 is different to the v0.1 source in the .artifact, whose own source doesn't compile with cashc v0.6.5 to the v0.5.3 bytecode (there's a 'NOP 0168' vs '016b' discrepancy near the beginning).
//5579009c635679016b7f77820134947f5c7f7701207f75527902010187916959798277589d5a79827701219d5b798277589d170000000000000000406a04534c500001010453454e4420577a7e587e59797e587e5b797e7b01207f77082202000000000000760317a9147e5156797e587e5c7a7e01147e5c79a97e53797ea97e01877e780317a9147e51577a7e587e5d7a7e01147e58797e547a7ea97e01877e7b041976a9147e5a7aa97e0288ac7e727e7b7e7c7e577a7eaa885579a97b88716e7c828c7f75577aa87bbbac77777767557a519d55796101687f77820134947f5c7f7701207f75587951876352790100886758790100876352795188686851597a7e7b527f777e082202000000000000760317a9147e7ba97e01877e7c041976a9147e557a7e0288ac7e170000000000000000376a04534c500001010453454e4420577a7e587e557a7e537a7c537a7e7b7e557a7eaa88537a7b6e7c828c7f75557aa87bbbac7768
#cashc -h slp_vault.cash aims to avoid accidental burning of SLP tokens. Equivalent to asm bytecode in slp_vault.artifact, & has no CODESEPARATORs. Both cashc v0.6.5 & v0.5.3 -h output are identical for the following 2 Scripts.
//78009c635279820134947f77587f75547f7581022202a1635379587f7508000000000000000088685379547a827752947f770288ac885379a988726e7c828c7f75557aa87bbbac77677c519d7801447f7701247f820134947f77587f547f7701207f757c547f7581022202a163765579aa885479587f750800000000000000008868557a56797e577a7eaa7b01207f7588716e7c828c7f75567aa87bbbac77777768
#slp_mint_guard.artifact. Equivalent to 'cashc -h slp_mint_guard.cash' + 2 CODESEPARATORs.
//5479009c635579820128947f7701207f755779827701219d707c7e030102087e0800000000000000007e0822020000000000000317a9147e01145a7aa97e01207e567a7e01177e557a7e01207e54797e5a797ea97e01877e7c577a7e7c7e5679040000000087646e58797eaa88676eaa8868577aa8537a885679a9537a88567a567a6e7c828c7f75577aa87babbbad6d6d5167547a519d5479820128947f7701207f75707c7e030102087e577a7e0822020000000000000317a9147e011457797e01207e567a7e01177e557a7e01207e54797e59797ea97e01877e7c567a7e7c7e5579040000000087646e57797eaa88676eaa8868567aa8537a885579a9537a88716e7c828c7f75567aa87babbbac77777768
#cashc -h assuranceContract.cash (Native Introspection requires EC v4.2.6+). Aims to enable flipstarters with minimum pledge only 100 bits.
//5479009c637cb1755479a9537a88537a011f7f7c01177f7b01197f00cc537a819d00cd537a8851cc7c819d51cd87777777675479519c63c3529d00c7827701179d00c700c658807e51c7827701199d51c6021027a26951c751c602b0049458807e7ea900c651c6930258029401147b7ec101157f777e00cc7b9d02a9147ca97e01877e00cd886d6d755167547a529d00cca1690376a9147b7e0288ac7e00cd8777776868
#And there's 'cashc -h yieldContract.cash', yield-farming CashScript from github.com/mazetoken/SLP-smart-contract-tokens.
//52796101687f77820134947f5c7f7701207f75567a56796e7c828c7f75587aa87bbbad02e8030222020222025879537aa269080000000000000000016a04534c5000827c7e7e51827c7e7e044d494e548276014ba063014c7c7e687c7e7e577a8276014ba063014c7c7e687c7e7e53827c7e7e0800000000000186a0827c7e7e827c7e7e7b5880041976a9147e567aa97e0288ac7e567a5880041976a9147e567a7e0288ac7e537a58800317a9147e557aa97e01877e727e7b7e7c7eaa87
#BTC-testnet LightNing to_local HTLC:
//6321026644cb387614f66421d14da3596c21cffa239011416c9adf3f351ee8551a9fc767029000b27521029654f80732769d7c435a184a3559f12178315526c53bbf003349390811c7590a68ac        
''',
''.join(Codes[key].upper()+'    #'+key+'\n' for key in Codes.keys())+'//Native Introspection & MUL OpCodes will be enabled in 2022.\n//Converting to asm allows the hex below to be decoded.',    #OpCodes List.
'',
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
#P2SH sender must have 3 or 4 data pushes, ≤75B each, in their unlocking sigscript ≤252B. Compressed 1of1, 1of2, 2of2 & VanityTXID are all compatible.
#Sending txn SIZE must be at most 520 Bytes. 3 inputs max for P2PKH, 1 input max for 2of2.
#13 bits minimum for single input (P2PKH sender), but add a couple more bits per extra input.
#It can't return SLP tokens!
#Fee btwn 6 to 9 bits.
#21 BCH max, but only 10tBCH have been tested. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#To return from other addresses requires editing qt.py.
''',
''] #Blanks for 'Δ List' & 'Clear all below'.
CovenantScripts[1]=CovenantScripts[1].replace('Flow control','Flow control. -3Δ').replace('Bitwise logic','Bitwise logic (unary & binary). -6Δ').replace('Locktime','Locktime (unary). +0Δ').replace('Reserved words','Reserved words (nullary). +0Δ').replace('BCH','BCH (binary, unary & ternary)')   #This section provides some commentary to OpCodes list.
CovenantScripts[1]=CovenantScripts[1].replace('Splice','Splice (unary). +1Δ').replace('NUM2BIN  ','NUM2BIN    #Splice (binary). -2Δ')
CovenantScripts[1]=CovenantScripts[1].replace('Arithmetic','Arithmetic (ternary). -2Δ').replace('MAX  ','MAX    #Arithmetic (binary). -19Δ').replace('0NOTEQUAL','0NOTEQUAL    #Arithmetic (unary). +0Δ')
CovenantScripts[1]=CovenantScripts[1].replace('Crypto','Crypto (binary, multary & unary)').replace('CODESEPARATOR  ','CODESEPARATOR    #Crypto (unary & nullary). +0Δ')
CovenantScripts[1]=CovenantScripts[1].replace('#Native Introspection','#Native Introspection (unary). +0Δ').replace('TXLOCKTIME  ','TXLOCKTIME    #Native Introspection (nullary). +6Δ')

for key in DepthDict.keys():    #Δ List. Writing out a loop seems efficient. +g for general.
    CovenantScripts[2]+=key
    if DepthDict[key]!=None: CovenantScripts[2]+=' '*8+'#%+gΔ'%DepthDict[key]
    CovenantScripts[2]+='\n'
ReturnScripts='''
080000000000da5ddd757801207f6b78aa8882029f01936c567f77587f6b817c9458807c01297f77517f7c01007e817f75517f7c817f77517f7c817f826377517f7c817f826377517f7c7f6875a90317a9147c7e7e01876775a9041976a9147c7e7e0288ac687eaa6c547f7701207f7588510144807c7ea86f7cbb757c01c37e7cabac
'''.splitlines()[1:]    #The covenant script hex is only needed by the watching-only wallet. Adding another line here allows wallet to also return from that Script's address, if the fee is correct.
ReturnAddresses=[electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)) for Script in ReturnScripts]

def push_script(script):    #Bugfix for script size 255B.
        if len(script)>>1 != 255: return bitcoin.push_script(script)
        else:                     return              '4cff'+script
class Plugin(BasePlugin):   #Everything can be controlled from console by entering 'plugins.external_plugins['AutoCove']'.
    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.windows, self.tabs, self.UIs = {}, {}, {}  #Initialize plugin wallet dictionaries.
  
        self.Dir=self.parent.get_external_plugin_dir().replace('\\','/')+'/AutoCove/' #Daemon help message needs /.
        self.WebP=self.Dir+'Icon.webp'    #QMovie only supports GIF & WebP. Another option is to put the icon's hex data in a .py script, so only Python's needed. Animating a flag looks too difficult for me.
        if shutil.os.path.exists(self.Dir): Extract = False   #Only ever extract zip (i.e. install) once.
        else:
            Zip, Extract = zipfile.ZipFile(self.Dir[:-1]+'-Plugin.zip'), True
            Zip.extract('AutoCove/Icon.webp',self.Dir[:-9])
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
        self.Movie = QMovie(self.WebP)    
        self.Movie.frameChanged.connect(self.setTabIcon), self.Movie.start()
        {self.load_wallet(window.wallet, window) for window in qt_gui.windows}  # These are per-wallet windows.
    @hook
    def load_wallet(self, wallet, window):
        """Hook called when a wallet is loaded and a window opened for it."""
        wallet_name = wallet.basename()
        self.windows[wallet_name] = window
        l = UI(window, self)
        tab = window.create_list_tab(l)
        self.tabs[wallet_name], self.UIs[wallet_name] = tab, l
        window.tabs.addTab(tab, self.Icon, 'AutoCove') #Add Icon instantly in case WebP frame rate is slow.
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
            Tabs.setTabIcon(Tabs.indexOf(self.tabs[wallet_name]), self.Icon)
    @daemon_command #This method could allow internet servers to decode user input to a HTML file, using only terminal command, after EC GUI wallet has been launched. Only the last P2SH sigscript in a txn will be written to HTML. (A future version might allow selecting input.) It might be possible for other plugins to somehow issue Daemon commands for this plugin.
    def AutoCove(self, daemon, config):
        if not self.UIs: return 'No UI. Check GUI.' #UI won't load until after user clicks OK when launching a watching-only wallet.
        self.DaemonArgs = config.get('subargs')
        if len(self.DaemonArgs)<2: return 'AutoCove usage example:\nElectron-Cash daemon AutoCove TXID FileName.html Option1 Option2 Option3 Option4 Option5\nTXID can also be any input, such as a redeem Script, a raw TX, "DUP DROP", etc.\n"TXID" can instead be replaced with a filename (requires file option following). .artifact & .txn accepted.\nAll 5 options are optional and can be in any order, select from:\nfile\nblack white\ncodes Codes CODES OP_CODES Op_Codes op_codes\nhex asm dec 0b 0o 0x\n1line align#\nColors & font can be set manually in GUI.\nGUI memory cleared before each HTML, except all options are remembered.\nExample command:\n./Electron-Cash daemon AutoCove 9b91b2c8afb3caca4e98921cb8b7d6131a8087ee524018d1154b609b92e92b30 '+self.Dir+'RefreshTimer.html black align#'
        list(self.UIs.values())[0].HiddenButton.clicked.emit()  #Daemon isn't allowed to directly connect to a real live text-box. Use the 0th UI.
class BTextEdit(QTextEdit): #HexBox (Black) QTextEdit class which has a bugfix for ContextMenu StyleSheet on a black background.
    def contextMenuEvent(self, Event):
        Menu=self.createStandardContextMenu()
        Menu.setStyleSheet(':enabled {selection-background-color: blue} :disabled {selection-background-color: darkgray; color: gray}') #Bugfix for Black background.
        Menu.exec(Event.globalPos())
class DualTextEdit(QTextEdit): #Special QTextEdit which aims to fully support undo & redo (with history) without any glitches due to colors, etc. It uses a phantom QPlainTextEdit. It's also zoomable and has a bugfix for when clicking halfway btwn 2 lines jumps the horizontalScrollBar to the right. A phantom should be more efficient than tracking all colors undo-history, etc. Unfortunately this code isn't self-sufficient yet (relies on UI to update phantom).
    def __init__(self): #Haven't bothered to support initialization string & parent.
        QTextEdit.__init__(self)
        self.PlainBox, self.UndoRedoBool = QPlainTextEdit(), False
        self.Document = self.PlainBox.document()
        self.setUndoRedoEnabled(False), self.setAcceptRichText(False), self.setTabStopWidth(24) # 3=default space-bar-width, so 24=8 spaces. Don't allow copy-paste of colors or font into box. Only the 1st command is strictly needed.
    def clear(self): self.PlainBox.clear(), QTextEdit.clear(self)    #These 2 lines clear the undo/redo stack from the phantom. Phantom must go 1st.
    def setPlainText(self, Text): self.PlainBox.setPlainText(Text), QTextEdit.setPlainText(self, Text)
    def keyPressEvent(self, Event):
        if   Event.matches(QKeySequence.Undo): self.undo()
        elif Event.matches(QKeySequence.Redo): self.redo()
        elif Event.matches(QKeySequence.ZoomIn ): self.zoomIn ()
        elif Event.matches(QKeySequence.ZoomOut): self.zoomOut()
        else: QTextEdit.keyPressEvent(self, Event)
    def undo(self): #.undo & .redo are expected to come standard and separate. 
        if self.Document.isUndoAvailable(): self.UndoRedo()
    def redo(self):
        if self.Document.isRedoAvailable(): self.UndoRedo(Redo=True)
    def UndoRedo(self, Redo=False): #Simpler to code both together, due to geometry issues.
        Bars = self.horizontalScrollBar(), self.verticalScrollBar() #Store geometry for later.
        Values = tuple(Bar.value() for Bar in Bars)
        
        self.UndoRedoBool, Cursor = True, self.textCursor()
        if Redo: self.PlainBox.redo()
        else:    self.PlainBox.undo()
        QTextEdit.setPlainText(self, self.PlainBox.toPlainText())   #setPlainText without resetting phantom.
        {Bars[n].setValue(Values[n]) for n in (0,1)}  #Restore ScrollBar geometry.
        Cursor.setPosition(self.PlainBox.textCursor().position()), self.setTextCursor(Cursor)   #Restore cursor position.
        self.UndoRedoBool = False  
    def contextMenuEvent(self, Event):
        Menu=self.createStandardContextMenu()   #Context menu triggers vary in whether they're enabled or not.
        Undo, Redo = Menu.actions()[:2] #Both always disabled at this point.
        if self.Document.isUndoAvailable(): Undo.setEnabled(True), Undo.triggered.disconnect(), Undo.triggered.connect(self.undo)   #disconnect unnecessary, but future versions of PyQt could behave differently.
        if self.Document.isRedoAvailable(): Redo.setEnabled(True), Redo.triggered.disconnect(), Redo.triggered.connect(self.redo)
        
        Menu.setStyleSheet(':enabled {selection-background-color: blue} :disabled {selection-background-color: darkgray; color: gray}') #Bugfix for Black background.
        Menu.exec(Event.globalPos())
    def mousePressEvent(self,Event):    #Only ever move horizontalScrollBar leftward, never rightward, as a result of someone clicking (without drag).
        Bar = self.horizontalScrollBar()
        Value = Bar.value()
        QTextEdit.mousePressEvent(self,Event)
        Value2 = Bar.value()
        if Value<Value2: Bar.setValue(Value)
    def wheelEvent(self,Event): self.setReadOnly(True), QTextEdit.wheelEvent(self,Event), self.setReadOnly(False)   #This 1 line is sufficient to vary font size with mouse scroll wheel, + ctrl.
class UI(QWidget):  #Separating UI from qt.py could allow cmdline integration (virtual/imaginary window & wallet).
    def __init__(self, window, plugin):
        QWidget.__init__(self)
        self.window, self.plugin = window, plugin
        self.Scripts, self.Colors, self.ColorDict = (Object.copy() for Object in (CovenantScripts, Colors, ColorDict) )  #Create new copy for each wallet's memory.

        self.Thread, self.UTXOs, self.Selection = threading.Thread(), {}, ''    #Empty thread, set of UTXOs to *skip* over, & *previous* Selection for highlighting. A separate thread delays auto-broadcasts so wallet has time to analyze history. If main thread is delayed, then maybe it can't analyze the wallet's history.
        window.history_updated_signal.connect(self.history_updated) #This detects preturn UTXOs. A password is never necessary to loop over UTXOs.
        window.addr_converter_button.clicked.connect(self.AddrConverterClicked)   #Toggle CashAddr.
        
        self.HiddenBox, self.HiddenButton = QTextEdit(), QPushButton()  #HiddenBox connection allows broadcasting from sub-thread, after sleeping. The Daemon CLI needs a PYQT_SIGNAL (imaginary button). I've never used an imaginary button before!
        self.HiddenBox.textChanged.connect(self.broadcast_transaction), self.HiddenButton.clicked.connect(self.Daemon)

        self.ColorsBox = QCheckBox('Colors')
        self.ColorsBox.setToolTip('Slows down typing, selections, etc.\nNot sure how colors should be assigned.')
        self.ColorsBox.toggled.connect(self.ColorsToggled)
        
        self.BlackBox = QCheckBox('Black')
        self.BlackBox.setToolTip('Background color toggle.')
        
        self.CaseBox=QComboBox()
        self.CaseBox.addItems('codes Codes CODES OP_CODES Op_Codes op_codes'.split())
        self.CaseBox.setToolTip('Clears Undo & Redo history.')
        self.CaseBox.setCurrentIndex(2), self.CaseBox.activated.connect(self.CaseBoxActivated), self.CaseBox.highlighted.connect(self.CaseBoxHighlighted)

        self.AsmBox, self.AsmBool, self.AsmIndex = QComboBox(), False, 0  #AsmBool remembers whether 'hex' or 'asm' was already selected. AsmIndex is more general (2 for <dec>). A future update could combine these, if more elegant.
        self.AsmBox.addItems('hex asm <±dec> <±0b...> <±0o...> <±0x...>'.split())
        self.AsmBox.setToolTip('Select asm before inserting CashScript bytecode.\nNot all data can be converted to numbers.\nDisable colors for more speed.\nTo convert 1→<1> etc, choose <dec> & OP_CODES.\nSpecial numbers can be observed.\ndec, bin, oct & hex are supported.\nClears Undo & Redo history.')
        self.AsmBox.activated.connect(self.AsmBoxActivated), self.AsmBox.highlighted.connect(self.AsmBoxHighlighted)
        
        self.FontBox = QComboBox()
        self.FontBox.addItems('Default font, Courier New'.split(', '))
        self.FontBox.setToolTip("Ctrl+ScrollWheel varies font size.\nCtrl+± too.\nNotepad++ uses Courier New.")
        self.FontBox.activated.connect(self.FontBoxActivated), self.FontBox.highlighted.connect(self.FontBoxHighlighted)

        AlignButton = QPushButton('Align #')
        AlignButton.setToolTip("Lines with ≤34B have # (comments) aligned.\nResets font to Courier New.\nClears Undo & Redo history.")
        AlignButton.clicked.connect(self.AlignButtonClicked)

        LineButton, self.LineButtonClickedBool = QPushButton('1 Line'), False   #LineButtonClickedBool switches LineWrap on, while button clicked.
        LineButton.setToolTip('Strips out all comments.\nConvert to OP_CODES & asm to generate CashScript bytecode.\nTemporarily enables LineWrap.\nDisable colors for more speed.\nClears Undo & Redo history.')
        LineButton.clicked.connect(self.LineButtonClicked)
        
        SaveButton = QPushButton('Save HTML')
        SaveButton.setToolTip("Supports B&W background, word wrap, & highlighting.\nTerminal command './Electron-Cash daemon AutoCove' displays CLI instructions.\nCtrl+S shortcut.")
        SaveButton.clicked.connect(self.SaveButtonClicked)

        self.ScriptsBox = QComboBox()
        self.ScriptsBox.setToolTip('New auto-decodes are stored here.\nasm form not stored.\nDisable colors for more speed.\nClears Undo & Redo history.')
        self.ScriptsBox.addItems('New, OpCodes List, Δ List, preturn... v1.1.3, Clear all below'.split(', '))
        self.ScriptsBox.activated.connect(self.ScriptActivated), self.ScriptsBox.highlighted.connect(self.ScriptsBoxHighlighted)
        self.KeepScriptsIndex = False   #Normally False. Whenever text changes, combo-box switches to 'New'.

        Title=QLabel('v1.1.3')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)

        HBoxTitle=QHBoxLayout()
        {HBoxTitle.addWidget(Widget) for Widget in (self.ColorsBox, self.BlackBox, self.CaseBox, self.AsmBox, self.FontBox, AlignButton, LineButton, SaveButton, self.ScriptsBox, Title)}
       
        InfoLabel = QLabel("Decode P2SH redeem Script hex by pasting it below. Paste txn or its TXID (or URL) to decode. Drag & drop .artifact &/or .txn files.") 
        InfoLabel.setToolTip("Only P2SH sigscripts are ever decoded.\nIf file is too large (e.g. 1GB) EC crashes.\nURL needs a TXID in its .split('/')\nAuto-indents are 8 spaces.\nΔ is the stack's depth change for each line, unavailable for IFDUP & CHECKMULTISIGs.\nΣΔ is summed from the last ΣΔ, or the beginning.")
        self.CoordsLabel = QLabel()
        self.CoordsLabel.setToolTip('Col refers to positionInBlock()+1')
        HBoxInfo=QHBoxLayout()
        {HBoxInfo.addWidget(Label) for Label in (InfoLabel, self.CoordsLabel)}
        
        self.ScriptBox=DualTextEdit()
        DefaultFont = self.ScriptBox.font()
        self.Family, self.PointSize = DefaultFont.family(), DefaultFont.pointSize()
        self.ToggleConnections()    #Activate connections.

        self.HexBox=BTextEdit()
        self.HexBox.setReadOnly(True), self.HexBox.setMinimumHeight(32)    #Default Height was 71p instead of 32p, which was a bit big.

        self.Splitter = QSplitter(Qt.Vertical)  #Adjustable TextEdits. Auto-height of HexBox re-sets it.
        {self.Splitter.addWidget(Box) for Box in (self.ScriptBox, self.HexBox)}

        self.AddressLabel, self.CountLabel = QLabel(), QLabel()
        self.AddressLabel.setToolTip("Start Electron-Cash with --testnet or --testnet4 to generate bchtest addresses.")
        self.  CountLabel.setToolTip("Limits are 201 Ops & 520 Bytes.\nops with values ≤0x60 don't count.")
        HBoxAddress=QHBoxLayout()
        {HBoxAddress.addWidget(Widget) for Widget in (self.AddressLabel, self.CountLabel)}

        {Label.setAlignment(Qt.AlignRight) for Label in (self.CoordsLabel, self.CountLabel)}
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, InfoLabel, self.CoordsLabel, self.AddressLabel, self.CountLabel}}

        if 'dark' in plugin.config.user_config['qt_gui_color_theme']:
            self.DarkTheme, self.pColor = True, '<font color=lightblue>'  #RTF string is used whenever calculating the BCH address with p (or 3) Color.
            self.BlackBox.setChecked(True)  #Black by default. 
        else: self.DarkTheme, self.pColor = False, '<font color=blue>'
        self.BlackToggled(self.DarkTheme), self.BlackBox.toggled.connect(self.BlackToggled), self.ScriptActivated(0), self.ColorsBox.setChecked(True)    #BlackToggled creates the Colors, then 'New' Script sets labels.
        
        VBox=QVBoxLayout()
        {VBox.addLayout(HBox) for HBox in (HBoxTitle, HBoxInfo)}
        VBox.addWidget(self.Splitter), VBox.addLayout(HBoxAddress)

        self.setLayout(VBox), self.setAcceptDrops(True), self.ScriptBox.setAcceptDrops(False)    #Drag & drop. Don't want "file: URI" inserted into ScriptBox, instead.
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
            
            Amount = UTXO['value']-(415+UTX.estimated_size())
            if Amount<546: continue #Dust limit
            
            TX = UTX  #Copy nLocktime.
            TX.outputs().clear(), TX.outputs().append( (0, ReturnAddress, Amount) )    #Covenant requires this exact output to correspond to its index. e.g. if pReturn is the 0th input, this must be the 0th output.
            
            UTXO['type'], UTXO['scriptCode'] = 'unknown', HexDict['CHECKSIG']  #scriptCode is the B following the only CODESEPARATOR.
            TX.inputs().clear(), TX.inputs().append(UTXO)

            Preimage, PrivKey = TX.serialize_preimage(0), (1).to_bytes(32,'big')
            Preimage = '01'+'00'*67+Preimage[68*2:-4*2]+'c3'+'00'*3
            PubKey, Sig = bitcoin.public_key_from_private_key(PrivKey, compressed=True), electroncash.schnorr.sign(PrivKey,bitcoin.Hash(bitcoin.bfh(Preimage)))  #Secp256k1 generator. 

            TX.inputs()[0]['scriptSig'] = push_script(Sig.hex())+push_script(PubKey)+push_script(Preimage[68*2:])+push_script(UTX.raw)+push_script(ReturnScripts[index])
            TX=TX.serialize()
            if TX!=self.HiddenBox.toPlainText(): self.HiddenBox.setPlainText(TX)    #Try not to double broadcast!
    def broadcast_transaction(self): self.window.broadcast_transaction(electroncash.Transaction(self.HiddenBox.toPlainText()), tx_desc=None)
    def textChanged(self):  #Whenever users type, attempt to re-compile.
        if self.ScriptBox.lineWrapMode() and not self.LineButtonClickedBool: self.ScriptBox.setLineWrapMode(QTextEdit.NoWrap)  

        Script, ScriptsIndex, ColorsBool, Cursor = self.ScriptBox.toPlainText(), self.ScriptsBox.currentIndex(), self.ColorsBox.isChecked(), self.ScriptBox.textCursor()
        if ScriptsIndex and Script!=self.Scripts[ScriptsIndex]:   #Is the Script New?
            if self.KeepScriptsIndex: self.KeepScriptsIndex = False   #Reset, i.e. when converting to asm.
            else: self.ScriptsBox.setCurrentIndex(0)     #New script.
        self.CurrentScript, CursorPos, Bytes = Script, Cursor.position(), b''

        if '\n' not in Script and 1==len(Script.split()):    #This section is the decoder. Start by checking if input is only 1 word & fully hex. Then check if an URL containing TXID, TX or TXID. Only attempt to decode a single word (bugfix for e.g. '00 NIP')
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
                    Inputs, TXID = TX.inputs(), TX.txid_fast()
                    Inputs[0] and TX.outputs()[0]   #Check there's at least 1 input & output, or else not a TX.
                    self.ColorsBox.setChecked(False)    #Disable colors for decoding loop, then re-enable.
                    self.InputN, self.TXIDComment = 0, '/'+str(len(Inputs))+' from TXID '+TXID  #Remember input # & TXID for auto-comment. Could also state locktime (last 4B). To get each input value, TX.fetch_input_data & TX.fetched_inputs could be used but that required a time.sleep delay to download all input txns.
                    for Input in Inputs:
                        self.InputN += 1    #Start counting from 1.
                        if Input['type'] in {'p2sh','unknown'}:    #'p2sh' is usually multisig, but 'unknown' also has a Script.
                            self.get_ops = electroncash.address.Script.get_ops(bitcoin.bfh(Input['scriptSig']))
                            self.ScriptBox.setPlainText(self.get_ops[-1][-1].hex())  #Script to decode.
                    del self.TXIDComment    #Or else Script decoder may think it's decoding a TX.
                    self.ColorsBox.setChecked(ColorsBool)
                    if Script==self.CurrentScript: self.ScriptBox.setPlainText('#No P2SH sigscript for TXID '+TXID), self.setTextColor()   #gray out comment.
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
            endlAfter  = endlEither+'BOOLAND'.split()    #BOOLAND may look good at line ends.
            Script, endl, IndentSize = '', '\n', 8 #endl gets tabbed after IFs (IF & NOTIF) etc. Try 8 spaces, because default font halves the space size.
            Size, SizeSize, Count, OpCount, Δ, ΣΔ = 0, 0, 0, 0, 0, 0  #Size count-down of "current" data push. SizeSize is the "remaining" size of Size (0 for 0<Size<0x4c). Count is the # of Bytes on the current line. Target min of 1 & max of 21, bytes/line. OpCount is for the current line. Δ counts the change in stack depth.
            try:
                for Tuple in self.get_ops[:-1]:
                    Script += '//'
                    try:
                        if not Tuple[1]: raise  #To be consistent with Blockchain.com, list empty push as OP_0.
                        Script   += Tuple[1].hex()    #Show full stack leading to redeem Script as asm comments when decoding a scriptSig.
                        ByteCount = ' '+str(len(Tuple[1]))+'B push'
                    except:   #Sigscript may push OP_N instead of data.
                        try:    Int = Tuple[0]
                        except: Int = Tuple   #SLP Ed.
                        Script   += 'OP_'+CodeDict[bitcoin.int_to_hex(Int)]
                        ByteCount = ''  
                    Script += ' '*IndentSize+'#+1Δ 0ops'+ByteCount+endl #No OP_EXEC means never any ops from push-only data-pushes.
                    ΣΔ += 1
                self.get_ops=[] #Delete per input.
            except: pass    #Not decoding a scriptSig with more than a redeem Script.
            
            def endlComment(Script,Δ,OpCount,Count,endl): #This method is used to end lines in the redeem Script, when decoding.
                if Δ==None: ΔStr = ''
                else:       ΔStr = '%+gΔ '%Δ
                if OpCount==1: ops  = 'op  '
                else:          ops  = 'ops '
                return Script+' '*(IndentSize-1)+'#'+ΔStr+str(OpCount)+ops+str(Count)+'B'+endl, 0, 0, 0    #Reset Δ, OpCount & Count to 0.
            def ΣΔComment(Script, ΣΔ, endl):  #This method adds ΣΔ to the last line & any line with IF, ENDIF etc. Also returns zeroed out ΣΔ.
                if ΣΔ==None: ΣΔStr = '?'   #Indicates where next ΣΔStr is summed from.
                else:        ΣΔStr = '%+g'%ΣΔ
                return Script.rstrip(endl)+' '*IndentSize+ΣΔStr+'ΣΔ'+endl, 0
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
                try:    #OpCode which has a name.
                    CODE=CodeDict[Hex]
                    if CODE in {'ENDIF','ELSE'}:
                        endl='\n'+endl[ 1+IndentSize : ] #Subtract indent for ENDIF & ELSE.
                        if not Count and Script[-IndentSize:]==' '*IndentSize: Script=Script[:-IndentSize]    #Subtract indent back if already on a new line.
                    if Count and (CODE in endlBefore or 'RESERVED' in CODE or 'PUSHDATA' in CODE): Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount, Count, endl)    #New line before any RESERVED or PUSHDATA.
                    if CODE in {'VERIF', 'VERNOTIF'}: Script=Script.rstrip(' ')   #No tab before these since script will fail no matter what.
                    Script  += CODE+' '
                    Count   += 1
                    OpCount += Byte>0x60 #Only these count towards 201 limit.
                    try:    Δ+= DepthDict[CODE]
                    except: Δ = None
                    try:   ΣΔ+= DepthDict[CODE]
                    except:ΣΔ = None
                    if CODE in {'ELSE', 'IF', 'NOTIF'}: endl+=' '*IndentSize #Add indent after ELSE, IF & NOTIF.
                    elif 'PUSHDATA' in CODE: SizeHex, SizeSize = '', 2**(Byte-0x4c)  #0x4c is SizeSize=1. SizeHex is to be the little endian hex form of Size.
                    if Count>=21 or CODE in endlAfter or any(Word in CODE for Word in {'RESERVED', 'VERIFY'}) or (endlAfterDROP and CODE=='DROP'): Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount,Count,endl)   #New line *after* any VERIFY or RESERVED. A <Nonce>DROP should have its own endlAfter (& maybe endlBefore).
                    if CODE in 'IF NOTIF ELSE ENDIF'.split(): Script, ΣΔ = ΣΔComment(Script, ΣΔ, endl)
                except: #New data push.
                    Size = Byte
                    if Count and Count+Size>=21: Script, Δ, OpCount, Count = endlComment(Script,Δ,OpCount,Count,endl)  #New line before too much data.
                    Script += Hex
                    Count  += 1
                    try:
                        Δ += 1
                        ΣΔ+= 1
                    except: pass    #Δ or ΣΔ may be None.
                if endlAfterDROP: endlAfterDROP = False
            Script = Script.rstrip(endl)    #Remove empty last line.
            if Count: Script = endlComment(Script,Δ,OpCount,Count,'')[0]  #Comment final line.
            if 'ΣΔ' not in Script.splitlines()[-1]: Script = ΣΔComment(Script, ΣΔ, '')[0]
            Script += '\n#Auto-decode'
            try: Script += ' of input '+str(self.InputN)+self.TXIDComment    #Txn inputs get a longer comment than plain redeem Script.
            except: pass
            
            if not (Size or SizeSize):   #Successful decode is plausible if all data-pushes completed successfully.
                try:  #No exact duplicates stored in memory.
                    ScriptsIndex = self.Scripts.index(Script)
                    self.ScriptsBox.setCurrentIndex(ScriptsIndex)
                except: #This subsection adds the Auto-decode to memory in the combo-box.
                    self.Scripts.append(Script), self.ScriptsBox.addItem(''), self.ScriptsBox.setCurrentText('') #Don't know what address yet to use as Script name.
                    ScriptsIndex = self.ScriptsBox.currentIndex()   #Keep track of this because activating the Script can cause it to change to 0 due to Asm-conversion.
                self.HexBox.clear(), self.ScriptActivated(ScriptsIndex), self.ScriptsBox.setItemText(ScriptsIndex, self.Address)   #Clearing HexBox ensures new colors, in case the same Script is being decoded.
                return  #textChanged signal will return to below this point. Decoder ends here.
        if Script and ColorsBool:  #This section greys out typed '#' even though they don't change bytecode. Same with bluing out '>'.
            Cursor=self.ScriptBox.textCursor()
            Format, ColorChange = Cursor.charFormat(), False  #if ColorChange, return.
            (Color, ColorNew), Char = (Format.foreground(),)*2, Script[CursorPos-1]
            if   Char=='#':                              ColorNew = Qt.gray
            elif Char in ('<','>') and Color != Qt.gray: ColorNew = self.Colors['Constants']  #gray may be a comment.
            if Color!=ColorNew: self.ToggleConnections(), Format.setForeground(ColorNew), Cursor.movePosition(Cursor.Left, Cursor.KeepAnchor), Cursor.setCharFormat(Format), Cursor.movePosition(Cursor.Right), self.ToggleConnections()    #Set ColorNew by toggling connections, since a selection's made.
        if not self.ScriptBox.UndoRedoBool: #This section controls DualTextEdit phantom. A better version would pass keyPressEvent on directly, internal to DualTextEdit. Instead a mathematical trick can be used.
            PhantomScript, PhantomCursor = self.ScriptBox.PlainBox.toPlainText(), self.ScriptBox.PlainBox.textCursor() 
            EndPos = len(PhantomScript)-len(Script)+CursorPos
            if EndPos>=0 and Script[CursorPos:] == PhantomScript[EndPos:]:    #Check just in case. Everything after CursorPos should match up with the phantom.
                MaxStartPos = min(EndPos, CursorPos)
                StartPos = next((n for n in range(MaxStartPos) if Script[n]!=PhantomScript[n]), MaxStartPos)    #Only change phantom if necessary.
                PhantomCursor.setPosition(StartPos), PhantomCursor.setPosition(EndPos, Cursor.KeepAnchor), PhantomCursor.insertText(Script[StartPos:CursorPos]) #When someone hits BackSpace or Delete key, a new editBlock is created for each deletion. This is a minor "error" which could be fixed by detecting keyPressEvent for Delete (all deletions should be undone together, not separately, e.g. using .joinEditBlock).
            else: self.ScriptBox.PlainBox.setPlainText(Script)   #Clear phantom undo history, e.g. if there's a bug.
        elif not ScriptsIndex and Script in self.Scripts: self.ScriptsBox.setCurrentIndex(self.Scripts.index(Script))   #Revert ScriptsIndex after Undo.

        Script, OpCount = self.ScriptToHex(Script)    #OpCount could also be calculated using EC's .get_ops
        if Script and Script==self.HexBox.toPlainText() and not self.ScriptBox.UndoRedoBool: return    #Do nothing if no hex change, unless empty (not much work) or Undo/Redo-ing.
        self.HexBox.setPlainText(Script)
        
        OpCount, ByteCount = str(OpCount)+' Op'+(OpCount!=1)*'s'+' & ', str(len(Script)>>1)+' Bytes' #Set Count QLabels.
        self.CountLabel.setText('is the BCH address for the redeem Script above (if valid) with              '+OpCount+ByteCount)
        
        try:    #Set Address QLabel.
            Bytes = bitcoin.bfh(Script)
            self.Address = electroncash.address.Address.from_multisig_script(Bytes).to_ui_string()
        except: self.Address = '_'*42   #42 chars typically in CashAddr. Script invalid.
        self.SetAddress(), self.setTextColor()
    def ScriptToHex(self, Script, BypassErrors=False):  #e.g. 'DUP DROP' → '7675',2
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
    def DecToHex(self, Str, BypassErrors=False):    #e.g. <100>→0164
        if Str=='<>':        return '00'    #Empty push.
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
    def ScriptsBoxHighlighted(self, Index):   #Highlighted → Activated, but only if Script is from decoder memory.
        if Index>=len(CovenantScripts) and Index!=self.ScriptsBox.currentIndex(): self.ScriptsBox.setCurrentIndex(Index), self.ScriptActivated(Index)
    def ScriptActivated(self, Index):    #Change redeem script.
        FirstIndex, self.AsmBool, self.AsmIndex = len(CovenantScripts), False, 0    #FirstIndex is for Scripts below 'Clear...'. Loading into asm or <dec> requires artificially toggling since memory is always in hex.
        if Index==FirstIndex-1:   #This section is for 'Clear below'. Maybe gc.collect() could fit in.
            {self.ScriptsBox.removeItem(FirstIndex) for ItemN in range(FirstIndex,len(self.Scripts))}
            self.Scripts, Index = self.Scripts[:FirstIndex], 0   #0 sets to 'New'.
        elif Index==2: self.AsmBoxHighlighted(0)    #Δ List viewed best with hex.
        self.HexBox.clear(), self.ScriptBox.setPlainText(self.Scripts[Index]), self.AsmBoxActivated(), self.CaseBoxActivated(), self.ScriptBox.textCursor().setPosition(0), self.setHexBoxHeight()   #Activate CaseBox & AsmBox for new PlainText. Clearing HexBox causes re-coloring.
    def SetAddress(self):   #Toggles the blue p or 3 in address.
        if self.Address and self.ColorsBox.isChecked(): self.AddressLabel.setText(self.pColor+self.Address[0]+"</font>"+self.Address[1:])
        else:                                           self.AddressLabel.setText(                                      self.Address)
    def setTextColor(self): #This can max out a CPU core when users hold in a key like '0'. A future possibility is only coloring in changes in text, instead of the whole of both boxes every time.
        if not self.ColorsBox.isChecked(): return   #No Colors.
        
        Cursor, HexCursor = self.ScriptBox.textCursor(), self.HexBox.textCursor()
        (Format, FormatData, FormatConstants), CursorPos = (Cursor.charFormat() for n in range(3)), Cursor.position()
        {Format.setBackground(Qt.transparent) for Format in (Format, FormatData, FormatConstants)}
        self.ToggleConnections(), FormatData.setForeground(self.Colors['Data']), FormatConstants.setForeground(self.Colors['Constants'])
        StartPosit, HexPos, SizeSize, ForegroundColor = 0, 0, 2, self.Colors['Constants']    #Line's absolute position, along with HexBox position. SizeSize is the # of hex digits which are colored in blue, by default. ForegroundColor tracks whether a PUSHDATA color should be used for the data-push size.
        for Line in self.CurrentScript.splitlines():
            LineCode=Line.split('#')[0].split('//')[0].upper()
            CommentPos, Pos, lenLine = len(LineCode), StartPosit, len(Line)  #Comment posn, virtual cursor position.
            for Word in LineCode.split():
                Find, lenWord = LineCode.find(Word), len(Word)
                Pos+=Find
                Cursor.setPosition(Pos), HexCursor.setPosition(HexPos)   #This removes Anchor.
                
                try:    #to color in Word as OpCode Name.
                    if self.AsmBool and Word in Codes1N: raise #1N not an OpCode in Asm.
                    else: Format.setForeground(self.ColorDict[Word.replace('OP_','')])
                    Pos+=lenWord
                    Cursor.movePosition(Cursor.EndOfWord,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)    #EndOfWord doesn't like punctuation.
                    HexPos+=2
                    HexCursor.setPosition(HexPos        ,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                    
                    if 'PUSHDATA' in Word:
                        ForegroundColor = self.Colors['PushData']
                        if   Word.endswith('2'): SizeSize = 4  # of blue digits to follow.
                        elif Word.endswith('4'): SizeSize = 8
                except: #Assume data push
                    Cursor.setPosition(Pos+lenWord, Cursor.KeepAnchor), Cursor.setCharFormat(FormatData), Format.setForeground(ForegroundColor), Cursor.setPosition(Pos)   #Color whole push in as data to start off with.
                    lenHex = lenWord
                    if Word.startswith('<') or Word.endswith('>'): #<dec>
                        lenHex = len(self.DecToHex(Word))
                        if lenHex<=2: Cursor.setPosition(Pos+lenWord, Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All blue, since an OpCode.
                        else:   #< & > turn blue! 
                            Cursor.movePosition(Cursor.Right,Cursor.KeepAnchor), Cursor.setCharFormat(Format), Cursor.clearSelection()
                            if Word.endswith('>'): Cursor.setPosition(Pos+lenWord-1), Cursor.movePosition(Cursor.Right,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                            if   lenHex > 0x101<<1: SizeSize = 6    #4d____ is 4 extra digits, on top of 2. SizeSize needed for hex coloring.
                            elif lenHex >  0x4c<<1: SizeSize = 4    #4c__   is 2 extra digits.
                            if SizeSize>2: HexCursor.setPosition(HexPos+2,Cursor.KeepAnchor), HexCursor.setCharFormat(FormatConstants), HexCursor.clearSelection(), Format.setForeground(self.Colors['PushData'])
                    elif self.AsmBool:   #No leading blue bytes for Asm.
                        if   lenWord > 0xff<<1: SizeSize = 6    #4d____ is 4 extra digits, on top of 2.
                        elif lenWord > 0x4b<<1: SizeSize = 4    #4c__   is 2 extra digits.
                        lenHex+=SizeSize   #Asm jumps ahead in HexPos.
                        if SizeSize>2: HexCursor.setPosition(HexPos+2,Cursor.KeepAnchor), HexCursor.setCharFormat(FormatConstants), HexCursor.clearSelection(), Format.setForeground(self.Colors['PushData'])
                    else: Cursor.setPosition(Pos+SizeSize,Cursor.KeepAnchor), Cursor.setCharFormat(Format), Cursor.clearSelection()    #Blue leading bytes followed by data.
                    
                    if ForegroundColor!=self.Colors['Constants']: ForegroundColor=self.Colors['Constants']  #Reset for next word.
                    HexCursor.setPosition(HexPos+SizeSize,Cursor.KeepAnchor), HexCursor.setCharFormat(Format), HexCursor.clearSelection()
                    Pos   +=lenWord
                    HexPos+=lenHex
                    HexCursor.setPosition(HexPos,Cursor.KeepAnchor), HexCursor.setCharFormat(FormatData)
                    if SizeSize!=2: SizeSize=2  #Reset to coloring in 2 digits as blue.
                LineCode=LineCode[Find+lenWord:]
            Cursor.setPosition(StartPosit+CommentPos)   #This section greys out the comments. '//' & '#' are the same, but Qt.darkGray or Qt.lightGray could also work for '//'.
            StartPosit+=lenLine
            if CommentPos<lenLine: Format.setForeground(Qt.gray), Cursor.movePosition(Cursor.EndOfLine,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
            StartPosit+=1 #'\n' is 1 Byte. Do this last in case '#' is on last line.
        Cursor.setPosition(CursorPos), HexCursor.movePosition(Cursor.Start), self.ToggleConnections()
    def selectionChanged(self): #Highlight all instances of selected word. Also does byte search of hex.
        self.CurrentScript, Cursor, HexCursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Text, Format, Selection, CursorPos, selectionStart, selectionEnd = self.CurrentScript.upper(), Cursor.charFormat(), Cursor.selectedText().upper(), Cursor.position(), Cursor.selectionStart(), Cursor.selectionEnd()
        
        if Selection==self.Selection: return    #Do nothing if Selection hasn't changed.
        else: self.Selection=Selection

        self.ToggleConnections(), Format.setForeground(self.Colors['Data']), Format.setBackground(Qt.transparent)   #All data. This section guarantees a fully transparent background to start with.
        Cursor   .movePosition(Cursor.Start),    Cursor.movePosition(Cursor.End,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)
        HexCursor.movePosition(Cursor.Start), HexCursor.movePosition(Cursor.End,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
        self.ToggleConnections(), self.setTextColor(), self.ToggleConnections() #Color & reconnect.

        Format.setForeground(Colors['SelectionForeground']), Format.setBackground(Colors['SelectionBackground'])
        Find, Pos, lenSelection = Text.find(Selection), 0, len(Selection)   #Pos is Virtual cursor position.
        while Selection and Find>=0:    #Ignore empty selection.
            Pos+=Find
            Cursor.setPosition(Pos)
            Pos+=lenSelection
            Cursor.setPosition(Pos,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
            Text=Text[Find+lenSelection:]
            Find=Text.find(Selection)
        if CursorPos>selectionStart: Cursor.setPosition(selectionStart)
        else:                        Cursor.setPosition(selectionEnd) #Right-to-left selection.
        Cursor.setPosition(CursorPos,Cursor.KeepAnchor), self.ToggleConnections()

        SelectionHex = self.ScriptToHex(Selection,BypassErrors=True)[0]  #[1] is OpCount.
        try: Bytes, SelectionBytes = bitcoin.bfh(self.HexBox.toPlainText()), bitcoin.bfh(SelectionHex)
        except: return  #Don't do anything if HexBox ain't valid.
        Find, Pos, lenSelectionHex, lenSelectionBytes = Bytes.find(SelectionBytes), 0, len(SelectionHex), len(SelectionBytes)
        while SelectionBytes and Find>=0:
            Pos+=Find*2
            HexCursor.setPosition(Pos)
            Pos+=lenSelectionHex
            HexCursor.setPosition(Pos,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
            Bytes=Bytes[Find+lenSelectionBytes:]
            Find=Bytes.find(SelectionBytes)
        HexCursor.movePosition(Cursor.Start)
    def ColorsToggled(self):
        self.Selection=None   #Force re-selection, now w/ or w/o Colors.
        self.SetAddress(), self.selectionChanged(), self.ScriptBox.setFocus()   #QCheckBox steals focus.
    def CaseBoxHighlighted(self,Index): self.CaseBox.setCurrentIndex(Index), self.CaseBoxActivated(Index)   #Highlighted → Activated.
    def CaseBoxActivated(self, Index=None):   #Change btwn Codes, CODES & OP_CODES using QTextCursor. This is more complicated but possibly quicker than editing strings directly.
        if Index==None: Index = self.CaseBox.currentIndex()
        Cursor = self.ScriptBox.textCursor()
        CursorPos, StartPosit, selectionStart, selectionEnd = Cursor.position(), 0, Cursor.selectionStart(), Cursor.selectionEnd()    #StartPosit is each line's starting posn. Retain selection highlighting.
        lenChangeSum, CursorFound = 0, False    #To re-locate CursorPos after changing many words.
        self.ToggleConnections()
        for Line in self.CurrentScript.splitlines():
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
        Cursor.setPosition(CursorPos,Cursor.KeepAnchor), self.ScriptBox.setTextCursor(Cursor), self.ToggleConnections() #setTextCursor is needed for final selection.
        self.Selection, self.CurrentScript = None, self.ScriptBox.toPlainText() #Force re-selection after changing spells.
        self.selectionChanged(), self.ScriptBox.setFocus(), self.ScriptBox.PlainBox.setPlainText(self.CurrentScript)    #Return focus to Selection, clear Undo/Redo history.
    def AsmBoxHighlighted(self, Index): self.AsmBox.setCurrentIndex(Index), self.AsmBoxActivated(Index)   #Highlighted → Activated.
    def AsmBoxActivated(self, Index=None):  #This method strips out blue leading bytes (asm), or else puts them back in. QTextCursor is used. <dec>, bin & oct conversion, via hex, also. Doesn't maintain selection.
        if Index == None: Index = self.AsmBox.currentIndex()
        Cursor, AsmBool = self.ScriptBox.textCursor(), 1==Index
        if Index == self.AsmIndex: return   #Do nothing if untoggled.
        if Index:   #Always fully convert to hex before attempting to convert to asm or <dec>.
            ColorsBool = self.ColorsBox.isChecked() #Disable colors for intermediate conversion.
            if not self.AsmIndex: self.AsmIndex = None
            self.ColorsBox.setChecked(False), self.AsmBoxHighlighted(0), self.AsmBox.setCurrentIndex(Index), self.ColorsBox.setChecked(ColorsBool)
        CursorPos, StartPosit, SizeSize = Cursor.position(), 0, 2    #StartPosit is each line's starting posn. SizeSize is the # of leading digits (in a data-push) to delete for coversion to asm.
        self.ToggleConnections()
        def FromDec(Dec):
            if   Index==3: return bin(Dec) #→<±0b...>
            elif Index==4: return oct(Dec) #→<±0o...>
            elif Index==5: return hex(Dec) #→<±0x...>
        for Line in self.CurrentScript.splitlines():
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
                except:    #Word isn't an OpCode Name.
                    if Word.startswith('<') or Word.endswith('>'): insertWord = self.DecToHex(Word) #<dec>→hex
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
                            if Hex!=self.DecToHex(insertWord): insertWord = Hex  #Data may not be a # in BCH VM. 
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
        self.AsmBool, self.AsmIndex, self.CurrentScript = AsmBool, Index, self.ScriptBox.toPlainText() #Remember for next time.
        Cursor.setPosition(CursorPos), self.ToggleConnections(), self.CaseBoxActivated(), self.ScriptBox.PlainBox.setPlainText(self.CurrentScript) #Change spelling as required (OP_ or op_ etc), & reset Undo/Redo history.
        if Index:  #Converting to asm or <dec> requires re-compiling since it deletes incorrect leading bytes, which are impossible to restore.
            self.KeepScriptsIndex = True    #Not 'New' Script.
            self.textChanged()
        if Index!=1: self.setTextColor() #Color leading blue bytes for hex or <> for <dec>.
    def BlackToggled(self, BlackBool):  #Test line (copy-paste for spectrum): PUSHDATA2 0100ff RETURN TOALTSTACK NUM2BIN INVERT MAX CHECKSIGVERIFY CHECKLOCKTIMEVERIFY TXLOCKTIME RESERVED 
        if BlackBool:   #Want equivalent clarity from a distance. Lighten blues. Strengthen green & yellow. Increase brightness of sky-blue, brown, purple & darkMagenta. +32 & +64 sacrifice color purity for readability.
            self.Colors.update( {'Constants':QColor(+128+64,+128+64,255),'Flow control':QColor(128+64,64+64,+64), 'Stack':Qt.green,'Bitwise logic':QColor(255,128+32,0),'Arithmetic':QColor(0,128+64,255),'Locktime':Qt.yellow,'Native Introspection':QColor(128+64,+128,255),'Reserved words':QColor(128+64,0+64,128+64),'PushData':QColor(128+0,128+0,255),'Data':Qt.white} )
            if self.DarkTheme: StyleSheet = 'background: black'    #StyleSheet for QTextEdit. I prefer black to dark. 'background: black; color: white' could also work.
            else:              StyleSheet = 'background: black; color: white'    #'selection-background-color: blue' could also work. There's a ContextMenu problem.
        else:   #Brown (here) is dark-orange. Sky-blue & Purple (here) stem from blue. darkCyan (aka teal) appears too close to darkGreen. Byte/s following a PUSHDATA are gray+blue. darkYellow is aka olive. Orange looks like red when I look up at my LCD, but looks like yellow when I look down. Green pixels may be projecting upwards. darkCyan is clearer from above, & can be re-introduced in the future.
            self.Colors.update( {'Constants':Qt.blue,'Flow control':QColor(128,64,0),'Stack':Qt.darkGreen,'Bitwise logic':QColor(255,128,0),'Arithmetic':QColor(0,128,255),'Locktime':Qt.darkYellow,'Native Introspection':QColor(128,0,255),'Reserved words':Qt.darkMagenta,'PushData':QColor(128,128,255),'Data':Qt.black} )
            if self.DarkTheme: StyleSheet = 'background: white; color: black'    #'color: black' is needed for ContextMenu.
            else:              StyleSheet = ''   #Default
        for key in Codes.keys()-{'BCH','Disabled'}:
                for Code in Codes[key].split(): self.ColorDict[Code.upper()] = self.Colors[key]
        {Box.setStyleSheet(StyleSheet) for Box in {self.ScriptBox, self.HexBox} }
        
        self.Selection = None   #This forces re-coloring without losing actual selection.
        self.selectionChanged(), self.ScriptBox.setFocus()
    def dragEnterEvent(self, Event): Event.accept()  #Must 1st accept drag before drop. More rigorous code should reject drag if all file extensions are incorrect.
    def dropEvent     (self, Event):
        Event.accept()
        mimeData = Event.mimeData()
        if mimeData.hasUrls(): self.OpenFileNames(URL.toLocalFile() for URL in mimeData.urls())
        else: self.ScriptBox.setPlainText(mimeData.text())  #User can drag & drop from HexBox to ScriptBox.
    def OpenFileNames(self, FileNames):
        ColorsBool, AsmIndex = self.ColorsBox.isChecked(), self.AsmIndex   #Remember Colors & AsmIndex for later on.
        self.ScriptBox.clear(), self.ColorsBox.setChecked(False)    #Disable colors for intermediate insertion.
        for fileName in FileNames:
            if fileName.lower().endswith('.artifact'):  #Decode hex from CashScript asm bytecode.
                try:
                    Script = json.loads(open(fileName,'r').read())['bytecode']  #artifact bytecodes are in asm. Check can load before setting AsmBox.
                    self.AsmBoxHighlighted(1), self.ScriptBox.setPlainText(Script), self.ScriptBox.setPlainText(self.HexBox.toPlainText())
                except: self.ScriptBox.setPlainText('#Unable to read artifact.')
                continue
            try: self.ScriptBox.setPlainText(self.window.read_tx_from_file(fileName=fileName).raw)  #Decode all P2SH sigscripts. This crashes if file is too large (e.g. GB).
            except: pass    #EC reports error.
        self.AsmBoxHighlighted(AsmIndex), self.ColorsBox.setChecked(ColorsBool)   #Return colors & AsmIndex settings.
    def LineButtonClicked(self):    #Convert to CashScript bytecode (in case of OP_CODES & asm).
        self.LineButtonClickedBool = True
        self.ScriptBox.setLineWrapMode(True)    #It might be faster to enable LineWrap first, due to an o'wise excessively long line.
        self.ScriptBox.setPlainText(' '.join(Word for Word in ' '.join(Line.split('#')[0].split('/')[0] for Line in self.CurrentScript.splitlines()).split()))
        self.setTextColor()
        self.LineButtonClickedBool = False
    def AddrConverterClicked(self):
        try:
            self.Address = electroncash.address.Address.from_string(self.Address).to_ui_string()
            self.SetAddress()
        except: pass
    def FontBoxHighlighted(self, Index): self.FontBox.setCurrentIndex(Index), self.FontBoxActivated(Index)   #Highlighted → Activated.
    def FontBoxActivated(self, Index): #A future version of this method could replace all 8-sized indents with 4-sized ones, depending on font. Notepad & macOS use 8, but MX-Linux uses 4.
        Font = self.ScriptBox.font()
        if Index: Font.setFamily('Courier New') #'Consolas' Size(11) is Windows Notepad default. 'Courier New' Size(10) is Notepad++. O'wise default is 'MS Shell Dlg 2' Size(8) which makes spaces half as big, and forces kerning (e.g. multisig PubKeys have different widths & hex digits from different bytes are squeezed together), and Size may be too small.
        else:     Font.setFamily(self.Family)
        Font.setPointSize(self.PointSize)
        {Box.setFont(Font) for Box in {self.ScriptBox, self.HexBox}}
        self.setHexBoxHeight()
    def SaveHTML(self,FileName,SaveCoords):    #Save HTML. A tabIcon isn't needed. LineWrap, background-color & a word-break edited manually. This method serves terminal Daemon as well, just not the coords.
        self.ScriptBox.document().setMetaInformation(0, self.Address)  #Can use address as title.
        HTML = self.ScriptBox.toHtml()
        if self.BlackBox.isChecked(): HTML = HTML.replace('style="','style=" background-color:#000000;',1)    #Black background.
        HTML+= '\n<br>\n'+self.HexBox.toHtml().replace('p style="','p style="white-space: pre-wrap; word-break: break-word;',1)+'\n\n'    #The big hex word always gets broken word-wrap.
        
        Box=QTextEdit() #Append address & count info to HTML output.
        Box.setTextColor(self.Colors['Data']), Box.setPlainText('\n'+self.Address+'\n'+self.CountLabel.text()+'\n'+SaveCoords*('\n\n'+self.CoordsLabel.text()+'        (TextCursor position)\n'))
        if self.ColorsBox.isChecked():  #Leading p or 3 can be blue.
            Cursor = Box.textCursor()
            Format = Cursor.charFormat()
            Cursor.setPosition(1), Cursor.movePosition(Cursor.Right, Cursor.KeepAnchor), Format.setForeground(self.Colors['Constants']), Cursor.setCharFormat(Format)
        if not self.ScriptBox.lineWrapMode(): HTML+= Box.toHtml().replace('-wrap','',1)    #No -wrap. It turns out only the last declaration counts in general.
        else                                : HTML+= Box.toHtml()
        try: open(FileName, 'w', encoding='utf-8').write(HTML+'\n')
        except: self.window.show_message("Can't save to that location.")    #Triggered by bad Daemon command.
    def SaveButtonClicked(self):    #Another possibility is to save .txt. Or a screenie, but that's always missing the title-bar. window.screen().grabWindow(window.winId()).save(FileName,'png')
        FileName = QFileDialog.getSaveFileName(self,'','','*.html')[0]
        if FileName: self.SaveHTML(FileName,SaveCoords=True)
    def Daemon(self):   #This method interfaces UI with Daemon CLI. It's like a remote control. The "correct" CLI options are determined here. 
        Args, OptionsLow, ColorsBool = self.plugin.DaemonArgs, [], self.ColorsBox.isChecked()
        self.ScriptActivated(len(CovenantScripts)-1), self.ScriptBox.clear(), self.FontBoxHighlighted(0), self.ColorsBox.setChecked(False)    #Clear memory before decoding. Default font unless align#. Potentially faster to toggle colors off & on.
        for Option in Args[2:]:
            OptionLow = Option.lower()
            OptionsLow.append(OptionLow)
            if   'black' in OptionLow: self.BlackBox.setChecked(True )
            elif 'white' in OptionLow: self.BlackBox.setChecked(False)
            elif Option in (self.CaseBox.itemText(n) for n in range(6)): self.CaseBox.setCurrentText(Option)   #OP_CODES etc.
            else:
                try: self.AsmBoxHighlighted('hex asm dec 0b 0o 0x'.split().index(OptionLow))
                except: pass
        if 'file' in OptionsLow: self.OpenFileNames({Args[0]})  #Filename input, e.g. .artifact.
        else: self.ScriptBox.setPlainText(Args[0])  #TXID, Script input etc.
        
        if    '1line' in OptionsLow: self.LineButtonClicked()   #A button may be pushed, too.
        elif 'align#' in OptionsLow: self.AlignButtonClicked()
        self.ColorsBox.setChecked(ColorsBool), self.SaveHTML(Args[1], SaveCoords=False)
    def AlignButtonClicked(self):   #Size up each line's bytecode, and base alignment on longest line ≤21B.
        SplitLines, Cursor, Pos, MaxFind = self.CurrentScript.splitlines(), self.ScriptBox.textCursor(), 0, 0  #Pos is line starting position, & MaxFind sets standard # column position.
        for Line in SplitLines: #Determine MaxFind
            if '#' in Line and len(self.ScriptToHex(Line,BypassErrors=True)[0])>>1 <= 34: MaxFind = max(MaxFind, len(Line.split('#')[0].split('//')[0].rstrip(' ')))    #This can all be done without rstrip (.find only), but not as well.
        if not MaxFind: #Re-scan. Align '#' in arbitrary text, unless it's passed ~Col 100.
            for Line in SplitLines:
                if '#' in Line:
                    Find = len(Line.split('#')[0].rstrip(' '))
                    if Find<=100: MaxFind = max(MaxFind, Find)
        self.ToggleConnections()
        for Line in SplitLines: #Insert spacing.
            Find, FindStrip = Line.find('#'), len(Line.split('#')[0].rstrip(' '))
            if 0<Find and FindStrip<=MaxFind:
                Cursor.setPosition(Pos+FindStrip), Cursor.setPosition(Pos+Find, Cursor.KeepAnchor), Cursor.insertText(' '*(MaxFind-FindStrip))
                Pos += MaxFind-Find
            Pos += len(Line)+1
        self.CurrentScript = self.ScriptBox.toPlainText()
        self.ScriptBox.PlainBox.setPlainText(self.CurrentScript), self.FontBoxHighlighted(1), self.ToggleConnections()  #Switch to Courier New, after resetting phantom Undo history. To undo successfully would require more code.
    def cursorPositionChanged(self):  #Calculate new coords. Standard convention is to start @(1,1).
        Cursor = self.ScriptBox.textCursor()
        self.CoordsLabel.setText('Ln '+str(Cursor.blockNumber()+1)+', Col '+str(Cursor.positionInBlock()+1))

        #CursorPos, Format = Cursor.position(), Cursor.charFormat()    # Method is a bit weak without bracket detection, like in Notepad++. Work in progress.
        # if Text[CursorPos]=='[':
            # Pos = CursorPos+Text[CursorPos:].find(']')
            # Cursor.setPosition(Pos), Cursor.setPosition(Pos+1, Cursor.KeepAnchor), Format.setBackground(self.Colors['SelectionBackground']), Cursor.setCharFormat(Format), Cursor.setPosition(CursorPos), self.ScriptBox.setTextCursor(Cursor)
    def ToggleConnections(self):    #Connections slow down intermediate steps.
        Box = self.ScriptBox
        try:    Box.textChanged.disconnect()             , Box.selectionChanged.disconnect()                  , Box.cursorPositionChanged.disconnect()
        except: Box.textChanged.connect(self.textChanged), Box.selectionChanged.connect(self.selectionChanged), Box.cursorPositionChanged.connect(self.cursorPositionChanged)
    def keyPressEvent(self, Event): #QKeySequence.Open & QKeySequence.New can't be handled by plugin, unlike the following.
        if   Event.matches(QKeySequence.Save) or Event.matches(QKeySequence.SaveAs): self.SaveButtonClicked() #SaveAs disabled on Windows.
        elif Event.matches(QKeySequence.ZoomIn ): {Box.zoomIn () for Box in {self.ScriptBox, self.HexBox}} #ZoomIn both boxes, etc.
        elif Event.matches(QKeySequence.ZoomOut): {Box.zoomOut() for Box in {self.ScriptBox, self.HexBox}}
        elif Event.matches(QKeySequence.Undo) or Event.matches(QKeySequence.Redo): self.ScriptBox.keyPressEvent(Event)  #Pass Undo/Redo to ScriptBox.
        else: QWidget.keyPressEvent(self, Event)
    def wheelEvent(self, Event):    #scrollWheel may apply to both boxes simultaneously. If neither, then both.
        if all(not Box.underMouse() for Box in {self.ScriptBox, self.HexBox}): {Box.wheelEvent(Event) for Box in {self.ScriptBox, self.HexBox}}
        QWidget.wheelEvent(self, Event) #Does nothing.
    def resizeEvent(self, Event): QWidget.resizeEvent(self, Event), self.setHexBoxHeight()  #Auto-resize HexBox.
    def setHexBoxHeight(self):  #Auto size HexBox after ScriptActivated & FontBoxActivated.
        SplitterHeight = self.Splitter.height() #This section auto-changes HexBox height.
        HexBoxHeight = min(SplitterHeight/4, max(self.HexBox.minimumHeight(), self.HexBox.document().size().height()+4+8*self.DarkTheme)) #HexBox no more than a quarter of Splitter, +4p+8p on document due to inaccuracy.
        if HexBoxHeight!=self.Splitter.sizes()[1]: self.Splitter.setSizes([SplitterHeight-HexBoxHeight, HexBoxHeight])  #Only change if needed.
    