from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QMovie, QColor
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit, QCheckBox
import electroncash, zipfile, shutil, threading, time
from electroncash import bitcoin
from electroncash.plugins import BasePlugin, hook

Codes={'Constants': '0 False  PushData1 PushData2 PushData4 1Negate  1 True '+''.join(' '+str(N) for N in range(2,17))}   #Codes dict is used for colors & lower-case conversion.
Codes['Flow control']='NOp If NotIf Else EndIf Verify Return'
Codes['Stack']='ToAltStack FromAltStack 2Drop 2Dup 3Dup 2Over 2Rot 2Swap IfDup Depth Drop Dup Nip Over Pick Roll Rot Swap Tuck'
Codes['Splice']='Cat Split Num2Bin  \nBin2Num Size' #Binary & unary.
Codes['Bitwise logic']='Invert And Or XOr Equal EqualVerify'    #Unary & binary.
Codes['Arithmetic']='1Add 1Sub 2Mul 2Div Negate Abs Not 0NotEqual  \nAdd Sub Mul Div Mod LShift RShift BoolAnd BoolOr NumEqual NumEqualVerify NumNotEqual LessThan GreaterThan LessThanOrEqual GreaterThanOrEqual Min Max  \nWithin' #Unary, binary & ternary.
Codes['Crypto']='RIPEMD160 SHA1 SHA256 Hash160 Hash256 CodeSeparator  \nCheckSig CheckSigVerify CheckMultiSig CheckMultiSigVerify CheckDataSig CheckDataSigVerify ReverseBytes'
Codes['Locktime']='CheckLocktimeVerify NOp2  CheckSequenceVerify NOp3'  #Unary

codesPythonic='pushData1 pushData2 pushData4  nOp notIf endIf  toAltStack fromAltStack ifDup  xOr equalVerify 0notEqual lShift rShift boolAnd boolOr numEqual numEqualVerify numNotEqual lessThan greaterThan lessThanOrEqual greaterThanOrEqual  codeSeparator checkSig checkSigVerify checkMultiSig checkMultiSigVerify checkDataSig checkDataSigVerify reverseBytes  checkLocktimeVerify nOp2 checkSequenceVerify nOp3  verIf verNotIf nOp1 nOp4 nOp5 nOp6 nOp7 nOp8 nOp9 nOp10  '
OpCodesMembers=electroncash.address.OpCodes.__members__.keys()  #Not all EC versions have Native Introspection, which I figure fits in between Locktime & Reserved words.
if 'OP_TXLOCKTIME' in OpCodesMembers:
    Codes['Native Introspection']='InputIndex ActiveBytecode TXVersion TXInputCount TXOutputCount TXLocktime  \nUTXOValue UTXOBytecode OutpointTXHash OutpointIndex InputBytecode InputSequenceNumber OutputValue OutputBytecode'   #Nullary & unary.
    codesPythonic               +='inputIndex activeBytecode txVersion txInputCount txOutputCount txLocktime utxoValue utxoBytecode outpointTxHash outpointIndex inputBytecode inputSequenceNumber outputValue outputBytecode'
Codes['Reserved words']='Reserved Ver VerIf VerNotIf Reserved1 Reserved2 NOp1 NOp4 NOp5 NOp6 NOp7 NOp8 NOp9 NOp10'  #Nullary

Codes['BCH']='\nCAT SPLIT NUM2BIN BIN2NUM AND OR XOR DIV MOD CHECKDATASIG CHECKDATASIGVERIFY REVERSEBYTES' #'MS Shell Dlg 2' is default font but doesn't seem to allow adding serifs (e.g. for BCH codes).
Codes['Disabled']='PUSHDATA4 INVERT 2MUL 2DIV MUL LSHIFT RSHIFT'
Codes1N = {str(N) for N in range(10,17)}   #Codes1N is the set of OpCode names which are hex when 'OP_' is stripped from them, which isn't allowed in Asm.
#Test line (copy-paste for spectrum): PUSHDATA2 0100ff RETURN TOALTSTACK NUM2BIN INVERT MAX CHECKSIGVERIFY CHECKLOCKTIMEVERIFY TXLOCKTIME RESERVED 
Colors={'Constants':Qt.blue,'Flow control':Qt.darkMagenta,'Stack':Qt.darkGreen,'Splice':Qt.red,'Bitwise logic':QColor(255,128,0),'Arithmetic':QColor(0,128,255),'Crypto':Qt.magenta,'Locktime':Qt.darkYellow,'Reserved words':QColor(128,64,0),'Native Introspection':QColor(128,0,255),'SelectionForeground':Qt.white,'PushData':QColor(128,128,255),'Data':Qt.black}
#Brown (here) is dark-orange. Sky-blue & Purple (here) stem from blue. darkCyan (aka teal) appears too close to darkGreen. Byte/s following a PUSHDATA are gray+blue. darkYellow is aka olive. I've noticed orange & red are too close, but only when I look slightly *up*, not down, at my LCD screen. It's similar to the darkGreen vs darkCyan problem, the green pixels project slightly upwards, so looking upward orange==red !
if 'nt' in shutil.os.name:                  Color=QColor(0,120,215) #WIN10 is strong blue. This section determines highlighting color.
elif 'Darwin' in shutil.os.uname().sysname: Color, Colors['SelectionForeground'] = QColor(179,215,255), Qt.black     #macOS Catalina is pale blue with black foreground. Windows & MX Linux have white foreground.
else:                                       Color=QColor(48,140,198)    #MX Linux is medium blue.
ColorLightness = Color.lightness()  #One idea is to seek a 25% difference between selection & highlighting, by either making darker lighter, or lighter darker.
if ColorLightness < 128: ColorLightness = .75*ColorLightness + 64   #This formula decreases darkness of highlighting by 25%, for all OSs. Max lightness is 255, but MSPaint has max luminosity at 240.
else:                    ColorLightness*= .75   #In this case, decrease lightness by 25%.
Color.setHsl(Color.hslHue(),Color.hslSaturation(),ColorLightness)
Colors['SelectionBackground'] = Color

ColorDict, HexDict, CodeDict, CaseDict = {}, {}, {}, {}    #OpCode dictionaries. CodeDict is used by the decoder as a reversed HexDict. ColorDict maps CODE to Color, & CaseDict maps CODE to Code. All dicts could easily be combined into one master dict, but that may not be as fast and elegant, except during initialization. CodeDict & CaseDict don't have to be as fast.
for key in Codes.keys()-{'BCH','Disabled'}:
    for Code in Codes[key].split():
        CODE = Code.upper()
        ColorDict[CODE], CaseDict[CODE] = Colors[key], Code
for OP_CODE in OpCodesMembers:    #There might be more OpCodes than what's typed here.
    CODE=OP_CODE[3:]
    HexDict[CODE] = bitcoin.int_to_hex(electroncash.address.OpCodes[OP_CODE].value)
    CodeDict[HexDict[CODE]] = CODE
    try:    ColorDict[CODE]    #Check whether code's been typed out.
    except: ColorDict[CODE], CaseDict[CODE] = Qt.darkGray, CODE  #Ensure ColorDict & CaseDict well-defined for all OpCodes.
for CODE in '0 1 CHECKLOCKTIMEVERIFY CHECKSEQUENCEVERIFY'.split(): CodeDict[HexDict[CODE]] = CODE   #I prefer the ones spelled here.

for code in codesPythonic.split():  #This section converts CaseDict from CODE→Code mapping, into CODE → Code, code mapping. 
    CODE = code.upper()
    CaseDict[CODE] = CaseDict[CODE], code
for CODE in CaseDict.keys()-codesPythonic.upper().split(): CaseDict[CODE] = CaseDict[CODE], CODE.lower()  #Ensure CaseDict tuple is valid for all CODEs.

CovenantScripts=['',   #This section can provide examples of Scripts.
''.join(Codes[key].upper()+'    #'+key+'\n' for key in Codes.keys())+'//Native Introspection & MUL OpCodes will be enabled in 2022.\n//Converting to asm allows the hex below to be decoded.',    #List all the OpCodes.
'''//[UTX, Preimage, Sig, PubKey] 'preturn...' v1.0.6 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. This update increases fees by 11% by supporting both P2PKH & P2SH senders! P2SH sender must have 3 or 4 data-pushes ≤75B (e.g. 1of1, 1of2 or 2of2) in its unlocking sigscript ≤252B. VanityTXID (compressed) sender is supported! Mof3 MULTISIG not supported yet. CHECKMULTISIG's leading 0 gives an extra data-push.
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

#If the 'preturn...' address is added to a watching-only wallet, this plugin will automatically broadcast the return txns.
#Sender must use a P2PKH or P2SH address, not P2PK.
#P2SH sender must have only 3 or 4 data pushes, ≤75B each, in their unlocking sigscript ≤252B. Compressed 1of1, 1of2, 2of2 & VanityTXID are all compatible.
#Sending txn SIZE must be at most 520 Bytes (3 inputs max).
#15 bits minimum for single input, but add a couple more bits per extra input.
#It can't return SLP tokens!
#Fee between 8 to 12 bits.
#21 BCH max, but I haven't tested over 10tBCH. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#The sender must not use a PUSHDATA OpCode in the output pkscript (non-standard).
#To return from other addresses currently requires editing qt.py.
''',
''] #Blanks for 'New' & 'Clear all below'.
CovenantScripts[1]=CovenantScripts[1].replace('Bitwise logic','Bitwise logic (unary & binary)').replace('Locktime','Locktime (unary)').replace('Reserved words','Reserved words (nullary)').replace('BCH','BCH (binary, unary & ternary)')   #This section provides some commentary to OpCodes list.
CovenantScripts[1]=CovenantScripts[1].replace('Splice','Splice (unary)').replace('NUM2BIN  ','NUM2BIN    #Splice (binary)')
CovenantScripts[1]=CovenantScripts[1].replace('Arithmetic','Arithmetic (ternary)').replace('MAX  ','MAX    #Arithmetic (binary)').replace('0NOTEQUAL','0NOTEQUAL    #Arithmetic (unary)')
CovenantScripts[1]=CovenantScripts[1].replace('Crypto','Crypto (binary, multary & unary)').replace('CODESEPARATOR  ','CODESEPARATOR    #Crypto (unary & nullary)')
CovenantScripts[1]=CovenantScripts[1].replace('#Native Introspection','#Native Introspection (unary)').replace('TXLOCKTIME  ','TXLOCKTIME    #Native Introspection (nullary)')

ReturnScripts='''
6fad7b828c7f757ca87bbb7d547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f7581788277940289029458807c01297f77517f7c01007e817f75517f7c817f77517f7c817f826377517f7c817f826377517f7c7f6875a90317a9147c7e7e01876775a9041976a9147c7e7e0288ac687eaa7c820128947f7701207f758708030000000071d8e975
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
        self.Scripts = CovenantScripts[:]   #[:] is a bugfix for when different wallets interfere with each others' memory.
        
        try: #Dark color theme demands its own colors, and is based on approx quarter-grey (nearly black). Though dark background allows more colors, I'm trying to be consistent. A trick is to add either 16 (darkMagenta, orange & purple), 32 (brown) or 64 (e.g. sky-blue→cyan) whenever more contrast against quarter-gray (dark-darkGray) is needed.
            self.pColor = "<font color='blue'>" #This RTF string is used whenever calculating the BCH address with pColor.
            if 'dark' not in window.config.user_config['qt_gui_color_theme']: raise
            self.pColor = "<font color='lightblue'>"
            ColorsUpdate = {'Constants':QColor(128,128,255),'Flow control':QColor(128+16,0,128+16),'Stack':Qt.green,'Bitwise logic':QColor(255,128+16,0),'Arithmetic':QColor(0,128+64,255),'Locktime':Qt.yellow,'Native Introspection':QColor(128+16,0,255),'Reserved words':QColor(128+32,64+32,0),'PushData':QColor(128+64,128+64,255),'Data':Qt.white}
            Colors.update(ColorsUpdate)   #Lighten blues. Strengthen green & yellow.
            for key in Codes.keys()-{'BCH','Disabled'}:
                for Code in Codes[key].split(): ColorDict[Code.upper()] = Colors[key]
        except: pass    #Default colors.
        
        self.Thread, self.UTXOs, self.Selection = threading.Thread(), {}, ''    #Empty thread, set of UTXOs to *skip* over, & *previous* Selection for highlighting. A separate thread delays auto-broadcasts so wallet has time to analyze history. If main thread is delayed, then maybe it can't analyze the wallet's history.
        window.history_updated_signal.connect(self.history_updated) #This detects preturn UTXOs. A password is never necessary to loop over UTXOs.
        self.HiddenBox=QTextEdit()  #HiddenBox connection allows broadcasting from sub-thread, after sleeping.
        self.HiddenBox.textChanged.connect(self.broadcast_transaction)

        self.CheckBox = QCheckBox('Colors')
        self.CheckBox.setToolTip("Slows down typing & selections.\nNot sure how colors should be assigned.")
        self.CheckBox.setChecked(True), self.CheckBox.toggled.connect(self.toggled)
                
        self.CaseBox=QComboBox()
        self.CaseBox.addItems('codes Codes CODES OP_CODES Op_Codes op_codes'.split())
        self.CaseBox.setCurrentIndex(2), self.CaseBox.activated.connect(self.CaseBoxActivated)

        self.AsmBox, self.AsmBool = QComboBox(), False  #AsmBool remembers whether 'hex' or 'asm' was already selected.
        self.AsmBox.addItems(['hex','asm']), self.AsmBox.activated.connect(self.AsmBoxActivated)
        self.AsmBox.setToolTip('Select asm before inserting CashScript bytecode.')
        
        try: self.CaseBox.textHighlighted.connect(self.CaseBoxHighlighted), self.AsmBox.textHighlighted.connect(self.AsmBoxHighlighted)
        except: pass    #textHighlighted signal unavailable in EC-v3.6.6.
        
        Title=QLabel('AutoCove v1.0.6')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)

        self.ScriptsBox = QComboBox()
        self.ScriptsBox.setToolTip('New auto-decodes are stored here.\nasm form never stored.')
        self.ScriptsBox.addItems(["New", "OpCodes", "preturn... v1.0.6", "Clear all below"])
        self.ScriptsBox.setCurrentIndex(2), self.ScriptsBox.activated.connect(self.ScriptActivated)

        HBoxTitle=QHBoxLayout()
        HBoxTitle.addWidget(self.CheckBox,.1), HBoxTitle.addWidget(self.CaseBox,.1), HBoxTitle.addWidget(self.AsmBox,.1), HBoxTitle.addWidget(Title,1), HBoxTitle.addWidget(self.ScriptsBox,.1)
        
        InfoLabel = QLabel("Auto-decode P2SH redeem Script hex into readable form by pasting it below. Paste raw txn or its TXID to decode all its P2SH sigscripts.") 
        InfoLabel.setToolTip("Data-pushes equally sized usually appear different widths due to default font.\nAuto-indents are 8 spaces.")
        
        self.ScriptBox=QTextEdit()
        self.ScriptBox.setUndoRedoEnabled(False)    #Undo etc can be enabled in a future version, using QTextDocument. IDE is unsafe without both save & undo.
        self.ScriptBox.setLineWrapMode(QTextEdit.NoWrap), self.ScriptBox.setTabStopDistance(24) # 3=default space-bar-Distance, so 24=8 spaces.
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)
        #Font=self.ScriptBox.font(); Font.setFamily('Consolas'), Font.setPointSize(10), self.ScriptBox.setFont(Font)    #'Consolas' Size(11) is Windows Notepad default. O'wise default is 'MS Shell Dlg 2' Size(8) which makes spaces half as big, and forces kerning (e.g. multisig PubKeys have different widths), and Size may be too small. An option is to kern only OpCodes, but I tried & varying font is a bit ugly.
        
        self.HexBox=QTextEdit()
        self.HexBox.setReadOnly(True)

        self.AddressLabel=QLabel()
        self.CountLabel=QLabel()
        self.ScriptActivated()    #Assembly Script dumped onto HexBox, to set labels.
        HBoxAddress=QHBoxLayout()
        {HBoxAddress.addWidget(Widget) for Widget in [self.AddressLabel, self.CountLabel]}
        self.CountLabel.setAlignment(Qt.AlignRight)
        self.CountLabel.setToolTip('Limits are 201 Ops & 520 Bytes.\nOps inside an IF branch may not count towards the limit.')
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, InfoLabel, self.CountLabel, self.AddressLabel}}

        VBox=QVBoxLayout()
        VBox.addLayout(HBoxTitle)
        VBox.addWidget(InfoLabel)
        VBox.addWidget(self.ScriptBox,10), VBox.addWidget(self.HexBox,1)  #Script bigger than hex. Dunno how to set a dynamic or adjustable height on HexBox.
        VBox.addLayout(HBoxAddress)
        self.setLayout(VBox)
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
            
            Amount = UTXO['value']-(649+UTX.estimated_size())
            if Amount<546: continue #Dust limit
            
            TX=UTX  #Copy nLocktime.
            TX.inputs().clear(), TX.outputs().clear()
            TX.outputs().append((0,ReturnAddress,Amount))    #Covenant requires this exact output, and that it's the only one.
            
            UTXO['type'], UTXO['scriptCode'] = 'unknown', ReturnScripts[index]
            TX.inputs().append(UTXO)    #Covenant requires return TX have only 1 input.

            PreImage=TX.serialize_preimage(0)
            PrivKey=(1).to_bytes(32,'big')
            PubKey=bitcoin.public_key_from_private_key(PrivKey,compressed=True)  #Secp256k1 generator. 
            Sig=electroncash.schnorr.sign(PrivKey,bitcoin.Hash(bitcoin.bfh(PreImage)))
            TX.inputs()[0]['scriptSig']=push_script(UTX.raw)+push_script(PreImage)+push_script(Sig.hex()+'41')+push_script(PubKey)+push_script(ReturnScripts[index])
            TX=TX.serialize()
            if TX!=self.HiddenBox.toPlainText(): self.HiddenBox.setPlainText(TX)    #Don't double broadcast!
    def broadcast_transaction(self): self.window.broadcast_transaction(electroncash.Transaction(self.HiddenBox.toPlainText()),None)  #description=None.
    def textChanged(self):  #Whenever users type, attempt to re-compile.
        Script=self.ScriptBox.toPlainText()
        if self.ScriptsBox.currentIndex() and Script not in self.Scripts: self.ScriptsBox.setCurrentIndex(0)     #New script.
        
        Bytes=b''   #This section is the decoder. Start by checking if input is only 1 word & fully hex. Then check if a TX.
        if ' ' not in Script:
            Script=Script.lower().replace('0x','')  #Accept 0x hex code, as well.
            try:
                Bytes=bitcoin.bfh(Script)
                try:
                    TX=electroncash.Transaction(Script)
                    Inputs=TX.inputs()
                    Inputs[0] and TX.outputs()[0]   #Check there's at least 1 input & output, or else not a TX.
                    for Input in Inputs:
                        if Input['type'] in {'p2sh','unknown'}:    #'p2sh' is usually multisig, but 'unknown' also has a Script.
                            self.get_ops = electroncash.address.Script.get_ops(bitcoin.bfh(Input['scriptSig']))
                            self.ScriptBox.setPlainText(self.get_ops[-1][-1].hex())  #scriptCode to decode.
                    if Script!=self.ScriptBox.toPlainText(): return #P2SH input detected.
                    else: Bytes=''  #Treat TX as though it's a Script, but don't decode.
                except:    #Not a TX, so check if TXID.
                    network=self.window.network
                    if 64==len(Script) and network.is_connected():
                        Get = network.get_raw_tx_for_txid(Script)   #This can cause a (hang) crash if network is disconnected but can't tell. threading seems too complicated.
                        if Get[0]:  #TXID==Script
                            self.ScriptBox.setPlainText(Get[1])
                            return
            except: pass    #Not hex.
        if Bytes:
            endlBefore = 'IF NOTIF ELSE ENDIF RETURN VER VERIF VERNOTIF'.split()   #New line before & after these OpCodes.
            endlAfter = endlBefore+'NUM2BIN BOOLAND'.split()    #NUM2BIN & BOOLAND may look good at line ends.
            Script, endl, IndentSize = '', '\n', 8 #endl gets tabbed after IFs (IF & NOTIF) etc. Try 8 spaces, because default font halves the space size.
            Size, SizeSize, Count = 0, 0, -1  #Size count-down of "current" data push. SizeSize is the "remaining" size of Size (0 for 0<Size<0x4c). Count is the # of Bytes before the current byte on the current line. Target min of 1 & max of 21, bytes/line.
            try:
                for Tuple in self.get_ops[:-1]: Script += '#'+Tuple[1].hex()+endl    #Show full stack leading to redeem Script as asm comments, similar to Blockchain.com, when decoding a full scriptSig.
                self.get_ops=[] #Delete in case of confusion.
            except: pass    #Not decoding a scriptSig with more than a redeem Script.
            for Byte in Bytes:
                Count+=1
                Hex=bitcoin.int_to_hex(Byte,1)  #Byte is an int.
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
                        if Count>=20: Count, Script = -1, Script+endl    #Large data pushes (e.g. HASH160) get their own line.  At most 21B per line. A HASH160 requires 1+20 bytes. Count goes to -1 if word was placed on prior line. 
                    continue
                try:    #OpCode or else new data push.
                    CODE=CodeDict[Hex]
                    if CODE in {'ENDIF','ELSE'}:
                        endl='\n'+endl[ 1+IndentSize : ] #Subtract indent for ENDIF & ELSE.
                        if not Count and Script[-IndentSize:]==' '*IndentSize: Script=Script[:-IndentSize]    #Subtract indent back if already on a new line.
                    if Count and (CODE in endlBefore or 'RESERVED' in CODE): Count, Script = 0, Script+endl     #New line before & after any RESERVED. Count goes to 0 if word placed afterward.
                    if CODE in {'VERIF', 'VERNOTIF'}: Script=Script.rstrip(' ')   #No tab before these since script will fail no matter what.
                    Script+=CODE+' '
                    if CODE in {'ELSE', 'IF', 'NOTIF'}: endl+=' '*IndentSize #Add indent after ELSE, IF & NOTIF.
                    elif 'PUSHDATA' in CODE: SizeHex, SizeSize = '', 2**(Byte-0x4c)  #0x4c is SizeSize=1. SizeHex is to be the little endian hex form of Size.
                    if Count>=20 or CODE in endlAfter or any(Word in CODE for Word in {'RESERVED', 'VERIFY', 'PUSHDATA'}): Count, Script = -1, Script+endl    #New line *after* any VERIFY or PUSHDATA. The latter should only ever occur with large data-pushes.
                except:
                    Size = Byte
                    if Count and Count+Size>20: Count, Script = 0, Script+endl    #New line before too much data.
                    Script+=Hex
            Script=Script.rstrip(' ')+'\n'*(Count!=-1)+'#Auto-decode'   #Final comment shows up like a VERIF.
            if not (Size or SizeSize):   #Successful decode is plausible if all data-pushes completed successfully.
                self.Scripts.append(Script) #This section adds the Auto-decode to memory in the combo-box.
                self.ScriptsBox.addItem(''), self.ScriptsBox.setCurrentText('') #Don't know what address yet to use as Script name.
                ScriptsIndex = self.ScriptsBox.currentIndex()   #Keep track of this because activating the Script can cause it to change to 0 due to Asm-conversion.
                self.HexBox.clear(), self.ScriptActivated()   #Clearing HexBox ensures new colors, in case it's the same re-coding.
                self.ScriptsBox.setItemText(ScriptsIndex, self.Address)
                return  #textChanged signal will return to below this point. Decoder ends here.
        if self.CheckBox.isChecked():  #This section greys out typed '#' even though they don't change bytecode.
            Cursor=self.ScriptBox.textCursor()
            Format=Cursor.charFormat()
            position=Cursor.position()
            if Script and '#'==Script[position-1] and Qt.gray!=Format.foreground():
                Format.setForeground(Qt.gray)
                Cursor.setPosition(position-1), Cursor.setPosition(position,Cursor.KeepAnchor), Cursor.setCharFormat(Format), Cursor.clearSelection()
                self.ScriptBox.setTextCursor(Cursor)
                return  #signal brings us back to below here.
        Script = self.ScriptToHex(Script,False)
        if Script==self.HexBox.toPlainText(): return    #Do nothing if no hex change.
        
        self.HexBox.setPlainText(Script)
        OpCount, ByteCount = '___', str(len(Script)>>1)
        try:
            Bytes = bitcoin.bfh(Script)
            self.Address=electroncash.address.Address.from_multisig_script(Bytes).to_ui_string()
            try: OpCount = str(len(electroncash.address.Script.get_ops(Bytes)))
            except: pass    #PUSHDATA invalid.
        except: self.Address = '_'*42   #42 chars typically in CashAddr. Script invalid.
        self.CountLabel.setText('is the BCH address for the scriptCode above (if valid) with              '+OpCount+' Ops & '+ByteCount+' Bytes')
        self.SetAddress()
        if self.CheckBox.isChecked(): self.setTextColor()
    def ScriptToHex(self,Script,BypassErrors):
        Assembly=''.join(Line.split('#')[0].split('//')[0].upper()+' ' for Line in Script.splitlines()).split()    #This removes all line breaks & comments from assembly code, to start encoding. Both # & // supported.
        Return = ''
        for Str in Assembly:
            try:
                if self.AsmBool and Str in Codes1N: raise #1N in Asm means 011N.
                else: Return+=HexDict[Str.replace('OP_','')]   #Str is OpCode.
            except:
                if BypassErrors: #Necessary for split word selections. e.g. selecting 'R OR' highlights all instances of 0x85.
                    try: bitcoin.bfh(Str)
                    except: continue
                if self.AsmBool: Return+=push_script(Str.lower())
                else:            Return+=            Str.lower()
        return Return
    def ScriptActivated(self):    #Change redeem script with correct case.
        Index, self.AsmBool = self.ScriptsBox.currentIndex(), False    #Loading directly into Asm requires artificially toggling since memory is always in hex.
        if Index==3:   #This section is for 'Clear below'. Maybe gc.collect() could fit in.
            {self.ScriptsBox.removeItem(4) for ItemN in range(4,len(self.Scripts))}
            self.Scripts, Index = self.Scripts[:4], 0   #0 sets to 'New'.
        self.ScriptBox.setPlainText((self.Scripts[Index])), self.ScriptsBox.setCurrentIndex(Index), self.CaseBoxActivated(), self.AsmBoxActivated()
        if self.CheckBox.isChecked(): self.setTextColor()   #Color even if no change in bytecode or hex/asm.
    def SetAddress(self):
        if self.Address and self.CheckBox.isChecked(): self.AddressLabel.setText(self.pColor+self.Address[0]+"</font>"+self.Address[1:])
        else:                                          self.AddressLabel.setText(                                      self.Address)
    def setTextColor(self):
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Format, CursorPos = Cursor.charFormat(), Cursor.position()
        Format.setForeground(Colors['Data']), Format.setBackground(Qt.transparent)
        
        Cursor.setPosition(0), Cursor.movePosition(Cursor.End,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All black. This line guarantees fully transparent background.
        HexCursor.setPosition(0), HexCursor.movePosition(HexCursor.End,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)  #Hex colors actually add a lot of CPU lag.
        if self.CheckBox.isChecked():   #This can max out a CPU core when users hold in a button like '0'. A future possibility is only coloring the current word, unless copy/paste detected.
            StartPosit, HexPos, SizeSize = 0, 0, 2    #Line's absolute position, along with HexBox position. SizeSize is the # of hex digits which are colored in blue, by default.
            ForegroundColor = Colors['Constants']   #This tracks whether a PUSHDATA color should be used for the data-push size.
            for Line in Text.splitlines():
                LineCode=Line.split('#')[0].split('//')[0].upper()
                CommentPos, Pos, lenLine = len(LineCode), StartPosit, len(Line)  #Comment posn, virtual cursor position.
                for Word in LineCode.split():
                    Find, lenWord = LineCode.find(Word), len(Word)
                    Pos+=Find
                    Cursor.setPosition(Pos), HexCursor.setPosition(HexPos)   #This removes Anchor.
                    try:    #to color in Word as OpCode
                        if self.AsmBool and Word in Codes1N: raise #1N not an OpCode in Asm.
                        else: Format.setForeground(ColorDict[Word.replace('OP_','')])
                        Pos+=lenWord
                        Cursor   .setPosition(   Pos,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)
                        HexPos+=2
                        HexCursor.setPosition(HexPos,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        
                        if 'PUSHDATA' in Word:
                            ForegroundColor = Colors['PushData']
                            if   Word.endswith('2'): SizeSize = 4  # of blue digits to follow.
                            elif Word.endswith('4'): SizeSize = 8
                    except: #Assume data push
                        Format.setForeground(ForegroundColor)   #Color 1st SizeSize chars blue if not an opcode.
                        if ForegroundColor!=Colors['Constants']: ForegroundColor=Colors['Constants']
                        
                        if self.AsmBool:
                            if   lenWord > 0xff<<1: SizeSize = 6    #4d____ is 4 extra digits, on top of 2. 6 total only happens for Asm.
                            elif lenWord > 0x4b<<1: SizeSize = 4    #4c__   is 2 extra digits.
                        else: Cursor.setPosition(Pos+SizeSize,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #No leading blue bytes for Asm.
                        HexCursor.setPosition(HexPos+SizeSize,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        Pos   +=lenWord
                        HexPos+=lenWord+self.AsmBool*SizeSize   #Asm jumps ahead in HexPos.
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
    def selectionChanged(self): #Highlight all instances of selected word.
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

        SelectionHex = self.ScriptToHex(Selection,True)
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
    def toggled(self):
        self.Selection=None   #Force re-selection, now w/ or w/o Colors.
        self.SetAddress(), self.selectionChanged(), self.ScriptBox.setFocus()   #QCheckBox steals focus.
    def CaseBoxHighlighted(self,Text): self.CaseBox.setCurrentText(Text), self.CaseBoxActivated()   #Highlighted -> Activated.
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
                    if self.AsmBool and CODE in Codes1N and Word.startswith('OP_'): insertWord = (Index in {2,3})*'OP_' + (Index in {1,4})*'Op_' + (Index in {0,5})*'op_' + CODE   #Asm requires leading _1N.
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
    def AsmBoxHighlighted(self,Text): self.AsmBox.setCurrentText(Text), self.AsmBoxActivated()   #Highlighted -> Activated.
    def AsmBoxActivated(self):  #This method strips out blue leading bytes (asm), or else puts them back in. Instead of editing the ScriptBox string directly, QTextCursor is used.
        AsmBool = bool(self.AsmBox.currentIndex())
        if AsmBool == self.AsmBool: return   #Do nothing if untoggled.
        else: self.AsmBool = AsmBool #Remember for next time.
        
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Script, Cursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor()
        CursorPos, StartPosit, SizeSize = Cursor.position(), 0, 2    #StartPosit is each line's starting posn. SizeSize is the # of leading digits (in a data-push) to delete for coversion to asm.
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
                    if AsmBool and 'PUSHDATA' in WordUp:
                        insertWord = ''  #Strip PUSHDATA OpCodes for asm display.
                        if   WordUp.endswith('2'):  SizeSize = 4  # of leading digits to delete for Asm.
                        elif WordUp.endswith('4'):  SizeSize = 8
                    elif     AsmBool and WordUp in Codes1N: insertWord = 'OP_'+WordUp #e.g. map 10 to OP_10 in Asm.
                    elif not AsmBool and Word   in Codes1N: insertWord = '01'+Word   #This is data, not an OpCode. Map 10 to 0110 in hex.
                    HexDict[WordUp] #If OpCode, generally do nothing.
                except:    #Word isn't an OpCode.
                    if AsmBool: insertWord = Word[SizeSize:]
                    else:   #convert from asm to hex.
                        insertWord = push_script(Word)
                        if   insertWord.startswith('4c'): insertWord = 'PUSHDATA1 '+insertWord[2:]
                        elif insertWord.startswith('4d'): insertWord = 'PUSHDATA2 '+insertWord[2:]  #PUSHDATA4 can't be minimal.
                    if SizeSize!=2: SizeSize=2  #Reset to deleting only 2 digits.
                if Word!=insertWord:
                    Cursor.insertText(insertWord)
                    if not insertWord:
                        Cursor.deleteChar()  #Delete extra space, or \n, when stripping a PUSHDATA. Either is a single B.
                        Word+=' '   #1SUB from lenChange
                lenChange=len(insertWord)-len(Word)
                Pos       +=lenChange
                StartPosit+=lenChange
                LineCode=LineCode[Find+lenWord:]
            StartPosit+=lenLine+1
        Cursor.setPosition(CursorPos)
        self.ScriptBox.setTextCursor(Cursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        self.CaseBoxActivated() #Change spelling as required (OP_ or op_ etc).
        if AsmBool: self.textChanged()  #Converting to Asm deletes incorrect leading bytes, which are impossible to restore.
        elif self.CheckBox.isChecked(): self.setTextColor() #Color leading blue bytes for not-Asm.
