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
Codes['Arithmetic']='1Add 1Sub 2Mul 2Div Negate Abs Not 0NotEqual  \nAdd Sub Mul Div Mod LShift RShift BoolAnd BoolOr NumEqual NumEqualVerify NumNotEqual LessThan GreaterThan LessThanOrEqual GreaterThanOrEqual Min Max  \nWithin'
Codes['Crypto']='RIPEMD160 SHA1 SHA256 Hash160 Hash256 CodeSeparator  \nCheckSig CheckSigVerify CheckMultiSig CheckMultiSigVerify CheckDataSig CheckDataSigVerify ReverseBytes'
Codes['Locktime']='CheckLocktimeVerify NOp2  CheckSequenceVerify NOp3'  #Unary

codesPythonic='pushData1 pushData2 pushData4  nOp notIf endIf  toAltStack fromAltStack ifDup  xOr equalVerify 0notEqual lShift rShift boolAnd boolOr numEqual numEqualVerify numNotEqual lessThan greaterThan lessThanOrEqual greaterThanOrEqual  codeSeparator checkSig checkSigVerify checkMultiSig checkMultiSigVerify checkDataSig checkDataSigVerify reverseBytes  checkLocktimeVerify nOp2 checkSequenceVerify nOp3  verIf verNotIf nOp1 nOp4 nOp5 nOp6 nOp7 nOp8 nOp9 nOp10  '
OpCodesMembers=electroncash.address.OpCodes.__members__.keys()  #Not all EC versions have Native Introspection, which I figure fits in between Locktime & Reserved words.
if 'OP_TXLOCKTIME' in OpCodesMembers:
    Codes['Native Introspection']='InputIndex ActiveBytecode TXVersion TXInputCount TXOutputCount TXLocktime  \nUTXOValue UTXOBytecode OutpointTXHash OutpointIndex InputBytecode InputSequenceNumber OutputValue OutputBytecode'   #Nullary & unary.
    codesPythonic               +='inputIndex activeBytecode txVersion txInputCount txOutputCount txLocktime utxoValue utxoBytecode outpointTxHash outpointIndex inputBytecode inputSequenceNumber outputValue outputBytecode'
Codes['Reserved words']='Reserved Ver VerIf VerNotIf Reserved1 Reserved2 NOp1 NOp4 NOp5 NOp6 NOp7 NOp8 NOp9 NOp10'  #Nullary

Codes['BCH']='\nCAT SPLIT NUM2BIN BIN2NUM AND OR XOR DIV MOD CHECKDATASIG CHECKDATASIGVERIFY REVERSEBYTES' #'MS Shell Dlg 2' is default font but doesn't seem to allow adding serifs (e.g. for BCH codes).
Codes['Disabled']='INVERT 2MUL 2DIV MUL LSHIFT RSHIFT'
#Test line (copy-paste for full spectrum): PUSHDATA1 RETURN TOALTSTACK NUM2BIN INVERT MAX CHECKSIGVERIFY CHECKLOCKTIMEVERIFY TXLOCKTIME RESERVED 
Colors={'Constants':Qt.blue,'Flow control':Qt.darkMagenta,'Stack':Qt.darkGreen,'Splice':Qt.red,'Bitwise logic':QColor(255,128,0),'Arithmetic':QColor(0,128,255),'Crypto':Qt.magenta,'Locktime':Qt.darkYellow,'Reserved words':QColor(128,64,0),'Native Introspection':QColor(128,0,255)}    #Brown is dark-orange. Sky-blue & Purple stem from blue. darkCyan appears too close to darkGreen.
Colors['SelectionForeground'] = Qt.white   #Windows & MX Linux agree on white selection font.
if 'nt' in shutil.os.name:                  Color=QColor(0,120,215) #WIN10 is strong blue.
elif 'Darwin' in shutil.os.uname().sysname: Color, Colors['SelectionForeground'] = QColor(179,215,255), Qt.black     #macOS Catalina is pale blue.
else:                                       Color=QColor(48,140,198)    #MX Linux is medium blue.
Color.setHsl(Color.hslHue(),Color.hslSaturation(),64+.75*Color.lightness())   #This formula decreases darkness of highlighting by 25%, for all OSs.
Colors['SelectionBackground'] = Color

ColorDict, HexDict, CodeDict, CaseDict = {}, {}, {}, {}    #OpCode dictionaries. CodeDict is used by the decoder as a reversed HexDict. ColorDict maps CODE to Color, & CaseDict maps CODE to Code. All dicts could easily be combined into one master dict, but that may not be as fast and elegant, except during initialization. CodeDict & CaseDict can be slow if that's more convenient.
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

CovenantScripts=['',   #This section can provide examples of scripts.
''.join(Codes[key].upper()+'    #'+key+'\n' for key in Codes.keys())+'//Native Introspection OpCodes & MUL will be enabled in 2022.',    #List all the OpCodes.
'''//[UTX, Preimage, Sig, PubKey] 'preturn...' v1.0.4 Script. UTX = (Unspent TX) = Parent. The starting stack items relevant to each line are to its right. Assumes miners can't corrupt a P2PKH sender's sigscript. v1.0.4 is a few bytes smaller than v1.0.2.
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
#14 bits minimum for single input, but add a couple more bits per extra input.
#Never send it SLP tokens!
#Fee between 8 to 12 bits.
#21 BCH max, but I haven't tested over 10tBCH. If the sending txn is somehow malleated (e.g. by miner), then the money may be lost! 
#The private key used to auto-return is 1.
#The sender must not use a PUSHDATA OpCode in the output pkscript (non-standard).
#To return from other addresses currently requires editing qt.py.
''',
''] #Blanks for 'New' & 'Clear all below'.
CovenantScripts[1]=CovenantScripts[1].replace('Bitwise logic','Bitwise logic (unary & binary)').replace('Locktime','Locktime (unary)').replace('Reserved words','Reserved words (nullary)').replace('#BCH','//BCH (binary, unary & ternary)').replace('#Disabled','//Disabled (unary & binary)')   #This section provides some commentary to OpCodes list.
CovenantScripts[1]=CovenantScripts[1].replace('Splice','Splice (unary)').replace('NUM2BIN  ','NUM2BIN    #Splice (binary)')
CovenantScripts[1]=CovenantScripts[1].replace('Arithmetic','Arithmetic (ternary)').replace('MAX  ','MAX    #Arithmetic (binary)').replace('0NOTEQUAL','0NOTEQUAL    #Arithmetic (unary)')
CovenantScripts[1]=CovenantScripts[1].replace('Crypto','Crypto (binary, multary & unary)').replace('CODESEPARATOR  ','CODESEPARATOR    #Crypto (unary & nullary)')
CovenantScripts[1]=CovenantScripts[1].replace('#Native Introspection','#Native Introspection (unary)').replace('TXLOCKTIME  ','TXLOCKTIME    #Native Introspection (nullary)')

ReturnScripts='''
6fad7b828c7f757ca87bbb7d547f7701207f01207f7701247f757daa8801207f7578aa8878820134947f77587f7581788277940239029458807c012a7f77517f7c7f77517f7c7f75a9041976a9147c7e7e0288ac7eaa7c820128947f7701207f7587080500000001e5413e75
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
        self.WebP=Dir+'Icon.webp'    #QMovie only supports GIF & WebP. GIF appears ugly. This file is a color-exchange from the bitcoinbch.com web icon, which may be copyrighted. Animating it looks too difficult for me.
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
    Scripts = CovenantScripts
    def __init__(self, window, plugin):
        QDialog.__init__(self, window)
        self.window, self.plugin = window, plugin
        
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
        try: self.CaseBox.textHighlighted.connect(self.CaseBoxHighlighted)
        except: pass    #textHighlighted signal unavailable in EC-v3.6.6.
        
        Title=QLabel('AutoCove v1.0.5')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)

        self.ScriptsBox = QComboBox()
        self.ScriptsBox.setToolTip('New auto-decodes are stored here.')
        self.ScriptsBox.addItems(["New", "OpCodes", "preturn... v1.0.4", "Clear all below"])
        self.ScriptsBox.setCurrentIndex(2), self.ScriptsBox.activated.connect(self.ScriptActivated)

        HBoxTitle=QHBoxLayout()
        HBoxTitle.addWidget(self.CheckBox,.1), HBoxTitle.addWidget(self.CaseBox,.1), HBoxTitle.addWidget(Title,1), HBoxTitle.addWidget(self.ScriptsBox,.1)
        
        self.ScriptBox=QTextEdit()
        self.ScriptBox.setUndoRedoEnabled(False)    #I'll enable undo etc in a future version, using QTextDocument. IDE is unsafe without both save & undo.
        self.ScriptBox.setLineWrapMode(QTextEdit.NoWrap), self.ScriptBox.setTabStopDistance(12) # 3=space, so 12=4 spaces.
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        self.HexBox=QTextEdit()
        self.HexBox.setReadOnly(True)

        self.AddressLabel=QLabel()
        self.CountLabel=QLabel()
        self.ScriptActivated()    #Assembly Script dumped onto HexBox, to set labels.
        HBoxAddress=QHBoxLayout()
        {HBoxAddress.addWidget(Widget) for Widget in [self.AddressLabel, self.CountLabel]}
        self.CountLabel.setAlignment(Qt.AlignRight)
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, self.CountLabel, self.AddressLabel}}

        VBox=QVBoxLayout()
        VBox.addLayout(HBoxTitle)
        VBox.addWidget(QLabel("Auto-decode P2SH Script hex into readable form by pasting it below. Paste raw txn to decode all its P2SH input Scripts."))
        VBox.addWidget(self.ScriptBox,10), VBox.addWidget(self.HexBox,1)  #Script bigger than hex.
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
            if SInput['type']!='p2pkh': continue
            
            Amount = UTXO['value']-(569+UTX.estimated_size())
            if Amount<546: continue #Dust limit
            
            TX=UTX  #Copy nLocktime.
            TX.inputs().clear(), TX.outputs().clear()
            TX.outputs().append((0,SInput['address'],Amount))    #Covenant requires this exact output, and that it's the only one.
            
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
            try:
                Bytes=bitcoin.bfh(Script)
                try:
                    TX=electroncash.Transaction(Script)
                    Inputs=TX.inputs()
                    Inputs[0] and TX.outputs()[0]   #Check there's at least 1 input & output, or else not a TX.
                    {self.ScriptBox.setPlainText(electroncash.address.Script.get_ops(bitcoin.bfh(Input['scriptSig']))[-1][-1].hex()) for Input in Inputs if Input['type'] in {'p2sh','unknown'}}    #'p2sh' is usually multisig, but 'unknown' also has a Script.
                    if Script!=self.ScriptBox.toPlainText(): return #P2SH input detected.
                    else: Bytes=''  #Treat TX as though it's a Script, but don't decode.
                except: pass    #Not a TX.
            except: pass    #Not hex.
        if Bytes:
            endlBefore = 'IF NOTIF ELSE ENDIF RETURN VER VERIF VERNOTIF'.split()   #New line before & after these OpCodes.
            endlAfter = endlBefore+'NUM2BIN BIN2NUM BOOLAND'.split()    #Binary conversion & BOOLAND may look good at line ends.
            Script, endl = '', '\n' #endl gets tabbed after IFs (IF & NOTIF) etc.
            Size, SizeSize, Words = 0, 0, 0  #Size count-down of "current" data push. SizeSize is the "remaining" size of Size (0 for 0<Size<0x4c). Words is the words on current line s.t. 0<Words/Line<=16.
            for Byte in Bytes:
                Hex=bitcoin.int_to_hex(Byte,1)  #Byte is an int.
                if SizeSize:    #This section is for PUSHDATA2&4 (&1, too).
                    SizeSize-=1
                    SizeHex +=Hex
                    if not SizeSize:    #SizeHex is complete.
                        Size, SizeFull = [ int(bitcoin.rev_hex(SizeHex),16) ]*2 #This is the data-push size. SizeFull remains constant throughout push, but there may be a more elegant code.
                        if Words and Size>=20: Script+=endl    #New line before large data push.
                        Script+=SizeHex
                    continue
                if Size:  #This section is for all data pushes.
                    Size  -=1
                    Script+=Hex
                    if not Size: #End of data push.
                        Script+=' '
                        Words+=1
                        if SizeFull>=20 or Words>=16: Words, Script = 0, Script+endl    #Large data pushes (e.g. HASH160) get their own line.  At most 16 words per line.
                    continue
                try:    #OpCode or else new data push.
                    CODE=CodeDict[Hex]
                    if CODE in {'ENDIF','ELSE'}:
                        endl='\n'+endl[5:] #Subtract tab for ENDIF & ELSE.
                        if not Words and Script[-4:]=='    ': Script=Script[:-4]    #Tab back if already on a new line.
                    if Words and (CODE in endlBefore or 'RESERVED' in CODE): Words, Script = 0, Script+endl     #New line before & after any RESERVED.
                    if CODE in {'VERIF', 'VERNOTIF'}: Script=Script.rstrip(' ')   #No tab before these since script will fail no matter what.
                    Script+=CODE+' '
                    Words+=1
                    if CODE in {'ELSE', 'IF', 'NOTIF'}: endl+='    ' #Add tab after ELSE, IF & NOTIF.
                    elif 'PUSHDATA' in CODE: SizeHex, SizeSize = '', 2**(Byte-0x4c)  #0x4c is SizeSize=1. SizeHex is to be the little endian hex form of Size.
                    if Words>=16 or CODE in endlAfter or any(Word in CODE for Word in {'RESERVED', 'VERIFY'}): Words, Script = 0, Script+endl    #New line *after* any VERIFY.
                except:
                    Size, SizeFull = [ Byte ]*2
                    if Words and Size>=20: Script+=endl    #New line before large data push.
                    Script+=Hex
            Script=Script.rstrip(' ')+'\n'*(Words>0)+'#Auto-decode'
            if not (Size or SizeSize):   #Successful decode is plausible if all data-pushes completed successfully.
                self.Scripts.append(Script) #This section adds the Auto-decode to memory in the combo-box.
                self.ScriptsBox.addItem(''), self.ScriptsBox.setCurrentText('')
                self.HexBox.clear(), self.ScriptActivated()   #Clearing HexBox ensures new colors, in case it's the same re-coding.
                self.ScriptsBox.setItemText(self.ScriptsBox.currentIndex(), self.Address)
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
        Assembly=''.join(Line.split('#')[0].split('//')[0].upper().replace('OP_','')+' ' for Line in Script.splitlines()).split()    #This removes all line breaks & comments from assembly code, to start encoding. Both # & // supported. Strips out OP_.
        Script=''
        for Str in Assembly:
            try:     Script+=HexDict[Str]
            except:  Script+=Str.lower()
        if Script==self.HexBox.toPlainText(): return    #Do nothing if no hex change.
        
        self.HexBox.setPlainText(Script)
        self.CountLabel.setText('is the BCH address for the scriptCode above (if valid) whose size is              '+str(len(Script)>>1)+' Bytes')
        try:    self.Address=electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)).to_ui_string()
        except: self.Address=''
        self.SetAddress()
        if self.CheckBox.isChecked(): self.setTextColor()
        #if self.CheckBox.isChecked(): threading.Thread(target=self.setTextColor).start()   #Can try speeding up the coloring process using a sub-thread etc, but I tried and was slow.
    def ScriptActivated(self):    #Change assembly script with correct case.
        Index=self.ScriptsBox.currentIndex()
        if Index==3:   #This section is for 'Clear below'.
            {self.ScriptsBox.removeItem(4) for ItemN in range(4,len(self.Scripts))}
            self.Scripts, Index = self.Scripts[:4], 0   #0 sets to 'New'.
        self.ScriptBox.setPlainText((self.Scripts[Index])), self.CaseBoxActivated(), self.ScriptsBox.setCurrentIndex(Index)  
        if self.CheckBox.isChecked(): self.setTextColor()   #Color even if no change in bytecode.
    def SetAddress(self):
        if self.Address and self.CheckBox.isChecked(): self.AddressLabel.setText("<font color='blue'>"+self.Address[0]+"</font>"+self.Address[1:])
        else:                                          self.AddressLabel.setText(                                                self.Address)
    def setTextColor(self):
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Format, CursorPos = Cursor.charFormat(), Cursor.position()
        Format.setForeground(Qt.black), Format.setBackground(Qt.transparent)
        Cursor.setPosition(0), Cursor.movePosition(Cursor.End,Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All black. This line guarantees fully transparent background.
        HexCursor.setPosition(0), HexCursor.movePosition(HexCursor.End,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)  #Hex colors actually add a lot of CPU lag.
        if self.CheckBox.isChecked():   #This can max out a CPU core when users hold in a button like '0'. A future possibility is only coloring the current word, unless copy/paste detected.
            StartPosit, HexPos, SizeSize = 0, 0, 2    #Line's absolute position, along with HexBox position. SizeSize is the # of hex digits which are colored in blue, by default.
            for Line in Text.splitlines():
                LineCode=Line.split('#')[0].split('//')[0].upper()
                CommentPos, Pos, lenLine = len(LineCode), StartPosit, len(Line)  #Comment posn, virtual cursor position.
                for Word in LineCode.split():
                    Find, lenWord = LineCode.find(Word), len(Word)
                    Pos+=Find
                    Cursor.setPosition(Pos), HexCursor.setPosition(HexPos)   #This removes Anchor.
                    try:    #to color in Word as OpCode
                        Format.setForeground(ColorDict[Word.replace('OP_','')])
                        Pos+=lenWord
                        Cursor   .setPosition(   Pos,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)
                        HexPos+=2
                        HexCursor.setPosition(HexPos,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        
                        if   'PUSHDATA2' in Word: SizeSize = 4  # of blue digits to follow.
                        elif 'PUSHDATA4' in Word: SizeSize = 8
                    except: #Assume data push
                        Format.setForeground(Colors['Constants'])   #Color 1st 2 chars blue if not an opcode. Then the rest black.
                        Cursor   .setPosition(   Pos+SizeSize,Cursor.KeepAnchor),    Cursor.setCharFormat(Format)
                        HexCursor.setPosition(HexPos+SizeSize,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        Pos   +=lenWord
                        HexPos+=lenWord
                        if SizeSize!=2: SizeSize=2  #Reset to coloring in 2 digits as blue.
                    LineCode=LineCode[Find+lenWord:]
                Cursor.setPosition(StartPosit+CommentPos)   #This section greys out the comments. I treat '//' & '#' the same, but Qt.darkGray or Qt.lightGray could also work for '//'.
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

        Assembly=''.join(Line.split('#')[0].split('//')[0].upper().replace('OP_','')+' ' for Line in Selection.splitlines()).split()    #Remove all line breaks & comments from Selection.
        SelectionHex=''
        for Str in Assembly:
            try:     SelectionHex+=HexDict[Str]
            except:
                try: SelectionHex+=bitcoin.bfh(Str).hex()   #Verify word is hex, or else pass.
                except: pass
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
        CursorPos, StartPosit = Cursor.position(), 0    #StartPosit is each line's starting posn.
        for Line in Script.splitlines():
            LineCode=Line.split('#')[0].split('//')[0].upper()
            Pos, lenLine = StartPosit, len(Line)  #Comment posn, virtual cursor position.
            for Word in LineCode.split():
                Find, lenWord = LineCode.find(Word), len(Word)
                Pos+=Find
                Cursor.setPosition(Pos)
                Pos+=lenWord
                Cursor.setPosition(Pos,Cursor.KeepAnchor)
                
                WordUp=Word.upper().replace('OP_','')
                try:
                    insertWord = (Index==3)*'OP_' + (Index==4)*'Op_' + (Index==5)*'op_' + (Index in {2,3})*WordUp + (Index in {1,4})*CaseDict[WordUp][0] + (Index in {0,5})*CaseDict[WordUp][1]
                    lenChange=len(insertWord)-lenWord
                    Cursor.insertText(insertWord)
                    Pos       +=lenChange
                    StartPosit+=lenChange
                except: pass    #Word isn't an OpCode.
                LineCode=LineCode[Find+lenWord:]
            StartPosit+=lenLine+1
        Cursor.setPosition(CursorPos)
        self.ScriptBox.setTextCursor(Cursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)
