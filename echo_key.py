#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===========================================================================
                     E C H O   K E Y   (Keylogger educativo)
===========================================================================

¿QUÉ HACE ESTE PROGRAMA?
-------------------------
Es una aplicación de escritorio (con ventana e interfaz gráfica) que
muestra en pantalla, en tiempo real, las teclas que se van pulsando en el
ordenador. Sirve como demostración educativa de cómo funciona un keylogger
(programa que registra pulsaciones de teclado), pero SIEMPRE pidiendo
permiso al usuario antes de empezar a grabar nada.

Incluye:
- Un aviso de consentimiento antes de empezar a capturar teclas.
- Contador de estadísticas (cuántas teclas normales, especiales,
  modificadores y combinaciones se han pulsado).
- Lista con el historial de las últimas pulsaciones, con buscador y
  filtro por categoría.
- Resumen de sesión y gráfico de barras con las teclas más usadas.
- Botones para exportar ese historial a un archivo .json o .txt.
- Avisos de seguridad/privacidad al exportar, recordando que el archivo
  se guarda en texto plano (sin cifrar) y qué precauciones tomar si se
  va a mover a un USB, a la nube, etc.
- Botón para borrar todo lo guardado en memoria.
- Parada automática si no se pulsa nada durante 30 segundos (por si el
  usuario se olvida de la app abierta), y también con la tecla ESC.

IMPORTANTE — USO RESPONSABLE
-----------------------------
Este programa captura pulsaciones de teclado A NIVEL DE TODO EL SISTEMA
OPERATIVO mientras está activo, no solo lo que se escribe dentro de esta
ventana. Es decir: si mientras el keylogger está en marcha cambias a otra
aplicación (el navegador, el gestor de contraseñas, el chat...) esas
pulsaciones TAMBIÉN se capturan, incluidas las que se escriban en campos
que en esas otras apps se ven ocultos con asteriscos. Instálalo y actívalo
únicamente en tu propio equipo, con tu propio consentimiento, y con fines
educativos o de autoanálisis (por ejemplo, medir tu velocidad de
escritura).

Usar este tipo de programas para capturar pulsaciones de OTRA PERSONA sin
su conocimiento y consentimiento explícito es ilegal en la gran mayoría de
países y constituye una violación grave de la privacidad.

COMPATIBILIDAD DE SISTEMA OPERATIVO
-------------------------------------
- La interfaz gráfica (Tkinter) y la captura de teclado (pynput) funcionan
  en Windows, macOS y Linux.
- El sonido al pulsar cada tecla usa el módulo "winsound", que SOLO existe
  en Windows. En otros sistemas operativos, la casilla de sonido aparece
  desactivada automáticamente y no da ningún error.
- En macOS y en algunas distribuciones de Linux, pynput necesita permisos
  especiales de accesibilidad/entrada para poder capturar el teclado. Si
  el programa no detecta pulsaciones, o si al iniciar la sesión aparece un
  aviso de error, revisa esos permisos primero.

GLOSARIO RÁPIDO (para quien no ha programado nunca con hilos)
---------------------------------------------------------------------------
- "Hilo" (thread): una segunda línea de ejecución que corre en paralelo al
  programa principal. Aquí hay dos hilos: el principal (que dibuja la
  ventana) y uno secundario que se dedica solo a escuchar el teclado.
  Un hilo secundario NUNCA debe tocar directamente los botones o textos
  de la ventana: si lo hace, la aplicación puede fallar de forma
  aleatoria e intermitente. Por eso todo lo que detecta el teclado se
  envía a una "cola" para que lo recoja el hilo principal.
- "Cola" (queue): una lista de tareas pendientes, tipo cola de supermercado.
  El hilo del teclado deja avisos en la cola y el hilo principal los va
  sacando uno a uno, con calma, cada 50 milisegundos.
- "Callback": una función que no llamamos nosotros directamente, sino que
  otra pieza de código (aquí, la librería pynput) llama por nosotros
  cuando ocurre algo (por ejemplo, al pulsar una tecla).
- "Widget": cualquier elemento visual de la ventana (un botón, una
  etiqueta de texto, una casilla, etc.).
- "Lock" (candado): un mecanismo para que solo un hilo a la vez pueda
  modificar un dato compartido, evitando que dos hilos escriban a la vez
  y se pisen el uno al otro (lo que se llama una "carrera de datos").
===========================================================================
"""

# ──────────────────────────────────────────────────────────────────────────────
# IMPORTACIONES
# ──────────────────────────────────────────────────────────────────────────────
import json                              # Serialización de datos para exportar JSON
import queue                             # Cola segura entre hilos
import threading                         # Listener en hilo secundario + candados de sincronización
import platform                          # (No usado actualmente) detectar sistema operativo

from datetime import datetime            # Timestamps de cada evento
from pathlib import Path                 # Manejo de rutas de ficheros
import tkinter as tk                     # GUI principal
from tkinter import ttk, messagebox, filedialog  # Widgets adicionales de Tkinter
from pynput import keyboard              # Captura de eventos de teclado
from collections import Counter          # Conteo rápido para el resumen

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES GLOBALES
# ──────────────────────────────────────────────────────────────────────────────

MAX_EVENTS = 300          # Número máximo de eventos guardados en memoria
INACTIVITY_TIMEOUT = 30   # Segundos de inactividad antes de pausar automáticamente

# Intento de importar winsound (solo disponible en Windows).
# Esto va dentro de un try/except a propósito: si no se hiciera así, el programa
# directamente no arrancaría en Linux o macOS (fallaría con "ModuleNotFoundError"
# antes incluso de abrir la ventana). Con el try/except, en esos sistemas
# simplemente se desactiva la casilla de sonido y todo lo demás sigue funcionando.
try:
    import winsound        # Pitidos de feedback en Windows
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False  # Silencio en sistemas no-Windows

# ──────────────────────────────────────────────────────────────────────────────
# PALETA DE COLORES
# ──────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#2d1a2e",   # Fondo principal: ciruela oscuro
    "surface":   "#3d2040",   # Superficies de widgets
    "accent":    "#e05aa0",   # Rosa fucsia principal
    "accent2":   "#c9417f",   # Rosa más oscuro (hover / activo)
    "text":      "#fce4f4",   # Texto claro lavanda
    "subtext":   "#c899bc",   # Texto secundario
    "entry_bg":  "#4a2550",   # Fondo de entradas de texto
    "listbg":    "#3a1d3c",   # Fondo del listbox
    "disabled":  "#7a5080",   # Color desactivado
}

# ──────────────────────────────────────────────────────────────────────────────
# MAPA COMPLETO DE TECLAS ESPECIALES → etiqueta legible
# Cada entrada: pynput Key → cadena que se mostrará en la UI
# ──────────────────────────────────────────────────────────────────────────────
SPECIAL_KEY_LABELS = {
    keyboard.Key.enter:         "[ENTER]",
    keyboard.Key.space:         "[ESPACIO]",
    keyboard.Key.tab:           "[TAB]",
    keyboard.Key.backspace:     "[RETROCESO]",
    keyboard.Key.delete:        "[SUPR]",
    keyboard.Key.esc:           "[ESC]",
    keyboard.Key.caps_lock:     "[BLOQ MAYÚS]",
    keyboard.Key.num_lock:      "[BLOQ NUM]",
    keyboard.Key.scroll_lock:   "[BLOQ DESPL]",
    keyboard.Key.insert:        "[INSERT]",
    keyboard.Key.home:          "[INICIO]",
    keyboard.Key.end:           "[FIN]",
    keyboard.Key.page_up:       "[RE PÁG]",
    keyboard.Key.page_down:     "[AV PÁG]",
    keyboard.Key.up:            "[↑]",
    keyboard.Key.down:          "[↓]",
    keyboard.Key.left:          "[←]",
    keyboard.Key.right:         "[→]",
    keyboard.Key.f1:            "[F1]",
    keyboard.Key.f2:            "[F2]",
    keyboard.Key.f3:            "[F3]",
    keyboard.Key.f4:            "[F4]",
    keyboard.Key.f5:            "[F5]",
    keyboard.Key.f6:            "[F6]",
    keyboard.Key.f7:            "[F7]",
    keyboard.Key.f8:            "[F8]",
    keyboard.Key.f9:            "[F9]",
    keyboard.Key.f10:           "[F10]",
    keyboard.Key.f11:           "[F11]",
    keyboard.Key.f12:           "[F12]",
    keyboard.Key.f13:           "[F13]",
    keyboard.Key.f14:           "[F14]",
    keyboard.Key.f15:           "[F15]",
    keyboard.Key.f16:           "[F16]",
    keyboard.Key.f17:           "[F17]",
    keyboard.Key.f18:           "[F18]",
    keyboard.Key.f19:           "[F19]",
    keyboard.Key.f20:           "[F20]",
    keyboard.Key.shift:         "[SHIFT]",
    keyboard.Key.shift_r:       "[SHIFT DER]",
    keyboard.Key.ctrl:          "[CTRL]",
    keyboard.Key.ctrl_l:        "[CTRL IZQ]",
    keyboard.Key.ctrl_r:        "[CTRL DER]",
    keyboard.Key.alt:           "[ALT]",
    keyboard.Key.alt_r:         "[ALT GR]",
    keyboard.Key.alt_gr:        "[ALT GR]",
    keyboard.Key.cmd:           "[WIN/CMD]",
    keyboard.Key.cmd_r:         "[WIN/CMD DER]",
    keyboard.Key.menu:          "[MENÚ]",
    keyboard.Key.print_screen:  "[IMPR PANT]",
    keyboard.Key.pause:         "[PAUSA]",
    keyboard.Key.media_play_pause: "[▶/⏸]",
    keyboard.Key.media_volume_up:  "[VOL+]",
    keyboard.Key.media_volume_down: "[VOL-]",
    keyboard.Key.media_volume_mute: "[MUTE]",
    keyboard.Key.media_next:    "[SIGUIENTE ▶▶]",
    keyboard.Key.media_previous: "[ANTERIOR ◀◀]",
}

# Conjunto de teclas modificadoras (no se muestran solas si van con otra tecla)
MODIFIER_KEYS = {
    keyboard.Key.shift, keyboard.Key.shift_r,
    keyboard.Key.ctrl,  keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.alt,   keyboard.Key.alt_r,  keyboard.Key.alt_gr,
    keyboard.Key.cmd,   keyboard.Key.cmd_r,
}

# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def timestamp():
    """Devuelve la hora actual con precisión de centésimas de segundo.

    Se usa para que cada evento guardado tenga un tiempo legible.
    La salida incluye fracciones (sin necesidad de almacenar microsegundos completos).
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]


def is_modifier(key):
    """Devuelve True si la tecla es un modificador (CTRL, ALT, SHIFT, WIN)."""
    # Se delega en el set MODIFIER_KEYS para que la comprobación sea rápida.
    return key in MODIFIER_KEYS


# ──────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

class EchoKey:
    """Gestiona la lógica y la interfaz gráfica del monitor de teclado educativo.

    Nota importante sobre hilos (leer antes de tocar el código):
    - El listener de teclado (pynput) corre en un hilo secundario, porque tiene
      que quedarse "escuchando" al sistema operativo todo el rato.
    - Ese hilo secundario NUNCA debe modificar directamente widgets de Tkinter
      (botones, etiquetas...) ni variables compartidas como las estadísticas.
      Si lo hiciera, la aplicación podría fallar de forma intermitente y muy
      difícil de depurar.
    - Por eso, el hilo del teclado se limita a meter mensajes en `self.queue`.
      El hilo principal (el que dibuja la ventana) va sacando esos mensajes
      cada 50 ms con `_periodic_process` y es el ÚNICO que actualiza widgets,
      estadísticas (`self.stats`) e historial (`self.events`).
    - El único dato que sí se comparte directamente entre los dos hilos es
      `self.pressed` (las teclas actualmente pulsadas, usada para detectar
      combinaciones). Para protegerlo se usa `self._pressed_lock`, un candado
      que impide que dos hilos lo modifiquen al mismo tiempo.
    """

    def __init__(self, root):
        self.root = root                          # Ventana raíz de Tkinter
        self.root.title("Echo Key — Monitor de Teclado")
        self.root.configure(bg=PALETTE["bg"])     # Aplicar fondo oscuro

        # ── Estado interno ──────────────────────────────────────────────
        self.running     = False                  # True si el listener está activo
        self.queue       = queue.Queue()          # Cola de eventos del listener → UI
        self.events      = []                     # Historial de eventos guardados (diccionarios con hora/evento/categoría)

        self.listener    = None                   # Referencia al Listener para poder parar correctamente

        self.start_time  = None                   # Momento en que se inició la sesión
        self.last_event_time = None               # Momento del último evento recibido

        # ── Teclas presionadas simultáneamente (para combos) ────────────
        # Este set lo escribe el hilo del teclado (en _on_press/_on_release) y lo
        # vacía el hilo principal (en _stop_listener), así que necesita candado.
        self.pressed = set()                      # Conjunto de teclas actualmente pulsadas
        self._pressed_lock = threading.Lock()     # Candado que protege `self.pressed`

        # ── Estadísticas por categoría ──────────────────────────────────
        # IMPORTANTE: estas estadísticas SOLO se modifican desde el hilo principal
        # (dentro de `_handle_event`), nunca desde el hilo del teclado. Así se evita
        # que, por ejemplo, se pulse "Limpiar" justo en el instante en que el
        # listener está incrementando un contador (una carrera de datos clásica).
        self.stats = {
            "total":    0,   # Total de pulsaciones
            "normal":   0,   # Letras y símbolos simples
            "especial": 0,   # Teclas especiales (F1-F20, flechas, etc.)
            "modificador": 0,# CTRL, SHIFT, ALT solos
            "combinacion": 0,# Combos tipo CTRL+C, ALT+F4...
        }

        # ── Variables de la UI ──────────────────────────────────────────
        self.sound_enabled  = tk.BooleanVar(value=False)   # Toggle de sonido
        self.show_modifiers = tk.BooleanVar(value=False)   # Mostrar modificadores solos
        self.timer_var      = tk.StringVar(value="Tiempo: 00:00  |  TPM: —")
        self.status_var     = tk.StringVar(value="⏹ Detenido")

        self._build_ui()           # Construir todos los widgets
        self._apply_theme()        # Colorear widgets nativos (Text, Listbox, etc.)
        self._periodic_process()   # Arrancar bucle de procesamiento de cola
        self._update_timer()       # Arrancar actualización del temporizador
        self._check_inactivity()   # Arrancar vigilancia de inactividad

    # ──────────────────────────────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        """Construye todos los elementos gráficos de la ventana."""

        # Configurar estilos ttk para que respeten la paleta rosa
        style = ttk.Style()
        style.theme_use("clam")   # Tema base que permite personalización de colores

        # Estilo de Frame
        style.configure("TFrame",
                         background=PALETTE["bg"])

        # Etiquetas normales
        style.configure("TLabel",
                         background=PALETTE["bg"],
                         foreground=PALETTE["text"],
                         font=("Segoe UI", 10))

        # Etiquetas de subtítulo pequeño
        style.configure("Sub.TLabel",
                         background=PALETTE["bg"],
                         foreground=PALETTE["subtext"],
                         font=("Segoe UI", 9))

        # Botones principales
        style.configure("TButton",
                         background=PALETTE["accent"],
                         foreground="white",
                         font=("Segoe UI", 10, "bold"),
                         padding=(10, 6),
                         borderwidth=0,
                         relief="flat")
        style.map("TButton",
                  background=[("active",   PALETTE["accent2"]),
                               ("disabled", PALETTE["disabled"])],
                  foreground=[("disabled", "#ffffff")])

        # Botón de peligro (Limpiar / Salir)
        style.configure("Danger.TButton",
                         background="#a03060",
                         foreground="white",
                         font=("Segoe UI", 10, "bold"),
                         padding=(10, 6))
        style.map("Danger.TButton",
                  background=[("active", "#7a1a40")])

        # Checkbutton como toggle
        style.configure("Toggle.TCheckbutton",
                         background=PALETTE["surface"],
                         foreground=PALETTE["text"],
                         font=("Segoe UI", 10),
                         padding=(8, 5))
        style.map("Toggle.TCheckbutton",
                  background=[("active", PALETTE["accent2"]),
                               ("selected", PALETTE["accent"])])

        # ── Contenedor raíz con padding ──────────────────────────────────
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        # ── Cabecera: título + estado ────────────────────────────────────
        header = ttk.Frame(frm)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="🎹  Echo Key",
                  font=("Segoe UI", 15, "bold"),
                  foreground=PALETTE["accent"]).grid(row=0, column=0, sticky="w")

        ttk.Label(header, textvariable=self.status_var,
                  style="Sub.TLabel",
                  font=("Segoe UI", 10, "italic")).grid(row=0, column=1, sticky="e")

        ttk.Label(header, textvariable=self.timer_var,
                  style="Sub.TLabel").grid(row=1, column=0, columnspan=2, sticky="e")

        # ── Panel de última tecla ────────────────────────────────────────
        key_frame = ttk.Frame(frm)
        key_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        key_frame.configure(style="TFrame")

        ttk.Label(key_frame, text="Última pulsación:",
                  style="Sub.TLabel").grid(row=0, column=0, sticky="w")

        self.last_var = tk.StringVar(value="—")     # Variable vinculada a la etiqueta grande
        ttk.Label(key_frame, textvariable=self.last_var,
                  font=("Segoe UI", 26, "bold"),
                  foreground=PALETTE["accent"]).grid(row=1, column=0, sticky="w")

        # ── Cuadro de estadísticas ───────────────────────────────────────
        ttk.Label(frm, text="Estadísticas de sesión:",
                  style="Sub.TLabel").grid(row=2, column=0, sticky="w")

        self.stats_text = tk.Text(frm, height=5, width=60,
                                   state="disabled", wrap="none",
                                   font=("Cascadia Code", 9))
        self.stats_text.grid(row=3, column=0, sticky="ew", pady=(2, 8))

        # ── Barra de búsqueda sobre el historial ────────────────────────
        search_frame = ttk.Frame(frm)
        search_frame.grid(row=4, column=0, sticky="ew", pady=(0, 2))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Historial  |  Buscar:").grid(row=0, column=0, padx=(0, 6))

        self.search_var = tk.StringVar()
        # Filtrado en tiempo real: cada cambio en el Entry dispara _filter_events
        self.search_var.trace_add("write", lambda *_: self._filter_events())
        # Entry con búsqueda: al escribir, se recalcula el filtrado del historial
        ttk.Entry(search_frame,
                  textvariable=self.search_var,
                  width=28).grid(row=0, column=1, sticky="ew")


        # Selector de categoría para filtrar
        self.filter_cat = tk.StringVar(value="Todos")
        cat_combo = ttk.Combobox(search_frame,
                                  textvariable=self.filter_cat,
                                  values=["Todos", "Normal", "Especial",
                                          "Modificador", "Combinación"],
                                  state="readonly", width=14)
        cat_combo.grid(row=0, column=2, padx=(6, 0))
        cat_combo.bind("<<ComboboxSelected>>", lambda _: self._filter_events())

        # ── Listbox de historial con scrollbar ──────────────────────────
        list_frame = ttk.Frame(frm)
        list_frame.grid(row=5, column=0, sticky="nsew", pady=(2, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        frm.rowconfigure(5, weight=1)

        self.listbox = tk.Listbox(list_frame, height=11, width=62,
                                   font=("Cascadia Code", 9),
                                   activestyle="none",
                                   selectmode="extended")   # Permite selección múltiple
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame,
                                   orient="vertical",
                                   command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)  # Vincular scroll al listbox

        # ── Fila de botones principales ──────────────────────────────────
        btn1 = ttk.Frame(frm)
        btn1.grid(row=6, column=0, sticky="ew", pady=(0, 4))
        for i in range(5):
            btn1.columnconfigure(i, weight=1)   # Distribuir espacio por igual

        self.start_btn = ttk.Button(btn1, text="▶  Iniciar sesión",
                                     command=self._toggle_listener)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=3)

        ttk.Button(btn1, text="📋  Resumen",
                   command=self._show_summary).grid(row=0, column=1, sticky="ew", padx=3)

        ttk.Button(btn1, text="📊  Gráfico top",
                   command=self._show_top_chart).grid(row=0, column=2, sticky="ew", padx=3)

        ttk.Button(btn1, text="🗑  Limpiar",
                   style="Danger.TButton",
                   command=self._clear_memory).grid(row=0, column=3, sticky="ew", padx=3)

        ttk.Button(btn1, text="❌  Salir",
                   style="Danger.TButton",
                   command=self._exit).grid(row=0, column=4, sticky="ew", padx=3)

        # ── Fila de botones secundarios ──────────────────────────────────
        btn2 = ttk.Frame(frm)
        btn2.grid(row=7, column=0, sticky="ew", pady=(0, 4))
        for i in range(4):
            btn2.columnconfigure(i, weight=1)

        ttk.Button(btn2, text="💾  Exportar JSON",
                   command=self._export_json).grid(row=0, column=0, sticky="ew", padx=3)

        ttk.Button(btn2, text="📄  Exportar TXT",
                   command=self._export_txt).grid(row=0, column=1, sticky="ew", padx=3)

        ttk.Checkbutton(btn2, text="🔊  Sonido tecla",
                        variable=self.sound_enabled,
                        style="Toggle.TCheckbutton").grid(row=0, column=2, sticky="ew", padx=3)

        ttk.Checkbutton(btn2, text="👁  Ver modificadores solos",
                        variable=self.show_modifiers,
                        style="Toggle.TCheckbutton").grid(row=0, column=3, sticky="ew", padx=3)

        # Si estamos en Linux/macOS no hay winsound, así que desactivamos la casilla
        # de sonido en vez de dejar que el usuario la marque sin que haga nada.
        if not WINSOUND_AVAILABLE:
            for child in btn2.winfo_children():
                if isinstance(child, ttk.Checkbutton) and "Sonido" in child.cget("text"):
                    child.configure(state="disabled")

        # Inicializar display de estadísticas vacío
        self._refresh_stats_display()

    def _apply_theme(self):
        """Aplica colores de la paleta rosa a widgets nativos Tk (no-ttk)."""
        self.stats_text.configure(
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["accent"],
            selectbackground=PALETTE["accent"],
            selectforeground="white",
            bd=0, relief="flat"
        )
        self.listbox.configure(
            bg=PALETTE["listbg"],
            fg=PALETTE["text"],
            selectbackground=PALETTE["accent"],
            selectforeground="white",
            bd=0, relief="flat",
            highlightthickness=0
        )

    # ──────────────────────────────────────────────────────────────────────
    # LISTENER DE TECLADO
    # ──────────────────────────────────────────────────────────────────────

    def _classify_key(self, key):
        """Clasifica una tecla y decide si es normal/especial/modificador/combinación.

        La clave de la detección de combinaciones es el set `self.pressed`, que
        refleja qué modificadores (CTRL/ALT/SHIFT/WIN) están activos en el instante
        en el que llega el evento de `on_press`.

        IMPORTANTE: este método lee `self.pressed` y se llama siempre desde dentro
        de un bloque que ya tiene el candado `self._pressed_lock` cogido (ver
        `_on_press`), así que aquí no hace falta volver a pedirlo.

        Devuelve:
          (etiqueta_legible, categoria)

        Categorías posibles:
          - 'normal'
          - 'especial'
          - 'modificador'
          - 'combinacion'
        """

        # Detectar qué modificadores están activos en este instante
        ctrl  = any(k in self.pressed for k in (keyboard.Key.ctrl,
                                                  keyboard.Key.ctrl_l,
                                                  keyboard.Key.ctrl_r))
        shift = any(k in self.pressed for k in (keyboard.Key.shift,
                                                  keyboard.Key.shift_r))
        alt   = any(k in self.pressed for k in (keyboard.Key.alt,
                                                  keyboard.Key.alt_r,
                                                  keyboard.Key.alt_gr))
        win   = any(k in self.pressed for k in (keyboard.Key.cmd,
                                                  keyboard.Key.cmd_r))

        # Construir prefijo de combinación (p.ej. "CTRL+SHIFT+")
        mods = []
        if ctrl:  mods.append("CTRL")
        if shift: mods.append("SHIFT")
        if alt:   mods.append("ALT")
        if win:   mods.append("WIN")
        prefix = "+".join(mods) + "+" if mods else ""

        # ── Caso 1: la tecla ES un modificador (CTRL, ALT, SHIFT, WIN) ──
        if is_modifier(key):
            label = SPECIAL_KEY_LABELS.get(key, f"[MOD:{key}]")
            return label, "modificador"

        # ── Caso 2: tecla especial con etiqueta conocida ─────────────────
        if key in SPECIAL_KEY_LABELS:
            label = SPECIAL_KEY_LABELS[key]
            if prefix:
                # Ejemplo: CTRL+[F4], ALT+[ENTER]
                return f"[{prefix}{label[1:-1]}]", "combinacion"
            return label, "especial"

        # ── Caso 3: tecla con carácter imprimible ────────────────────────
        try:
            char = key.char    # Puede ser None o lanzar AttributeError
            if char is not None:
                # Si hay modificadores activos → combinación
                if mods:
                    # Para CTRL, obtener la letra aunque sea un carácter de control
                    if ctrl and len(char) == 1 and ord(char) < 32:
                        # Convertir carácter de control a letra (^A=1 → A, etc.)
                        char = chr(ord('@') + ord(char))
                    return f"[{prefix}{char.upper()}]", "combinacion"
                # Sin modificadores → tecla normal
                return char, "normal"
        except AttributeError:
            pass   # key.char no existe en teclas especiales no mapeadas

        # ── Caso 4: tecla desconocida (fallback) ─────────────────────────
        # Extraer nombre legible del Key (p.ej. "Key.unknown_123" → "unknown_123")
        raw = str(key).replace("Key.", "").upper()
        label = f"[{prefix}{raw}]" if prefix else f"[{raw}]"
        return label, "especial" if not prefix else "combinacion"

    def _on_press(self, key):
        """Callback de pynput: se ejecuta en el HILO SECUNDARIO del teclado.

        Se ejecuta cada vez que el sistema operativo notifica una tecla pulsada,
        en cualquier programa que tenga el foco (no solo en Echo Key).

        Regla de oro que sigue esta función: aquí NO se toca ningún widget de
        Tkinter, ni `self.stats`, ni `self.show_modifiers`/`self.sound_enabled`
        directamente. Todo eso se decide más tarde, en el hilo principal, dentro
        de `_handle_event`. Esta función solo:
        1. Registra la tecla en `self.pressed` (protegido con candado).
        2. Clasifica la tecla (etiqueta + categoría).
        3. Deja el evento en la cola para que lo recoja el hilo principal.
        4. Si la tecla es ESC, pide (a través de la cola) que se detenga la sesión;
           NO detiene el listener directamente desde aquí.
        """

        with self._pressed_lock:
            self.pressed.add(key)                 # Registrar la tecla como presionada
            label, category = self._classify_key(key)   # Clasificarla (lee self.pressed)

        # Empaquetar el evento y dejarlo en la cola. El hilo principal decidirá
        # si hay que contarlo en las estadísticas, mostrarlo, sonar, etc.
        self.queue.put({
            "tipo":      "tecla",
            "hora":      timestamp(),
            "evento":    label,
            "categoria": category
        })

        # ESC debe detener la sesión, pero NO podemos llamar aquí a _stop_listener()
        # directamente: esa función toca botones y variables de la ventana, y esto
        # es un hilo distinto al de Tkinter. En su lugar, mandamos un mensaje de
        # "control" por la misma cola; el hilo principal lo verá y parará él mismo.
        if key == keyboard.Key.esc:
            self.queue.put({"tipo": "control", "accion": "detener"})

    def _on_release(self, key):
        """Callback de pynput: se llama cuando se suelta una tecla (hilo secundario)."""
        # Eliminar del conjunto de presionadas para tracking correcto de combos.
        # Usamos el mismo candado que en _on_press para evitar carreras de datos
        # con el momento en que el hilo principal vacía `self.pressed` al parar.
        with self._pressed_lock:
            self.pressed.discard(key)   # discard no lanza error si no existe

    def _listener_thread(self):
        """Hilo daemon que mantiene vivo el listener de pynput.

        Si el listener no puede arrancar (por ejemplo, en macOS sin permisos de
        Accesibilidad, o en Linux sin acceso al dispositivo de entrada), la
        excepción ocurre AQUÍ, dentro de este hilo. No podemos mostrar un
        mensaje de error de Tkinter directamente desde este hilo, así que lo
        enviamos por la cola para que el hilo principal se encargue de avisar
        al usuario y de dejar la interfaz en un estado coherente (botón en
        "Iniciar sesión", no en "Detener").
        """
        try:
            with keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            ) as lst:
                self.listener = lst   # Guardar referencia para poder pararlo
                lst.join()            # Bloquear este hilo hasta que se detenga
        except Exception as e:
            self.queue.put({
                "tipo": "control",
                "accion": "error_inicio",
                "mensaje": str(e),
            })

    def _start_listener(self):
        """Pide consentimiento al usuario y arranca el listener en un hilo."""
        if self.running:
            return   # Evitar doble arranque

        ok = messagebox.askokcancel(
            "Consentimiento requerido",
            "Echo Key va a capturar TODAS las teclas que pulses en el ORDENADOR "
            "ENTERO, no solo dentro de esta ventana. Si cambias a otra aplicación "
            "(el navegador, un gestor de contraseñas, etc.) mientras la sesión "
            "sigue activa, esas pulsaciones también quedarán registradas, "
            "incluidas posibles contraseñas escritas en campos que en otras "
            "aplicaciones se ven ocultos con asteriscos.\n\n"
            "⚠ Úsalo solo en tu propio equipo y con fines educativos o de "
            "autoanálisis (por ejemplo, medir tu velocidad de escritura).\n\n"
            "¿Das tu consentimiento para iniciar la captura?"
        )
        if not ok:
            return   # Usuario rechazó: no hacer nada

        self.running = True
        self.start_time = datetime.now()                  # Guardar momento de inicio
        self.start_btn.config(text="⏹  Detener sesión")  # Cambiar texto del botón
        self.status_var.set("🟢 Escuchando...")           # Actualizar barra de estado

        # Arrancar el listener en un hilo daemon (muere al cerrar la app).
        # "daemon=True" significa que este hilo no impedirá que el programa
        # se cierre aunque siga vivo cuando se cierra la ventana principal.
        t = threading.Thread(target=self._listener_thread, daemon=True)
        t.start()

    def _stop_listener(self):
        """Detiene el listener si estaba activo. Debe llamarse SIEMPRE desde
        el hilo principal (por eso ESC no la llama directamente, ver _on_press)."""
        if not self.running:
            return

        if self.listener:
            try:
                self.listener.stop()   # Señal de parada a pynput
            except Exception:
                pass
            self.listener = None

        with self._pressed_lock:
            self.pressed.clear()   # Limpiar teclas presionadas para evitar combos fantasma

        self._reset_ui_stopped()

    def _reset_ui_stopped(self):
        """Deja la interfaz (botón y barra de estado) en el estado 'detenido'.

        Se separa en su propio método porque hay dos situaciones que necesitan
        exactamente este mismo reseteo visual: una parada normal (_stop_listener)
        y un fallo al arrancar el listener (ver _handle_control).
        """
        self.running = False
        self.start_btn.config(text="▶  Iniciar sesión")  # Restaurar texto del botón
        self.status_var.set("⏹ Detenido")

    def _toggle_listener(self):
        """Alterna entre iniciar y detener el listener."""
        if self.running:
            self._stop_listener()
        else:
            self._start_listener()

    # ──────────────────────────────────────────────────────────────────────
    # PROCESAMIENTO DE COLA Y ACTUALIZACIÓN DE UI
    # ──────────────────────────────────────────────────────────────────────

    def _periodic_process(self):
        """Vacía la cola de eventos y actualiza la UI.

        Se ejecuta en el hilo principal de Tkinter y se reprograma con `after`.
        - El listener (pynput) NO actualiza la interfaz directamente.
        - Esta función consume eventos con `get_nowait()` para no bloquear.
        - Hay dos tipos de mensajes en la cola: "tecla" (una pulsación real) y
          "control" (peticiones internas, como "detener" o "hubo un error al
          arrancar"). Cada uno se procesa con su propio método.
        """

        try:
            while True:
                ev = self.queue.get_nowait()   # Obtener evento sin bloquear
                if ev.get("tipo") == "control":
                    self._handle_control(ev)
                else:
                    self._handle_event(ev)
        except queue.Empty:
            pass   # Cola vacía: no hay nada que procesar ahora
        self.root.after(50, self._periodic_process)   # Reprogramar próxima llamada

    def _handle_control(self, ev):
        """Procesa mensajes de control enviados por el hilo del teclado.

        Estos mensajes nunca representan una tecla pulsada, sino una petición
        interna que solo el hilo principal puede resolver con seguridad.
        """
        accion = ev.get("accion")

        if accion == "detener":
            # Petición de parada (normalmente porque se pulsó ESC)
            self._stop_listener()

        elif accion == "error_inicio":
            # El listener no pudo arrancar. Dejamos la interfaz coherente y
            # avisamos con el motivo técnico, además de una pista de solución
            # habitual según el sistema operativo.
            self._reset_ui_stopped()
            messagebox.showerror(
                "No se pudo iniciar la captura",
                "Echo Key no ha podido empezar a escuchar el teclado.\n\n"
                f"Detalle técnico: {ev.get('mensaje', 'desconocido')}\n\n"
                "Posibles soluciones:\n"
                "• macOS: ve a Ajustes del Sistema → Privacidad y Seguridad → "
                "Accesibilidad, y da permiso a la aplicación (o a la terminal/IDE "
                "desde la que la ejecutas).\n"
                "• Linux: puede requerir permisos sobre el dispositivo de entrada "
                "o ejecutarse en la misma sesión gráfica que el usuario activo."
            )

    def _handle_event(self, ev):
        """Procesa un evento de tecla recibido de la cola (hilo principal).

        Este es el ÚNICO lugar del programa donde se actualizan `self.stats`
        y `self.events`, precisamente para que no haya dos hilos escribiendo
        sobre los mismos datos a la vez.
        """
        categoria = ev.get("categoria", "normal")

        # Si es un modificador solo (CTRL, SHIFT...) y el usuario no quiere verlos,
        # lo ignoramos aquí. Esta comprobación se hace en el hilo principal porque
        # leer una variable de Tkinter (self.show_modifiers) desde otro hilo no es
        # seguro.
        if categoria == "modificador" and not self.show_modifiers.get():
            return

        # Actualizar contadores (a salvo de carreras de datos: solo este método
        # los toca)
        self.stats["total"] += 1
        self.stats[categoria] = self.stats.get(categoria, 0) + 1

        self.last_var.set(ev["evento"])             # Mostrar la tecla en grande
        self.last_event_time = datetime.now()        # Registrar tiempo del último evento

        # Añadir al historial en memoria (con límite MAX_EVENTS)
        self.events.append(ev)
        if len(self.events) > MAX_EVENTS:
            self.events.pop(0)   # Eliminar el evento más antiguo si se supera el límite

        # Feedback sonoro opcional (solo en Windows). Se lanza en su propio
        # hilo, corto y aislado, para no bloquear ni la ventana ni el "gancho"
        # del sistema operativo que detecta las teclas.
        if self.sound_enabled.get() and WINSOUND_AVAILABLE:
            threading.Thread(target=self._play_beep, daemon=True).start()

        # Reconstruir el listbox completo aplicando el filtro activo
        self._filter_events()
        self._refresh_stats_display()

    def _play_beep(self):
        """Reproduce un pitido corto (solo Windows) en su propio hilo desechable."""
        try:
            winsound.Beep(500, 15)   # Pitido breve a 500 Hz
        except Exception:
            pass

    def _filter_events(self):
        """Filtra el historial por texto buscado y/o categoría seleccionada."""
        term = self.search_var.get().strip().lower()   # Texto introducido en el buscador
        cat  = self.filter_cat.get()                   # Categoría del desplegable

        self.listbox.delete(0, tk.END)   # Limpiar listbox antes de repoblarlo

        for ev in reversed(self.events):   # Mostrar más recientes arriba
            evento_str = ev["evento"].lower()
            ev_cat     = ev.get("categoria", "normal")

            # Filtrar por texto
            if term and term not in evento_str:
                continue

            # Filtrar por categoría (traducción español → clave interna)
            cat_map = {
                "Normal": "normal", "Especial": "especial",
                "Modificador": "modificador", "Combinación": "combinacion"
            }
            if cat != "Todos" and ev_cat != cat_map.get(cat, ""):
                continue

            # Insertar en el listbox con etiqueta de categoría
            cat_icon = {
                "normal":       "🔤",
                "especial":     "⌨",
                "modificador":  "🔧",
                "combinacion":  "⚡",
            }.get(ev_cat, "  ")

            self.listbox.insert(tk.END, f"{cat_icon} {ev['hora']}  {ev['evento']}")

    # ──────────────────────────────────────────────────────────────────────
    # ESTADÍSTICAS Y RESUMEN
    # ──────────────────────────────────────────────────────────────────────

    def _refresh_stats_display(self):
        """Actualiza el cuadro de texto de estadísticas con los valores actuales."""
        self.stats_text.config(state="normal")    # Desbloquear para escribir
        self.stats_text.delete("1.0", "end")      # Borrar contenido previo

        total = self.stats["total"] or 1          # Evitar división por cero

        # Calcular teclas por minuto si hay sesión activa
        tpm = 0
        if self.start_time:
            mins = (datetime.now() - self.start_time).total_seconds() / 60
            tpm  = self.stats["total"] / mins if mins > 0 else 0

        # Líneas de estadísticas con porcentaje
        lines = [
            f"{'Total':<14}: {self.stats['total']:>5}   TPM: {tpm:>6.1f}",
            f"{'Normal':<14}: {self.stats['normal']:>5}   ({self.stats['normal']/total*100:.1f}%)",
            f"{'Especiales':<14}: {self.stats['especial']:>5}   ({self.stats['especial']/total*100:.1f}%)",
            f"{'Modificadores':<14}: {self.stats['modificador']:>5}   ({self.stats['modificador']/total*100:.1f}%)",
            f"{'Combinaciones':<14}: {self.stats['combinacion']:>5}   ({self.stats['combinacion']/total*100:.1f}%)",
        ]
        self.stats_text.insert("end", "\n".join(lines))
        self.stats_text.config(state="disabled")   # Volver a bloquear edición

    def _show_summary(self):
        """Muestra ventana emergente con resumen detallado de la sesión."""
        if not self.events:
            messagebox.showinfo("Resumen", "No hay datos todavía. Inicia una sesión primero.")
            return

        # Top 10 teclas más usadas
        counts = Counter(e["evento"] for e in self.events)
        top10  = "\n".join(f"  {k:<20} ×{v}" for k, v in counts.most_common(10))

        # Tiempo total de sesión
        elapsed_s = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        mins      = elapsed_s / 60
        tpm       = self.stats["total"] / mins if mins > 0 else 0

        # Distribución porcentual
        total  = self.stats["total"] or 1
        dist   = "\n".join(
            f"  {k.capitalize():<15}: {v:>4}  ({v/total*100:.1f}%)"
            for k, v in self.stats.items() if k != "total"
        )

        # Combinar todo el resumen
        texto = (
            f"━━━━  RESUMEN DE SESIÓN  ━━━━\n\n"
            f"Duración : {int(elapsed_s//60):02d}:{int(elapsed_s%60):02d}\n"
            f"Total    : {self.stats['total']} pulsaciones\n"
            f"TPM      : {tpm:.1f} teclas/minuto\n\n"
            f"── Top 10 teclas ─────────────\n{top10}\n\n"
            f"── Distribución ──────────────\n{dist}"
        )
        messagebox.showinfo("Resumen de sesión", texto)

    def _show_top_chart(self):
        """Abre una ventana emergente con un gráfico de barras de las top 10 teclas."""
        if not self.events:
            messagebox.showinfo("Gráfico", "No hay datos todavía.")
            return

        counts = Counter(e["evento"] for e in self.events)
        top10  = counts.most_common(10)
        maxval = top10[0][1] if top10 else 1   # Máximo para normalizar barras

        # Construir ventana emergente personalizada
        win = tk.Toplevel(self.root)
        win.title("Top 10 Teclas")
        win.configure(bg=PALETTE["bg"])
        win.resizable(False, False)

        ttk.Label(win, text="📊  Top 10 teclas más pulsadas",
                  font=("Segoe UI", 12, "bold"),
                  foreground=PALETTE["accent"]).pack(padx=20, pady=(14, 6))

        # Canvas donde dibujar las barras
        CANVAS_W, CANVAS_H = 480, 300
        canvas = tk.Canvas(win,
                            width=CANVAS_W, height=CANVAS_H,
                            bg=PALETTE["surface"], bd=0, highlightthickness=0)
        canvas.pack(padx=20, pady=(0, 16))

        bar_h  = 22        # Altura de cada barra en píxeles
        gap    = 8         # Separación entre barras
        left   = 120       # Margen izquierdo para las etiquetas
        right  = CANVAS_W - 60   # Margen derecho (reserva para cifra)
        bar_area = right - left  # Ancho disponible para las barras

        for i, (key_label, count) in enumerate(top10):
            y_top = i * (bar_h + gap) + 10     # Posición Y superior de la barra
            y_bot = y_top + bar_h               # Posición Y inferior
            bar_w = int((count / maxval) * bar_area)   # Ancho proporcional

            # Gradiente simulado: barra principal y sombra
            canvas.create_rectangle(left, y_top, left + bar_w, y_bot,
                                     fill=PALETTE["accent"], outline="")
            canvas.create_rectangle(left, y_bot - 3, left + bar_w, y_bot,
                                     fill=PALETTE["accent2"], outline="")

            # Etiqueta de la tecla a la izquierda
            canvas.create_text(left - 6, (y_top + y_bot) // 2,
                                anchor="e",
                                text=key_label[:16],   # Truncar si es muy larga
                                fill=PALETTE["text"],
                                font=("Cascadia Code", 9))

            # Cifra a la derecha de la barra
            canvas.create_text(left + bar_w + 6, (y_top + y_bot) // 2,
                                anchor="w",
                                text=str(count),
                                fill=PALETTE["subtext"],
                                font=("Segoe UI", 9))

        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0, 12))

    # ──────────────────────────────────────────────────────────────────────
    # TEMPORIZADOR E INACTIVIDAD
    # ──────────────────────────────────────────────────────────────────────

    def _update_timer(self):
        """Actualiza el temporizador de sesión en la cabecera cada segundo."""
        if self.running and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            mins_i, secs_i = divmod(int(elapsed), 60)
            mins_f = elapsed / 60
            tpm = self.stats["total"] / mins_f if mins_f > 0 else 0
            self.timer_var.set(f"Tiempo: {mins_i:02d}:{secs_i:02d}  |  TPM: {tpm:.1f}")
        self.root.after(1000, self._update_timer)   # Reprogramar en 1 s

    def _check_inactivity(self):
        """
        Comprueba si han pasado INACTIVITY_TIMEOUT segundos sin pulsaciones.
        Si es así, pausa el listener automáticamente y avisa al usuario.
        Este método corre siempre en el hilo principal (se reprograma con
        `root.after`), así que puede llamar a `_stop_listener` sin problema.
        """
        if self.running and self.last_event_time:
            idle = (datetime.now() - self.last_event_time).total_seconds()
            if idle > INACTIVITY_TIMEOUT:
                self._stop_listener()
                self.status_var.set("💤 Pausado por inactividad")
                messagebox.showinfo(
                    "Pausa automática",
                    f"El listener se ha detenido tras {INACTIVITY_TIMEOUT}s sin actividad."
                )
        self.root.after(5000, self._check_inactivity)   # Comprobar cada 5 s

    # ──────────────────────────────────────────────────────────────────────
    # EXPORTACIÓN
    # ──────────────────────────────────────────────────────────────────────

    def _security_reminder(self, path):
        """Muestra un aviso (tipo pop-up) recordando cómo tratar el archivo exportado.

        Se llama justo después de guardar con éxito un JSON o un TXT. El archivo
        se guarda siempre en texto plano, así que puede contener contraseñas u
        otra información sensible si se escribió algo así durante la sesión.
        """
        messagebox.showwarning(
            "Recordatorio de seguridad",
            "El archivo se ha guardado correctamente, pero SIN cifrar (texto plano).\n\n"
            "Antes de moverlo a un USB, subirlo a la nube o enviarlo por correo:\n"
            "  1) Compŕímelo en un .zip con contraseña, o cífralo con 7-Zip "
            "(AES-256) o VeraCrypt.\n"
            "  2) No lo dejes en una carpeta que se sincronice sola con la nube "
            "(Google Drive, OneDrive, iCloud...) sin cifrarlo antes.\n"
            "  3) Bórralo de forma segura en cuanto ya no lo necesites.\n\n"
            f"Archivo guardado en:\n{path}"
        )

    def _export_json(self):
        """Exporta estadísticas e historial a un fichero JSON con confirmación.

        Genera un objeto con:
        - metadatos de exportación
        - duración de la sesión
        - estadísticas acumuladas
        - historial completo (lista de eventos)
        """

        if not messagebox.askyesno("Exportar JSON",
                                    "¿Guardar estadísticas y pulsaciones en un archivo JSON?\n\n"
                                    "Recuerda: el archivo se guardará sin cifrar."):
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Guardar como JSON"
        )
        if not path:
            return   # Usuario canceló el diálogo

        payload = {
            "exportado_en":      datetime.now().isoformat(timespec="seconds"),
            "duracion_sesion_s": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time else 0
            ),
            "estadisticas":      self.stats,
            "historial":         list(self.events),   # Copia de la lista de eventos
        }
        try:
            Path(path).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self._security_reminder(path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    def _export_txt(self):
        """Exporta estadísticas e historial a un fichero TXT con confirmación.

        El formato es pensado para lectura humana:
        - cabecera
        - estadísticas por categoría
        - historial evento por evento
        """

        if not messagebox.askyesno("Exportar TXT",
                                    "¿Guardar estadísticas y pulsaciones en un archivo TXT?\n\n"
                                    "Recuerda: el archivo se guardará sin cifrar."):
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto plano", "*.txt")],
            title="Guardar como TXT"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Echo Key — Exportación de sesión\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

                f.write("ESTADÍSTICAS:\n")
                for k, v in self.stats.items():
                    f.write(f"  {k.capitalize():<16}: {v}\n")

                f.write("\n" + "=" * 50 + "\n")
                f.write("HISTORIAL DE PULSACIONES:\n\n")
                for ev in self.events:
                    # Formato: [hora] [categoría] evento
                    cat = ev.get("categoria", "?")[0].upper()   # Primera letra de la categoría
                    f.write(f"[{ev['hora']}] [{cat}] {ev['evento']}\n")

            self._security_reminder(path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    # ──────────────────────────────────────────────────────────────────────
    # UTILIDADES DE UI
    # ──────────────────────────────────────────────────────────────────────

    def _clear_memory(self):
        """Borra el historial en memoria y reinicia los contadores con confirmación."""
        if not messagebox.askokcancel("Limpiar memoria",
                                       "¿Borrar todo el historial y reiniciar contadores?"):
            return

        self.events.clear()                       # Vaciar lista de eventos
        for k in self.stats:
            self.stats[k] = 0                     # Resetear todos los contadores

        self.last_var.set("—")                    # Limpiar indicador de última tecla
        self.listbox.delete(0, tk.END)            # Limpiar listbox
        self._refresh_stats_display()             # Actualizar panel de estadísticas

    def _exit(self):
        """Solicita confirmación y cierra la aplicación limpiamente."""
        if messagebox.askyesno("Salir", "¿Seguro que quieres salir?"):
            self._stop_listener()     # Detener listener si estaba activo
            self.root.quit()          # Terminar el bucle de Tkinter


# ──────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = EchoKey(root)
    root.geometry("720x620")     # Tamaño inicial de la ventana
    root.minsize(640, 560)        # Tamaño mínimo para evitar colapso de widgets
    root.mainloop()               # Iniciar bucle principal de eventos Tkinter