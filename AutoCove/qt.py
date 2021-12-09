from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QMovie, QColor
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit, QCheckBox
import electroncash, zipfile, shutil, threading, time
from electroncash import bitcoin
from electroncash.i18n import _ #Language translator didn't work on more than one word at a time, when I checked.
from electroncash.plugins import BasePlugin, hook

Codes={'Constants': '0 FALSE  PUSHDATA1 PUSHDATA2 PUSHDATA4 1NEGATE  1 TRUE '+''.join(' '+str(N) for N in range(2,17))}   #Start Codes dictionary, used only for colors.
Codes['Flow control']='NOP IF NOTIF ELSE ENDIF VERIFY RETURN'
Codes['Stack']='TOALTSTACK FROMALTSTACK 2DROP 2DUP 3DUP 2OVER 2ROT 2SWAP IFDUP DEPTH DROP DUP NIP OVER PICK ROLL ROT SWAP TUCK'
Codes['Splice']='CAT SPLIT NUM2BIN BIN2NUM SIZE'    #NUM2BIN & BIN2NUM take Splice hex codes, but are they really Splice? BIN2NUM is often needed to SPLIT, but NUM2BIN is used for amounts (in sats).
Codes['Bitwise logic']='INVERT AND OR XOR EQUAL EQUALVERIFY'
Codes['Arithmetic']='1ADD 1SUB 2MUL 2DIV NEGATE ABS NOT 0NOTEQUAL ADD SUB MUL DIV MOD LSHIFT RSHIFT BOOLAND BOOLOR NUMEQUAL NUMEQUALVERIFY NUMNOTEQUAL LESSTHAN GREATERTHAN LESSTHANOREQUAL GREATERTHANOREQUAL MIN MAX WITHIN'
Codes['Crypto']='RIPEMD160 SHA1 SHA256 HASH160 HASH256 CODESEPARATOR CHECKSIG CHECKSIGVERIFY CHECKMULTISIG CHECKMULTISIGVERIFY CHECKDATASIG CHECKDATASIGVERIFY'
Codes['Locktime']='CHECKLOCKTIMEVERIFY NOP2  CHECKSEQUENCEVERIFY NOP3'
Codes['Reserved words']='RESERVED VER VERIF VERNOTIF RESERVED1 RESERVED2 NOP1 NOP4 NOP5 NOP6 NOP7 NOP8 NOP9 NOP10'
Codes['BCH']='CAT SPLIT NUM2BIN BIN2NUM AND OR XOR DIV MOD CHECKDATASIG CHECKDATASIGVERIFY'

Colors={'Constants':Qt.blue,'Flow control':Qt.darkMagenta,'Stack':Qt.darkGreen,'Splice':Qt.red,'Bitwise logic':QColor(255,127,0),'Arithmetic':QColor(0,127,255),'Crypto':Qt.magenta,'Locktime':Qt.darkCyan,'Reserved words':Qt.darkYellow}
Colors['SelectionForeground'] = Qt.white   #Windows & MX Linux agree on white selection font. 
if 'nt' in shutil.os.name: Colors['SelectionBackground']=QColor(0,120,215)
elif 'Darwin' in shutil.os.uname().sysname: Colors['SelectionForeground'], Colors['SelectionBackground'] = Qt.black, QColor(179,215,255)  #macOS Catalina selections use black font with pale blue background.
else:                      Colors['SelectionBackground']=QColor(48,140,198)    #MX Linux uses medium blue.

ColorDict, HexDict = {}, {}    #OpCode dictionaries.
for key in Codes.keys()-{'BCH'}:
    for Code in Codes[key].split(): ColorDict[Code], ColorDict['OP_'+Code] = [ Colors[key] ]*2
#Test line (copy-paste for full spectrum): FALSE RETURN TOALTSTACK CAT INVERT 1ADD RIPEMD160 CHECKLOCKTIMEVERIFY RESERVED 
for Code in electroncash.address.OpCodes.__members__.keys(): HexDict[Code], HexDict[Code[3:]] = [ bitcoin.int_to_hex(electroncash.address.OpCodes[Code].value) ]*2   #Construct HexDict separately to colors because testnet version has more OpCodes.

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
080600000000444346 DROP #[Bool] Append nonce for vanity address, generated from VanityTXID-Plugin.\n''', 

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
080600000001292a86 DROP #[nVersion] Append nonce for vanity address, generated from VanityTXID-Plugin.\n''',

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
0803000000001cf0d6 DROP #[nVersion] Append nonce for vanity address, generated using VanityTXID-Plugin.\n''',
''.join('\n'*(key=='BCH') + Codes[key]+'    #'+key+'\n' for key in Codes.keys())]   #List all the OpCodes.

class Plugin(BasePlugin):
    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.windows, self.tabs, self.UIs = {}, {}, {}  #Initialize plugin wallet dictionaries.
  
        Dir=self.parent.get_external_plugin_dir()+'/AutoCove/'
        self.WebP=Dir+'Icon.webp'    #QMovie only supports GIF & WebP. GIF appears ugly. This file is a color-exchange from the bitcoinbch.com web icon, which is probably copyrighted. Animating it looks too difficult for me.
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
            Tabs.setTabIcon(Tabs.indexOf(self.tabs[wallet_name]),self.Icon) #It's probably more elegant to keep track of each tab index using a pyqt5 signal connection, instead of constantly asking for it. I'm not sure how.
class UI(QDialog):
    Scripts='''
210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f758708060000000044434675
210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794027902819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7882012881947f770120817f7588547f0120817f0120817f770124817f75aa88080600000001292a8675
6fad7b828c7f757ca87bbb7d01447f7701207f7578aa8878820134947f77587f758178827794023f029458807c012a7f77517f7c7f77517f7c7f75a97c041976a9147e7c7e0288ac7eaa78820128947f7701207f7588547f01207f01207f7701247f75aa880803000000001cf0d675
'''.splitlines()[1:]    #The covenant script hex is only needed by the watching-only wallet.
    Addresses=[electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)) for Script in Scripts]
    
    def __init__(self, window, plugin):
        QDialog.__init__(self, window)
        self.window, self.plugin = window, plugin
        
        self.Thread, self.UTXOs = threading.Thread(), {}    #Empty thread & set of UTXOs to skip over. A separate thread delays auto-broadcasts so wallet has time to analyze history. If main thread is delayed, then maybe it can't analyze the wallet's history.
        window.history_updated_signal.connect(self.history_updated) #This detects preturn UTXOs.
        self.HiddenBox=QTextEdit()  #HiddenBox connection allows broadcasting from sub-thread, after sleeping.
        self.HiddenBox.textChanged.connect(self.broadcast_transaction)

        self.CheckBox = QCheckBox('Colors')
        self.CheckBox.setToolTip("Slows down typing.\nNot sure how colors should be assigned.\nPUSHDATA2 (& 4) won't have correct blue coloring.\nToo difficult to add serifs to BCH codes.")
        self.CheckBox.setChecked(True), self.CheckBox.toggled.connect(self.toggled)
                
        Title=QLabel('AutoCove v1.0.2')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)
        
        self.ComboBox = QComboBox()
        self.ComboBox.setToolTip('Remember to only ever send from a P2PKH address, and follow the other rules.')
        self.ComboBox.addItems(["v1.0.0", "v1.0.1", "v1.0.2", "OpCodes"])
        self.ComboBox.setCurrentIndex(2), self.ComboBox.activated.connect(self.VersionSwitch)
        
        HBoxTitle=QHBoxLayout()
        HBoxTitle.addWidget(self.CheckBox,.1), HBoxTitle.addWidget(Title,1), HBoxTitle.addWidget(self.ComboBox,.1)
        
        self.ScriptBox=QTextEdit()
        self.ScriptBox.setUndoRedoEnabled(False)    #I'll enable undo etc in a future version, using QTextDocument. IDE is unsafe without both save & undo. I'm more interested in programming a hex decoder instead.
        self.ScriptBox.setLineWrapMode(QTextEdit.NoWrap), self.ScriptBox.setTabStopDistance(24) # 3=space, which is half a char, so 24=4chars.
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        self.HexBox=QTextEdit()
        self.HexBox.setReadOnly(True)

        self.AddressLabel=QLabel()
        self.AddressLabel.setTextFormat(Qt.RichText)
        DescLabel = QLabel('is the BCH address for the scriptCode above (if valid) whose size is')
        self.CountLabel=QLabel()
        self.VersionSwitch()    #Assembly Script dumped onto HexBox.
        HBoxAddress=QHBoxLayout()
        {HBoxAddress.addWidget(Widget) for Widget in [self.AddressLabel, DescLabel, self.CountLabel]}
        self.CountLabel.setAlignment(Qt.AlignRight)
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, self.CountLabel, DescLabel, self.AddressLabel}}
        
        DescriptionBox=QTextEdit()
        DescriptionBox.setReadOnly(True)
        DescriptionBox.setPlainText("If a 'preturn...' address (versions 1.0.0 to 1.0.2) is added to a watching-only wallet, this plugin will automatically broadcast the return txns.\nSender must use a P2PKH address, not P2PK nor P2SH.\nSending txn SIZE must be at most 520 Bytes (3 inputs max).\n14 bits minimum for single input, but greater minimum for more inputs.\n8 bits minimum fee.\n21 BCH max, but only a single BCH has ever been tested.\nIf the sending txn is malleated (e.g. by miner), then all money will be lost! Native introspection in 2022 should result in a safe version.\nThe private key used is always 1.\nThe sender must not use a PUSHDATA OpCode in the output pkscript (non-standard).\nNever send SLP tokens, or they'll be burned!")

        VBox=QVBoxLayout()
        VBox.addLayout(HBoxTitle)
        VBox.addWidget(self.ScriptBox,10)  #Bigger Assembly.
        VBox.addWidget(self.HexBox,1)
        VBox.addLayout(HBoxAddress)
        VBox.addWidget(DescriptionBox,1)
        self.setLayout(VBox)
    def history_updated(self):
        if self.Thread.isAlive(): return    #Don't double broadcast the same return.
        self.Thread=threading.Thread(target=self.ThreadMethod)
        self.Thread.start()
    def ThreadMethod(self):
        time.sleep(1)
        window=self.window
        if not window.network.is_connected(): return
        
        wallet=window.wallet
        for UTXO in wallet.get_utxos():
            if (UTXO['prevout_hash'], UTXO['prevout_n']) in self.UTXOs.items(): continue    #UTXOs to skip over.
            self.UTXOs[UTXO['prevout_hash']]=UTXO['prevout_n']
        
            try: index=self.Addresses.index(UTXO['address'])
            except: continue    #Not an AutoCove UTXO.
            UTX=electroncash.Transaction(wallet.storage.get('transactions')[UTXO['prevout_hash']])
            
            SInput = UTX.inputs()[0]    #Spent Input. The sender demands their money returned. Covenant requires input 0 is sender.
            if SInput['type']!='p2pkh': continue
            
            Amount = UTXO['value']-(596+37*(index>0)-58*(index>1)+UTX.estimated_size())  #37 sats extra for v1.0.1 & 58 sats less for v1.0.2.
            if Amount<546: continue #Dust
            
            TX=UTX  #Copy nLocktime.
            TX.inputs().clear(), TX.outputs().clear()
            TX.outputs().append((0,SInput['address'],Amount))    #All covenant scripts require this exact output, and that it's the only one.
            
            UTXO['type'], UTXO['scriptCode'] = 'unknown', self.Scripts[index]
            TX.inputs().append(UTXO)    #Covenants (except v1.0.0) also require return TX have only 1 input.

            PreImage=TX.serialize_preimage(0)
            Sig=electroncash.schnorr.sign((1).to_bytes(32,'big'),bitcoin.Hash(bitcoin.bfh(PreImage)))
            TX.inputs()[0]['scriptSig']=bitcoin.push_script(UTX.raw)+bitcoin.push_script(PreImage)+bitcoin.push_script(Sig.hex()+'41')+bitcoin.push_script(PubKey)*(index>1)+bitcoin.push_script(self.Scripts[index])
            TX=TX.serialize()
            if TX!=self.HiddenBox.toPlainText(): self.HiddenBox.setPlainText(TX)    #Don't double broadcast!
    def broadcast_transaction(self): self.window.broadcast_transaction(electroncash.Transaction(self.HiddenBox.toPlainText()),None)  #description=None.
    def ToHex(self,Script): #This method handles both complete Script as well as selections!
        Assembly=''.join(Line.split('#')[0].upper()+' ' for Line in Script.splitlines())    #This removes all line breaks & comments from assembly code.
        ScriptHex=''
        for Str in Assembly.split():
            if Str in HexDict.keys(): ScriptHex+=HexDict[Str]
            else:                     ScriptHex+=Str
        return ScriptHex
    def textChanged(self):  #Whenever users type, attempt to re-compile.
        Script=self.ToHex(self.ScriptBox.toPlainText())
        self.HexBox.setPlainText(Script.lower())
        self.lenHex=len(Script) #Need this for coloring HexBox.
        self.CountLabel.setText(str(self.lenHex>>1)+' Bytes')
        try:
            Address=electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)).to_ui_string()
            if self.CheckBox.isChecked(): Address="<font color='blue'>"+Address[0]+"</font>"+Address[1:]
            self.AddressLabel.setText(Address)
        except: self.AddressLabel.setText('')
        if self.CheckBox.isChecked(): self.setTextColor()
        #if self.CheckBox.isChecked(): threading.Thread(target=self.setTextColor).start()   #Can try speeding up the coloring process using a sub-thread etc, but I tried and was too slow.
    def VersionSwitch(self): self.ScriptBox.setPlainText(CovenantScripts[self.ComboBox.currentIndex()])    #Change version of 'preturn...' covenant display.
    def setTextColor(self):
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText(), self.ScriptBox.textCursor(), self.HexBox.textCursor()   #It might be much faster to combine both ScriptBox & HexBox into one box, because then only one cursor is needed.
        Format, CursorPos = Cursor.charFormat(), Cursor.position()
        Format.setForeground(Qt.black), Format.setBackground(Qt.transparent)
        Cursor.setPosition(0), Cursor.setPosition(len(Text),Cursor.KeepAnchor), Cursor.setCharFormat(Format)   #All black. This line guarantees fully transparent background.
        HexCursor.setPosition(0), HexCursor.setPosition(self.lenHex,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)  #Hex colors actually add a lot of CPU lag.
        # Font=Format.font()    #Everything to do with .font is just for adding serifs to BCH codes. Unfortunately 'MS Shell Dlg 2' doesn't seem to have a serif version.
        if self.CheckBox.isChecked():   #This will max out a CPU core when users hold in spacebar.
            StartPosit=0    #Line's position.
            HexPos=0
            for Line in Text.splitlines():
                Pos=StartPosit  #Virtual cursor position.
                CommentPos=Line.find('#')
                if CommentPos<0: CommentPos=len(Line)
                LineCode=Line[:CommentPos].upper()
                for Word in LineCode.split():
                    Find=LineCode.find(Word)
                    Pos+=Find
                    Cursor.setPosition(Pos), HexCursor.setPosition(HexPos)   #This removes Anchor.
                    if Word in ColorDict.keys():
                        # if WordUpper in Codes['BCH']: Font.setFamily('MS Serif')
                        # else: Font.setFamily('MS Shell Dlg 2')
                        # Format.setFont(Font)
                        Format.setForeground(ColorDict[Word])
                        Pos+=len(Word)
                        Cursor.setPosition(Pos,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                        HexPos+=2
                        HexCursor.setPosition(HexPos,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                    else:
                        Format.setForeground(Colors['Constants'])   #Color 1st 2 chars blue if not an opcode. Then the rest black.
                        Cursor.setPosition(Pos+2,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                        Pos+=len(Word)
                        HexCursor.setPosition(HexPos+2,Cursor.KeepAnchor), HexCursor.setCharFormat(Format)
                        HexPos+=len(Word)
                    LineCode=LineCode[Find+len(Word):]  #Python strings are immutable so this should be efficient.
                # Font.setFamily('MS Shell Dlg 2'), Format.setFont(Font)
                Cursor.setPosition(StartPosit+CommentPos)   #This section greys out the comments.
                StartPosit+=len(Line)
                Format.setForeground(Qt.gray)
                Cursor.setPosition(StartPosit,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
                StartPosit+=1 #'\n' is 1 Byte. Do this last in case # is on last line.
        Cursor.setPosition(CursorPos), HexCursor.setPosition(0)
        self.ScriptBox.setTextCursor(Cursor), self.HexBox.setTextCursor(HexCursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)
        #self.ScriptBox.setFontFamily('MS Shell Dlg 2')
    def selectionChanged(self): #Select all instances of selected word.
        Text, Cursor, HexCursor = self.ScriptBox.toPlainText().upper(), self.ScriptBox.textCursor(), self.HexBox.textCursor()
        Format, Selection, CursorPos, selectionStart, selectionEnd = Cursor.charFormat(), Cursor.selectedText().upper(), Cursor.position(), Cursor.selectionStart(), Cursor.selectionEnd()
        Format.setForeground(Colors['SelectionForeground']), Format.setBackground(Colors['SelectionBackground'])
        
        self.setTextColor() #Undo any previous highlighting, & disconnect.
        self.ScriptBox.textChanged.disconnect(), self.ScriptBox.selectionChanged.disconnect()
        
        Find, Pos = Text.find(Selection), 0   #Virtual cursor position.
        while Selection and Find>=0:    #Ignore empty selection.
            Pos+=Find
            Cursor.setPosition(Pos)
            Pos+=len(Selection)
            Cursor.setPosition(Pos,Cursor.KeepAnchor), Cursor.setCharFormat(Format)
            Text=Text[Find+len(Selection):]
            Find=Text.find(Selection)
        if CursorPos>selectionStart: Cursor.setPosition(selectionStart)
        else:                        Cursor.setPosition(selectionEnd) #Right-to-left selection.
        Cursor.setPosition(CursorPos,Cursor.KeepAnchor), self.ScriptBox.setTextCursor(Cursor)
        self.ScriptBox.textChanged.connect(self.textChanged), self.ScriptBox.selectionChanged.connect(self.selectionChanged)

        SelectionHex=self.ToHex(Selection)
        try: Bytes, SelectionBytes = bitcoin.bfh(self.HexBox.toPlainText()), bitcoin.bfh(SelectionHex)
        except: return
        Find, Pos = Bytes.find(SelectionBytes), 0
        while SelectionBytes and Find>=0:
            Pos+=Find*2
            HexCursor.setPosition(Pos)
            Pos+=len(SelectionHex)
            HexCursor.setPosition(Pos,HexCursor.KeepAnchor), HexCursor.setCharFormat(Format)
            Bytes=Bytes[Find+len(SelectionBytes):]
            Find=Bytes.find(SelectionBytes)
        HexCursor.setPosition(0), self.HexBox.setTextCursor(HexCursor)
    def toggled(self): self.selectionChanged(), self.ScriptBox.setFocus()   #QCheckBox steals focus.
        