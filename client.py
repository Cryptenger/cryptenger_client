# coding=utf-8
#les modules faisant parti de la librairie standard de python :
import sys, random, os, functools, datetime, json, time, socket, select
#nous utilison la librairie graphiqye PyQt5
try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import *
except:
    print('You must install the PyQt5 library')
    print('You can do it with the following command on your Commands Prompt')
    print('pip install PyQt5')
    quit = input('press a key to quit')
    exit()

#nos propres modules
from gui import mainWidgetOBJ, connectionWidgetOBJ, warningOBG
from crypting import Crypting


#les commentaires d'explications sont disposés dans les déclarations de fonctions principalement. Les pararmètres ne sont pas forcément expliqués lors des appels de fonctions.

#le serveur n'envoieque des strings pures et par paquets de 1 Ko
#nous utilisons le json pour dialoguer avec le serveur
#Donc si l'historique est trop long il n'est pas envoyé d'un seul coup.
#Tant qu'il n'est pas entier on stoque l'historique dans la variable history


class WorkerSignals(QtCore.QObject):
    """
    Worker signal
    """
    result = QtCore.pyqtSignal(object)

class Worker(QtCore.QObject):#QRunnable):
    '''
    Worker thread    ben le truc qui recoit le message
    '''
    received_message = QtCore.pyqtSignal(str)


    def __init__(self, parent):
        super(Worker, self).__init__()
        self.parent = parent

        self.signals = WorkerSignals()

        self.history = ''

    @QtCore.pyqtSlot()
    def run(self):
        # global history
        while True:
            try:
                server_message, wlist, xlist = select.select([self.parent.server_connection], [], [], 0.05)

                if len(server_message) != 0:
                    # Client est de type socket
                    msg_received = server_message[0].recv(2048)
                    # Peut planter si le message contient des caractères spéciaux
                    self.received_message.emit(msg_received.decode()) # On envoie le message à la fonction pour le traiter [déchiffrage, affichage...]
            except Exception as ex :
                warning = warningOBG(
                    parent=self.parent,
                    windowTitle="Server closed",
                    h1text="Server closed",
                    informativeText="The server has been closed. \nYou may contact your host",
                    pythonError=str(ex)
                    )

class MainWindow(QMainWindow):
    """Ben, tout Cryptenger"""
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.initWindow()
        self.buildWindow()

        self.crypting = Crypting()

    def closeEvent(self, event):
        """fonction appelée (toute seule) quand l'utilisateur ferme cryptenger"""
        try: # Test pour voir si la connexion avec serveur est faite
            self.server_connection.send("<Close_the_connection>".encode()) # on envoie la fermeture de la connexion
        except:
            pass # Le connexion n'est pas faite, on ferme juste le client

        print("Cryptenger closed")
        try:    #on mettra ici toutes les fenêtres à fermer
            self.cryptenger_win.settings.close()
        except:
            pass
        sys.exit()

    def initWindow(self):                                                       #les self.settings de la fenêtre principale

        with open("./settings.json", "r") as app_settings:
            self.app_settings = json.load(app_settings)
        self.setGeometry(
            self.app_settings["cryptenger_win"]["window_location"][0],
            self.app_settings["cryptenger_win"]["window_location"][1],
            self.app_settings["cryptenger_win"]["connection_window_size"][0],
            self.app_settings["cryptenger_win"]["connection_window_size"][1]
            # 720, 300
        )
        self.setWindowTitle('Cryptenger')
        self.setWindowIcon(QtGui.QIcon('./assets/ico/cryptenger_icon.ico'))
        # self.setMinimumWidth(self.app_settings["cryptenger_win"]["connection_window_minimum_size"][0])
        # self.setMinimumHeight(self.app_settings["cryptenger_win"]["connection_window_minimum_size"][1])


        with open(self.app_settings["default_style"], "r") as style:
            styleSheet = style.read()
            self.setStyleSheet(styleSheet)


    def buildWindow(self):                                                      #le contenu de la fenêtre principale
        #fenêtre de connection
        self.connection_widget = connectionWidgetOBJ()      #on appelle la fenêtre de connection
        self.connection_widget.start_btn.clicked.connect(self.connectAndRunSever)
        self.connection_widget.firstName_lne.returnPressed.connect(self.connectAndRunSever)
        self.connection_widget.adresse_lne.returnPressed.connect(self.connectAndRunSever)
        self.connection_widget.port_lne.returnPressed.connect(self.connectAndRunSever)

        #layout de la fenêtre principale
        self.main_V_lyt = QVBoxLayout()
        self.main_V_lyt.addWidget(self.connection_widget)

        """TEMP PARCE QUE RELOU"""
        self.connection_widget.firstName_lne.setText(self.app_settings["default_login_data"]["username"])
        self.connection_widget.adresse_lne.setText(self.app_settings["default_login_data"]["adress"])
        self.connection_widget.port_lne.setText(self.app_settings["default_login_data"]["port"])

        #widget
        widget = QWidget()
        widget.setLayout(self.main_V_lyt)

        #QMainWindow
        self.setCentralWidget(widget)
        self.show()


    def connectAndRunSever(self): # Fonction d'initialisation avec le serveur
        self.login_settings = {
            "firstName" : self.connection_widget.firstName_lne.text(),
            "port" : self.connection_widget.port_lne.text(),
            "adress" : self.connection_widget.adresse_lne.text()
            }

        #check if the user have given all the required informations
        itIsOK = True
        for i in self.login_settings:
            if self.login_settings[i]=='':
                warning = warningOBG(
                    parent=self,
                    windowTitle="Missing informations",
                    h1text="Missing informations",
                    informativeText="You must give a " + str(i),
                    pythonError="You must give a " + i
                )
                print('You must give a ' + i)
                itIsOK = False


        #if the user have given all the required informations the client starts
        if itIsOK == True:
            #close connection widget

            try:        #si la connection est impossible, on affiche un message d'erreur et on attend
                #BUILD SERVER
                #creating a connection
                self.server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_connection.connect((self.login_settings['adress'], int(self.login_settings['port'])))
                print("Connection established on the port " + self.login_settings['port'] + "\n")

                self.initEncryption()
                self.setupApplication()

                self.connection_widget.close()
                #starting server
                self.threadpool = QtCore.QThreadPool()
                # print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

                self.worker = Worker(parent = self)
                self.workerThread = QtCore.QThread()
                self.workerThread.started.connect(self.worker.run) #r Start the Run function
                self.worker.received_message.connect(self.msgRecv)  # Connect your signals/slots
                self.worker.moveToThread(self.workerThread)  # Move the Worker object to the Thread object
                self.workerThread.start()

            except Exception as e:
                print(e)
                print("Unexpected error:", sys.exc_info()[0]) # TEMPORAIRE  -- REMOVE ME

                warning = warningOBG(parent=self, windowTitle="Connection failed", h1text="Connection failed", informativeText="Maybe the server is not started", pythonError=str(e))


    def initEncryption(self):
        print("Initlialize encryption !\n")
        self.server_connection.send(self.crypting.public_key_readable) # On envoie la clé publique au serveur

        server_pass = self.crypting.asymDecrypt(self.server_connection.recv(1024)) # On récupère la clé symmétrique envoyé par le serveur
        self.crypting.saveServerPass(server_pass) # On sauvegarde la clé

        self.server_connection.send(b"done") # Envoie au serveur la confirmation de réception du message


    def setupApplication(self):
        #
        # RÉCUPÉRATION DES CHANNELS
        self.channelList = json.loads(self.crypting.sym_decrypt(self.server_connection.recv(2048)))["channelList"]
        print("\n### BEGIN - Channel list received ###")

        # maintenant qu'on a TOUTES les informations nécessaires à la création de l'interface utilisateur finale on la crée
        self.cryptenger_win = mainWidgetOBJ(
            parentObject=self,
            # app_settings=self.app_settings,
            serverName=self.login_settings['adress'],
            Username=self.login_settings['firstName'],
            channelsNames=self.channelList,
        )

        #maintenant la taille minimum de la fenetre est plus petite
        self.setMinimumWidth(self.app_settings["cryptenger_win"]["window_minimum_size"][0])
        self.setMinimumHeight(self.app_settings["cryptenger_win"]["window_minimum_size"][1])
        self.resize(
            self.app_settings["cryptenger_win"]["window_size"][0],
            self.app_settings["cryptenger_win"]["window_size"][1]
        )

        self.main_V_lyt.addWidget(self.cryptenger_win)
        self.cryptenger_win.inputUI.input_lne.returnPressed.connect(self.msgSend)

        # initialisation des notifications (on cache le label et remet le compteur à 0)
        for j in range(len(self.channelList)):
            self.cryptenger_win.changeNotif(channel=int(j), reset=True)

        self.server_connection.send(b"done")  # Envoie au serveur la confirmation de réception du message
        print("### END Channel list received ###\n")


        # RÉCUPÉRATION DE L'HISTORIQUE
        print("\n### BEGIN - Received History ###")
        encoded_history = b""
        while True: # boucle permettant de récupérer un historique trop long
            part = self.server_connection.recv(4096) # On récupère un paquet de 4096 octets
            encoded_history += part # on l'ajoute à l'historique

            if (len(part) < 4096): # Si le paquet fait moins de 4096 octets on s'arrête
                break

        history = json.loads(self.crypting.sym_decrypt(encoded_history))["history"] # On déchiffre le total et on décode le json

        # pour chaque message
        for i in range(0, len(history)):
            message = history[i]
            channel = json.loads(message)["messageType"]['channel']  # récupère le channel
            self.cryptenger_win.addMessageToAChannel(msg=message, channel=int(channel), isHistory=True) # ajout du message
        print("\n### END - Receiving History ###")


    def msgSend(self):
        #message
        message = self.cryptenger_win.inputUI.input_lne.text()

        if message != '':
            #channel
            try:                                                                #PARCE QU IL FAUT SELECTIONNER UN CHANNEK D ABORD (plutard on le setera parr default)
                channel = self.cryptenger_win.getCurrrentIndex(listWidget=self.cryptenger_win.channelsList)
            except:
                channel = 0     #si on a pas encore changé de channel en cliquant sur la listWidget
                # TODO : Changer le channel par défaut, là c'est 0 mais ça serait bien que ça soit configurable dans le config.json

            #date
            date = datetime.datetime.now()
            date = {
            "day": date.strftime("%F"),
            "hour": date.strftime("%X")
            }

            #message metadata
            messageDict = {
                "messageType":{
                    "message": message,
                    "username": self.login_settings["firstName"],
                    "channel": channel,
                    "date": date,
                }
            }

            message = json.dumps(messageDict)
            print('Le message est', message)

            #send message
            #       self.server_connection.send(self.crypting.sym_encrypt(message).encode())
            self.server_connection.send(message.encode())

            #reset input line
            self.cryptenger_win.inputUI.input_lne.setText('')   #c'est peut etre de la que vient le bug d'atom des multiples messages

            # #met notif a 0
            # self.cryptenger_win.changeNotif(channel, reset=True)

            """ADD THE TEXT TO THE UI"""
            #self.cryptenger_win.addMessageToAChannel(msg = message, channel = channel)




    def msgRecv(self, msg):
        msg = self.crypting.sym_decrypt(msg.encode())

        message_in_python = json.loads(msg)       #conversion JSON to PYTHON
        # print(message_in_python)

        try:                                                                        #récupère le channel actuel depuis le current item sélectionné de la QListWidget des channels
            current_channel = self.cryptenger_win.channelsList.currentItem().text()
            current_channel = int(current_channel)
        except:                                                                     #si on a pas encore sélectionné de channel (qu'on utilise le channel par défaut, après le lancement) on utilise le channel 0 lancé par défaut. Car la ligne du dessus a besoin qu'un item de la liste ait été sélectionné au moins une fois.
            current_channel = 0

        channel = message_in_python["messageType"]["channel"]
        username = message_in_python["messageType"]["username"]

        #on ajoute une notification seulement si le message vient d'un autre utilisateur et qu'il est affiché dans un autre channel que celui actuellement sélectionné
        addNotif = False
        if username != self.login_settings["firstName"] and not channel == current_channel:          #ET SI CURRENT CHANNEL DIFFERENT DE CHANNEL DU MESSAGE ENVOYE
            addNotif=True

        #ajout du message
        self.cryptenger_win.addMessageToAChannel(msg = msg, channel=channel, addNotif=addNotif)





"""Lancement de L'application Cryptenger"""
if __name__ == "__main__":

    app = QApplication([])
    window = MainWindow()
    app.exec_()
