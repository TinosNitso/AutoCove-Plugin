from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QComboBox
from electroncash.i18n import _ #Language translator didn't work on more than one word at a time, when I checked.
from electroncash.plugins import BasePlugin, hook
import electroncash, threading, zipfile, shutil, time
from electroncash import bitcoin

class Plugin(BasePlugin):
    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.windows, self.tabs, self.UIs = {}, {}, {}  #Initialize plugin wallet "dictionaries".
        
        Dir=self.parent.get_external_plugin_dir()+'/AutoCove/'
        self.WebP=Dir+'Icon.webp'    #QMovie only supports GIF & WebP. GIF appears ugly.
        if shutil.os.path.exists(Dir): Extract=False   #Only ever extract zip (i.e. install) once.
        else:
            Extract=True
            Zip=zipfile.ZipFile(Dir[:-1]+'-Plugin.zip') #shutil._unpack_zipfile is an alternative function, but it'd extract everything.
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
        self.UIs[wallet_name].Active=False
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
'''.splitlines()[1:]
    Addresses=[electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)) for Script in Scripts]
    Assembly=[
'''# 'preturn...' v1.0.0 Script source-code. I like writing the starting stack items relevant to each line, to the right of it.
210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798	#[TXParent, Preimage, Sig] before [, PubKey].
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY	#[..., Preimage, Sig, PubKey] Proof DATA = Preimage
TUCK 0144 BIN2NUM SPLIT NIP 0120 BIN2NUM SPLIT DROP	#[TX, Preimage] Preimage Outpoint TXID
OVER HASH256 EQUALVERIFY	#[..., TX, TXID] Proof TXParentID = Outpoint TXID
OVER SIZE 0134 BIN2NUM SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM	#[Preimage, TX] Calulate input value from Preimage
OVER SIZE NIP SUB  025402 BIN2NUM SUB  8 NUM2BIN	#[..., TX, Amount] Subtract fee of (SIZE(TXParent)+596).
SWAP 012a BIN2NUM SPLIT NIP  1 SPLIT  SWAP BIN2NUM SPLIT NIP	# [..., TX, Amount] NIP start & sender sig off TX.
1 SPLIT  SWAP BIN2NUM SPLIT DROP   HASH160	#[..., TXSPLIT] 1ST input to parent has this address.
SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256	#[..., Amount, Address] Predict hashOutputs.
SWAP SIZE 0128 BIN2NUM SUB SPLIT NIP 0120 BIN2NUM SPLIT DROP  EQUAL	#[Preimage,hashOutputs] Proof hashOutputs EQUAL Amount & Address from Parent.
080600000000444346 DROP #[Bool] Append nonce for vanity address, generated from VanityTXID-Plugin.\n''', 

'''# 'preturn...' v1.0.1 Script source-code. I like writing the starting stack items relevant to each line, to the right of it. This update adds 1 line, a 5% fee increase, to guarantee return has only 1 input.
210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798	#[TXParent, Preimage, Sig] before [, PubKey].
3DUP CHECKSIGVERIFY  ROT SIZE 1SUB SPLIT DROP  SWAP SHA256  ROT CHECKDATASIGVERIFY	#[..., Preimage, Sig, PubKey] Proof DATA = Preimage
TUCK 0144 BIN2NUM SPLIT NIP 0120 BIN2NUM SPLIT DROP	#[TX, Preimage] Preimage Outpoint TXID
OVER HASH256 EQUALVERIFY	#[..., TX, TXID] Proof TXParentID = Outpoint TXID
OVER SIZE 0134 BIN2NUM SUB SPLIT NIP  8 SPLIT DROP  BIN2NUM	#[Preimage, TX] Calulate input value from Preimage
OVER SIZE NIP SUB  027902 BIN2NUM SUB  8 NUM2BIN	#[..., TX, Amount] Subtract fee of (SIZE(TXParent)+596+37).
SWAP 012a BIN2NUM SPLIT NIP  1 SPLIT  SWAP BIN2NUM SPLIT NIP	# [..., TX, Amount] NIP start & sender sig off TX.
1 SPLIT  SWAP BIN2NUM SPLIT DROP   HASH160	#[..., TXSPLIT] 1ST input to parent has this address.
SWAP 041976a914 CAT SWAP CAT 0288ac CAT  HASH256	#[..., Amount, Address] Predict hashOutputs.
OVER SIZE 0128 BIN2NUM SUB SPLIT NIP 0120 BIN2NUM SPLIT DROP  EQUALVERIFY	#[Preimage,hashOutputs] Proof hashOutputs EQUAL Amount & Address from Parent.
4 SPLIT  0120 BIN2NUM SPLIT  0120 BIN2NUM SPLIT NIP  0124 BIN2NUM SPLIT DROP  HASH256 EQUALVERIFY #[Preimage] Proof of only 1 input in return TX.
080600000001292a86 DROP #[nVersion] Append nonce for vanity address, generated from VanityTXID-Plugin.\n''']
    def __init__(self, window, plugin):
        QDialog.__init__(self, window)
        self.window, self.plugin = window, plugin
        
        self.UTXOs=None    #List of UTXOs to skip over.
        window.history_updated_signal.connect(self.history_updated)
        
        Title=QLabel('AutoCove IDE')
        Title.setStyleSheet('font-weight: bold'), Title.setAlignment(Qt.AlignCenter)
        
        self.ComboBox = QComboBox()
        self.ComboBox.addItems(['v1.0.0', 'v1.0.1'])
        self.ComboBox.setCurrentIndex(1)
        self.ComboBox.activated.connect(self.VersionSwitch)
        
        HBox=QHBoxLayout()
        HBox.addWidget(Title,1)
        HBox.addWidget(self.ComboBox,.1)
        
        self.AssemblyBox=QPlainTextEdit()
        self.AssemblyBox.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.AssemblyBox.textChanged.connect(self.Compile)

        self.ScriptBox=QPlainTextEdit()
        self.ScriptBox.setReadOnly(True)
        self.VersionSwitch()    #Assembly Script dumped onto ScriptBox.

        LabelBig=QLabel("If a 'preturn...' address (v1.0.1 or v1.0.0) is added to a watching-only wallet, this plugin will automatically enforce the return txns.\nSending txn SIZE must be smaller than 520 Bytes (3 inputs max).\n14 bits minimum for single input, but greater minimum for more inputs.\n8 bits minimum fee.\n21 BCH max, but only a single BCH has ever been tested.\nThe private key is always 1.")
        {Label.setTextInteractionFlags(Qt.TextSelectableByMouse) for Label in {Title, LabelBig}}
        
        VBox=QVBoxLayout()
        VBox.addLayout(HBox)
        VBox.addWidget(self.AssemblyBox,3)  #3x bigger Assembly.
        VBox.addWidget(self.ScriptBox,1)
        VBox.addWidget(LabelBig)
        self.setLayout(VBox)
    def history_updated(self):
        window=self.window
        wallet=window.wallet   
        UTXOs=wallet.get_utxos()
        if self.UTXOs==UTXOs: return    #No change in UTXOs.
        self.UTXOs=UTXOs
        for UTXO in UTXOs:
            try: index=self.Addresses.index(UTXO['address'])
            except: continue    #Not an AutoCove UTXO.
            UTX=electroncash.Transaction(wallet.storage.get('transactions')[UTXO['prevout_hash']])
            
            SInput = UTX.inputs()[0]    #Spent Input. The sender demands their money returned. Covenant requires input 0 is sender.
            if SInput['type']!='p2pkh': continue
            
            Amount = UTXO['value']-(596+37*index+UTX.estimated_size())  #v1.0.1 costs precisely 37 sats extra, to block multi-input return. (Technically 36 Bytes, but I set the covenant to 37 sats.)
            if Amount<546: continue #Dust
            
            TX=UTX  #Copy nLocktime.
            TX.inputs().clear(), TX.outputs().clear()
            TX.outputs().append((0,SInput['address'],Amount))    #I've verified the Covenant Script will fail if address or Amount are any different.
            
            UTXO['type'], UTXO['scriptCode'] = 'unknown', self.Scripts[index]
            TX.inputs().append(UTXO)    #Covenant also requires return TX have only 1 input.

            PreImage=TX.serialize_preimage(0)
            Sig=electroncash.schnorr.sign((1).to_bytes(32,'big'),bitcoin.Hash(bitcoin.bfh(PreImage)))
            TX.inputs()[0]['scriptSig']=bitcoin.push_script(UTX.raw)+bitcoin.push_script(PreImage)+bitcoin.push_script(Sig.hex()+'41')+bitcoin.push_script(self.Scripts[index])
            window.broadcast_transaction(electroncash.Transaction(TX.serialize()),None) #Throws error if we don't call .Transaction.
    def Compile(self):
        Assembly=''.join(Line.split('#')[0].upper()+' ' for Line in self.AssemblyBox.toPlainText().splitlines())    #This removes all line breaks & comments from assembly code.
        Script=''
        for Str in Assembly.split():
            try:        Script+=bitcoin.int_to_hex(eval('electroncash.address.OpCodes.OP_'+Str).value)
            except: 
                try:    Script+=bitcoin.int_to_hex(eval('electroncash.address.OpCodes.'+Str).value)
                except: Script+=Str
        try:    Address=electroncash.address.Address.from_multisig_script(bitcoin.bfh(Script)).to_ui_string()
        except: Address=''
        self.ScriptBox.setPlainText(Script.lower()+'\n'+str(int(len(Script)/2))+' Bytes scriptCode ↑ with BCH address ↓\n'+Address)
    def VersionSwitch(self): self.AssemblyBox.setPlainText(self.Assembly[self.ComboBox.currentIndex()])    
        