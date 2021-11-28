from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPlainTextEdit, QPushButton, QCheckBox, QComboBox, QMessageBox, QFileDialog
#from electroncash.i18n import _ #Language translator doesn't work on more than one word at a time, at least not when I checked.
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
    def __init__(self, window, plugin):
        QDialog.__init__(self, window)
        self.window, self.plugin = window, plugin
        
        self.HiddenBox=QPlainTextEdit()   #Hidden textbox allow primary Qt thread to broadcast_transaction. Only primary thread is allowed to do this.
        self.HiddenBox.textChanged.connect(self.broadcast_transaction)
        self.Active=True
        threading.Thread(target=self.Thread).start()  
        
        VBox=QVBoxLayout()
        Label=QLabel("Hi,\nThis is a minimum viable release for the AutoCove-Plugin v1.0.0.\nThe idea is that there will be many covenants who automatically forward payments, depending on their assembly code.\nFor example, address 'ppythagoras...' may only return three coins at a time, and only if the same address sends them, and a²+b²=c² (using OP_DIV we could check a/(c+b)=(c-b)/a).\nHere we'll have the power to add/choose from many covenants, and decode/encode their assembly code etc.\nI don't like Spedn & CashScript, so I might not include them as compilers.\nThe TabIcon will change.\n\nIn the case of 'preturn...', it will return whatever coins are sent to it, automatically, assuming a few conditions.\nSender must use a P2PKH address.\nSending transaction must be no more than 520B. Only 3 inputs at most.\n14 bits minimum for only one input.\n21 BCH max, but I've only tested ~$38 at most with this exact address.\n8 bits minimum fee.\nbitcoincash:preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4\nsimpleledger:preturnf8g0qd9pte0u4qkkvlk6t42zz2scxwm83at\n\nThe private key is just 1, but that's OK.\n-Tinos")
        Label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        VBox.addWidget(Label)
        self.setLayout(VBox)
    def broadcast_transaction(self): self.window.broadcast_transaction(electroncash.Transaction(self.HiddenBox.toPlainText()),None)
    def Thread(self):
        Address=electroncash.address.Address.from_string('preturnf8g0qd9pte0u4qkkvlk6t42zz2s5a9qj3r4')
        Script='210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f758708060000000044434675'
        TXRaw='01000000018fa0a26cc66f0ce4d7945f7618fbdbb352c80ec52b34c6a0cd7c730265edef0500000000fdba024cbe0100000001b744c5d4ae66053c8a7a6a5147ac1bb69d4e4b1458fd46bbb55acf31c8000000000000006b483045022100affc94adc0821c512164dab640f9537caa8e2c900df10093c900f74c480e78a8022070ca7ce866b76d0025e836f6f807a6e8e7ffff2db64d4a90ce9933a7b945044a4121025fbed04ee6f174942ccbadbaf8a5044728ee5bc52dda3d1b1698c173927b69b2feffffff01568100000000000017a914f2be0e693a1e06942bcbf9505accfdb4baa842548718ed0a004d280101000000bb31e6a63c2f02a0c2ef75f7f663f405c4f85a4f3fb52e43ee1cd0b764d478ca18606b350cd8bf565266bc352f0caddcf01e8fa789dd8a15386327cf8cabe1988fa0a26cc66f0ce4d7945f7618fbdbb352c80ec52b34c6a0cd7c730265edef05000000008b210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f7587080600000000444346755681000000000000feffffff8b84c80afed89b07268d8f289a6c83f2898b17eb52e31e8b19b2087daa679d2d18ed0a004100000041cb288e13d73f2807afe6a01aae86b734fd4b311ee19a03061c34d3b5d58cc51e773ec4220c441acbaf2a1fcefcfb96ab9f6caf225d42555fba569d935fcb3637414c8b210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f817986fad7b828c7f757ca87bbb7d0144817f770120817f7578aa887882013481947f77587f758178827794025402819458807c012a817f77517f7c817f77517f7c817f75a97c041976a9147e7c7e0288ac7eaa7c82012881947f770120817f758708060000000044434675feffffff01447e0000000000001976a91400000015f446176542da094175afedd60c891f3888ac18ed0a00'
        wallet=self.window.wallet   #The TXRaw is a starting example which is edited as new txns occur. We check every second.
        UTXOskip={None}  #Keep track of UTXOs to skip over.
        while self.Active:
            for UTXO in wallet.get_utxos():
                if UTXO['prevout_hash'] in UTXOskip: continue
                UTXOskip.add(UTXO['prevout_hash'])
                
                if Address!=UTXO['address']: continue
                UTX=electroncash.Transaction(wallet.storage.get('transactions')[UTXO['prevout_hash']])
                
                SInput = UTX.inputs()[0]    #Spent Input. The sender demands their money returned.
                if SInput['type']!='p2pkh': continue
                
                Amount = UTXO['value']-(596+UTX.estimated_size())
                if Amount<546: continue #Dust
                
                TXRaw=TXRaw[:-8]+UTX.raw[-8:] #Copy the UTXO time.
                TX=electroncash.Transaction(TXRaw)
                TX.outputs()[0]=(0,SInput['address'],Amount)    #I've checked the Covenant Script will fail if address or Amount are any different.
                
                Input=TX.inputs()[0]
                Input['prevout_n'] = UTXO['prevout_n']  #Covenant's relative index.
                Input['prevout_hash'] = UTXO['prevout_hash']
                Input['value']=UTXO['value']
                Input['scriptCode']=Script
                PreImage=TX.serialize_preimage(0)
                Sig=electroncash.schnorr.sign((1).to_bytes(32,'big'),bitcoin.Hash(bitcoin.bfh(PreImage)))
                Input['scriptSig']=bitcoin.push_script(UTX.raw)+bitcoin.push_script(PreImage)+bitcoin.push_script(Sig.hex()+'41')+bitcoin.push_script(Script)
                TXRaw=TX.serialize()
                self.HiddenBox.setPlainText(TXRaw)
            time.sleep(1)
