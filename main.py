import json
import os
import random
import threading
import time

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

# Import SDK Google GenAI
try:
  from google import genai
except ImportError:
  genai = None

# Imports Android NEOF (Pyjnius & Android Utils)
try:
  from android.broadcast import BroadcastReceiver
  from android.permissions import Permission, request_permissions
  from jnius import autoclass

  ON_ANDROID = True
except ImportError:
  ON_ANDROID = False

try:
  from plyer import sms
except ImportError:
  sms = None


# --- CONFIGURATION ET SAUVEGARDE LOCALE ---
CONFIG_FILE = 'vic_config.json'
MOT_DE_PASSE_SECRET = 'All2004?'

cerveau_par_defaut = {
    'salut_simple': {
        'mots_cles': ['salut', 'slt'],
        'reponses': [
            'Salut ! Ça va ?',
            'Salut salut, la forme ?',
            'Salut ! Tu as bien dormi ?',
        ],
    },
    'bonjour_simple': {
        'mots_cles': ['bonjour', 'bjr'],
        'reponses': [
            'Bonjour ! Comment vas-tu ce matin ?',
            'Bonjour ! Tu as passé une bonne nuit ?',
        ],
    },
    'ca_va_direct': {
        'mots_cles': ['ca va', 'ça va', 'cv'],
        'reponses': ['Oui ça va super bien et toi ?', 'Tranquille et toi ?'],
    },
}

dictionnaire_sms = {
    'cv': 'ca va',
    'slt': 'salut',
    'nn': 'non',
    'prq': 'pourquoi',
    'dsl': 'desole',
    'pk': 'pourquoi',
    'tkt': "t'inquiete",
    'bjr': 'bonjour',
    'mrc': 'merci',
}


def charger_config():
  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
    except Exception as e:
      print(f'Erreur lecture config: {e}')
  return {'gemini_key': '', 'cerveau': cerveau_par_defaut}


def sauvegarder_config(gemini_key, cerveau_dict):
  config_data = {'gemini_key': gemini_key, 'cerveau': cerveau_dict}
  with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump(config_data, f, ensure_ascii=False, indent=4)


# --- FONCTIONS DE TRAITEMENT ---


def nettoyer_message(msg):
  return msg.lower().strip() if msg else ''


def traduire_sms(msg):
  mots = msg.split()
  return ' '.join([dictionnaire_sms.get(m, m) for m in mots])


def analyser_message_local(message, cerveau):
  scores = {}
  mots_message = set(message.split())
  for cat, contenu in cerveau.items():
    score = sum(
        1
        for kw in contenu.get('mots_cles', [])
        if (kw in message if ' ' in kw else kw in mots_message)
    )
    if score > 0:
      scores[cat] = score
  return max(scores, key=scores.get) if scores else None


def interroger_gemini(message, api_key):
  """Appel sécurisé à l'API Google Gemini avec gestion d'erreurs complète."""
  if not genai:
    print('[Gemini Error] Bibliothèque google-genai non installée.')
    return 'Désolé, le service Gemini est indisponible.'

  if not api_key or len(api_key.strip()) < 10:
    print('[Gemini Error] Clé API invalide ou absente.')
    return 'Clé API Gemini non configurée.'

  try:
    client = genai.Client(api_key=api_key.strip())
    prompt = (
        'Tu es un assistant virtuel amical répondant par SMS. '
        'Sois très concis, naturel et réponds en une ou deux phrases maximum en'
        f" français. Voici le SMS reçu : '{message}'"
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash', contents=prompt
    )

    if response and response.text:
      return response.text.strip()
    return "J'ai bien reçu ton message !"

  except Exception as e:
    print(f'[Gemini Error] Échec de la requête : {e}')
    return "Désolé, je rencontre un problème de connexion pour répondre."


def generer_reponse(texte_recu, config):
  msg_traduit = traduire_sms(nettoyer_message(texte_recu))
  cerveau = config.get('cerveau', {})
  cat = analyser_message_local(msg_traduit, cerveau)

  if cat:
    print(f'[Bot] Catégorie trouvée : {cat}')
    return random.choice(cerveau[cat]['reponses'])
  else:
    print('[Bot] Aucune correspondance locale -> Passage à Gemini')
    return interroger_gemini(texte_recu, config.get('gemini_key', ''))


# --- ÉCRANS DE L'INTERFACE ---


class SplashScreen(Screen):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    layout = FloatLayout()

    with layout.canvas.before:
      from kivy.graphics import Color, Rectangle

      Color(0, 0, 0, 1)
      self.rect = Rectangle(size=Window.size, pos=layout.pos)

    self.logo = Label(
        text='[b]VIC SMS[/b]',
        markup=True,
        font_size='36sp',
        color=(1, 1, 1, 1),
        pos_hint={'center_x': 0.5, 'center_y': 0.6},
    )

    self.lbl_bienvenue = Label(
        text='Bienvenue',
        font_size='20sp',
        color=(0.8, 0.8, 0.8, 1),
        pos_hint={'center_x': 0.5, 'center_y': 0.15},
    )

    self.progress = ProgressBar(
        max=100,
        value=0,
        size_hint=(0.8, None),
        height=20,
        pos_hint={'center_x': 0.5, 'center_y': 0.2},
        opacity=0,
    )

    self.lbl_pourcent = Label(
        text='0%',
        font_size='16sp',
        color=(0, 1, 0, 1),
        pos_hint={'center_x': 0.5, 'center_y': 0.25},
        opacity=0,
    )

    layout.add_widget(self.logo)
    layout.add_widget(self.lbl_bienvenue)
    layout.add_widget(self.progress)
    layout.add_widget(self.lbl_pourcent)
    self.add_widget(layout)

  def on_enter(self):
    Clock.schedule_once(self.demarrer_progression, 3)

  def demarrer_progression(self, dt):
    Animation(opacity=0, d=0.5).start(self.lbl_bienvenue)
    Animation(opacity=1, d=0.5).start(self.progress)
    Animation(opacity=1, d=0.5).start(self.lbl_pourcent)

    self.valeur = 0
    Clock.schedule_interval(self.update_progress, 0.07)

  def update_progress(self, dt):
    self.valeur += 1
    self.progress.value = self.valeur
    self.lbl_pourcent.text = f'{self.valeur}%'

    if self.valeur >= 100:
      Clock.unschedule(self.update_progress)
      self.manager.current = 'accueil'


class AccueilScreen(Screen):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    layout = FloatLayout()

    if os.path.exists('elma.png'):
      bg = Image(
          source='elma.png',
          allow_stretch=True,
          keep_ratio=False,
          size_hint=(1, 1),
      )
      layout.add_widget(bg)

    btn_cle = Button(
        text='Clé 🔑',
        size_hint=(None, None),
        size=(100, 50),
        pos_hint={'top': 0.98, 'right': 0.98},
        background_color=(0.2, 0.6, 1, 1),
    )
    btn_cle.bind(on_press=self.ouvrir_cle)

    self.status_label = Label(
        text='[color=ff0000]VIC EST EN PAUSE ⏸️[/color]',
        markup=True,
        font_size='22sp',
        pos_hint={'center_x': 0.5, 'center_y': 0.55},
    )

    self.btn_controle = ToggleButton(
        text='ACTIVER LE BOT ⏯️',
        font_size='18sp',
        size_hint=(None, None),
        size=(280, 90),
        pos_hint={'center_x': 0.5, 'center_y': 0.4},
        background_color=(0, 0.8, 0, 1),
    )
    self.btn_controle.bind(on_press=self.clic_bouton)

    layout.add_widget(btn_cle)
    layout.add_widget(self.status_label)
    layout.add_widget(self.btn_controle)
    self.add_widget(layout)

    self.bot_actif = False

  def ouvrir_cle(self, instance):
    self.manager.current = 'cle_config'

  def clic_bouton(self, instance):
    app = App.get_running_app()

    if not app.est_deverrouille:
      self.status_label.text = (
          '[color=ff0000]ERREUR : Clé Vic non validée ![/color]'
      )
      instance.state = 'normal'
      return

    if instance.state == 'down':
      instance.text = 'STOPPER LE BOT ⏸️'
      instance.background_color = (1, 0, 0, 1)
      self.status_label.text = '[color=00ff00]VIC EST EN SERVICE ⏯️[/color]'
      self.bot_actif = True
      app.demarrer_ecoute_sms()
    else:
      instance.text = 'ACTIVER LE BOT ⏯️'
      instance.background_color = (0, 0.8, 0, 1)
      self.status_label.text = '[color=ff0000]VIC EST EN PAUSE ⏸️[/color]'
      self.bot_actif = False
      app.arreter_ecoute_sms()


class CleConfigScreen(Screen):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    main_layout = FloatLayout()

    btn_retour = Button(
        text='⬅️',
        size_hint=(None, None),
        size=(60, 50),
        pos_hint={'top': 0.98, 'x': 0.02},
        background_color=(0.8, 0.2, 0.2, 1),
    )
    btn_retour.bind(on_press=self.sauvegarder_et_retour)

    titre = Label(
        text='[b]Configuration Clé Vic[/b]',
        markup=True,
        font_size='22sp',
        pos_hint={'center_x': 0.5, 'top': 0.97},
        size_hint=(None, None),
        size=(200, 50),
    )

    scroll = ScrollView(
        size_hint=(0.95, 0.82), pos_hint={'center_x': 0.5, 'y': 0.05}
    )
    form_layout = BoxLayout(
        orientation='vertical', spacing=15, size_hint_y=None
    )
    form_layout.bind(minimum_height=form_layout.setter('height'))

    form_layout.add_widget(
        Label(
            text='Clé Vic (Mot de passe) :',
            size_hint_y=None,
            height=30,
            halign='left',
        )
    )
    self.input_cle_vic = TextInput(
        password=True,
        multiline=False,
        hint_text='Entrez votre clé...',
        size_hint_y=None,
        height=45,
    )
    form_layout.add_widget(self.input_cle_vic)

    form_layout.add_widget(
        Label(
            text='Cerveau Vic (JSON) :',
            size_hint_y=None,
            height=30,
            halign='left',
        )
    )
    self.input_cerveau = TextInput(
        multiline=True, size_hint_y=None, height=250
    )
    form_layout.add_widget(self.input_cerveau)

    form_layout.add_widget(
        Label(
            text='Clé API Google Gemini :',
            size_hint_y=None,
            height=30,
            halign='left',
        )
    )
    self.input_gemini = TextInput(
        multiline=True, size_hint_y=None, height=90
    )
    form_layout.add_widget(self.input_gemini)

    scroll.add_widget(form_layout)
    main_layout.add_widget(btn_retour)
    main_layout.add_widget(titre)
    main_layout.add_widget(scroll)
    self.add_widget(main_layout)

  def on_pre_enter(self):
    app = App.get_running_app()
    self.input_cle_vic.text = ''
    self.input_gemini.text = app.config_data.get('gemini_key', '')
    self.input_cerveau.text = json.dumps(
        app.config_data.get('cerveau', {}), ensure_ascii=False, indent=2
    )

  def sauvegarder_et_retour(self, instance):
    app = App.get_running_app()

    code_saisi = self.input_cle_vic.text.strip()
    app.est_deverrouille = code_saisi == MOT_DE_PASSE_SECRET

    try:
      nouveau_cerveau = json.loads(self.input_cerveau.text)
    except Exception:
      nouveau_cerveau = app.config_data.get('cerveau', {})

    gemini_key = self.input_gemini.text.strip()

    app.config_data['gemini_key'] = gemini_key
    app.config_data['cerveau'] = nouveau_cerveau
    sauvegarder_config(gemini_key, nouveau_cerveau)

    self.input_cle_vic.text = ''
    self.manager.current = 'accueil'


# --- APPLICATION PRINCIPALE & RECEPTEUR SMS ---


class VicBotApp(App):

  def build(self):
    self.config_data = charger_config()
    self.est_deverrouille = False
    self.receiver = None

    # Demande des permissions au démarrage sur Android
    if ON_ANDROID:
      request_permissions([
          Permission.RECEIVE_SMS,
          Permission.READ_SMS,
          Permission.SEND_SMS,
      ])

    sm = ScreenManager()
    sm.add_widget(SplashScreen(name='splash'))
    sm.add_widget(AccueilScreen(name='accueil'))
    sm.add_widget(CleConfigScreen(name='cle_config'))

    return sm

  def demarrer_ecoute_sms(self):
    """Initialise le BroadcastReceiver Android pour écouter les SMS entrants."""
    if ON_ANDROID and not self.receiver:
      try:
        self.receiver = BroadcastReceiver(
            self.on_sms_broadcast, actions=['android.provider.Telephony.SMS_RECEIVED']
        )
        self.receiver.start()
        print('[BroadcastReceiver] Écoute des SMS activée.')
      except Exception as e:
        print(f'[BroadcastReceiver Error] {e}')

  def arreter_ecoute_sms(self):
    """Arrête le BroadcastReceiver."""
    if self.receiver:
      self.receiver.stop()
      self.receiver = None
      print('[BroadcastReceiver] Écoute des SMS désactivée.')

  def on_sms_broadcast(self, context, intent):
    """Sert de passerelle entre le signal natif Android et Python."""
    try:
      SmsMessage = autoclass('android.telephony.SmsMessage')
      bundle = intent.getExtras()
      if bundle:
        pdus = bundle.get('pdus')
        if pdus:
          for pdu in pdus:
            msg_obj = SmsMessage.createFromPdu(pdu)
            numero = msg_obj.getOriginatingAddress()
            message = msg_obj.getMessageBody()
            if numero and message:
              self.traiter_sms_entrant(numero, message)
    except Exception as e:
      print(f'[SMS Parse Error] {e}')

  def traiter_sms_entrant(self, numero, message):
    """Exécute la réponse automatique avec un délai de 10 secondes."""
    accueil = self.root.get_screen('accueil')
    if accueil.bot_actif:

      def repondre_differe():
        print(f'[SMS Recu] De: {numero} | Msg: {message}')
        time.sleep(10)  # Délai de 10 secondes
        reponse = generer_reponse(message, self.config_data)

        if sms:
          try:
            sms.send(recipient=numero, message=reponse)
            print(f'[SMS Envoye] A: {numero} | Reponse: {reponse}')
          except Exception as e:
            print(f'[SMS Send Error] {e}')

      threading.Thread(target=repondre_differe, daemon=True).start()


if __name__ == '__main__':
  VicBotApp().run()
