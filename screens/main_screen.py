from kivy.uix.screenmanager import Screen
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivy.uix.widget import Widget


def _gas_display(o2, he):
    """Retorna nome legível do gás: Ar, O₂ Puro, EANxx ou Trimix xx/yy."""
    if o2 == 21 and he == 0:
        return "Ar"
    if o2 == 100 and he == 0:
        return "O₂ Puro"
    if he == 0:
        return f"EAN{o2}"
    return f"Trimix {o2}/{he}"


class DiveLevelCard(MDCard):
    """Card para configurar um nível de mergulho (profundidade + tempo + gás)."""

    def __init__(self, index: int, is_first=False, on_remove=None,
                 default_depth=30, default_time=20, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(4)
        self.adaptive_height = True
        self.elevation = 1
        self.radius = [dp(8)]
        self._on_remove = on_remove
        self._building = True

        # Cabeçalho
        header = MDBoxLayout(adaptive_height=True, spacing=dp(4))
        header.add_widget(MDLabel(
            text=f"Nível {index}",
            font_style="Caption",
            bold=True,
            theme_text_color="Primary",
            adaptive_height=True,
        ))
        header.add_widget(Widget())
        if not is_first:
            btn_rm = MDIconButton(
                icon="close-circle",
                size_hint_x=None,
                width=dp(36),
                on_release=self._remove,
                theme_text_color="Error",
            )
            header.add_widget(btn_rm)
        self.add_widget(header)

        # Profundidade e Tempo
        dt_row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.field_depth = MDTextField(
            hint_text="Profundidade (m)",
            text=str(default_depth),
            input_filter="float",
            mode="rectangle",
            size_hint_x=0.5,
        )
        self.field_time = MDTextField(
            hint_text="Tempo (min)",
            text=str(default_time),
            input_filter="float",
            mode="rectangle",
            size_hint_x=0.5,
        )
        dt_row.add_widget(self.field_depth)
        dt_row.add_widget(self.field_time)
        self.add_widget(dt_row)

        # Slider O₂
        o2_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.lbl_o2 = MDLabel(text="O₂: 21%", size_hint_x=0.3, adaptive_height=True)
        self.sl_o2 = MDSlider(min=1, max=100, value=21, size_hint_x=0.7)
        self.sl_o2.bind(value=self._update)
        o2_row.add_widget(self.lbl_o2)
        o2_row.add_widget(self.sl_o2)
        self.add_widget(o2_row)

        # Slider He
        he_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.lbl_he = MDLabel(text="He:  0%", size_hint_x=0.3, adaptive_height=True)
        self.sl_he = MDSlider(min=0, max=99, value=0, size_hint_x=0.7)
        self.sl_he.bind(value=self._update)
        he_row.add_widget(self.lbl_he)
        he_row.add_widget(self.sl_he)
        self.add_widget(he_row)

        # Resumo: N₂ + nome do gás + MOD
        self.lbl_info = MDLabel(
            text="N₂: 79%  |  Ar  |  MOD: 56m (PO₂ 1.4)",
            font_style="Caption",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        self.add_widget(self.lbl_info)

        self._building = False
        self._update()

    def _update(self, *args):
        if self._building:
            return
        o2 = int(self.sl_o2.value)
        he = int(self.sl_he.value)
        if o2 + he > 100:
            he = 100 - o2
            self._building = True
            self.sl_he.value = he
            self._building = False
        n2 = 100 - o2 - he
        gas_name = _gas_display(o2, he)
        mod14 = (1.4 / (o2 / 100.0) - 1) * 10 if o2 > 0 else 999.0
        self.lbl_o2.text = f"O₂: {o2}%"
        self.lbl_he.text = f"He:  {he}%"
        self.lbl_info.text = f"N₂: {n2}%  |  {gas_name}  |  MOD: {mod14:.0f}m (PO₂ 1.4)"

    def get_data(self):
        from buhlmann import GasMix
        try:
            depth = float(self.field_depth.text or '30')
            time_val = float(self.field_time.text or '20')
        except ValueError:
            depth, time_val = 30.0, 20.0
        o2 = int(self.sl_o2.value) / 100.0
        he = int(self.sl_he.value) / 100.0
        n2 = round(1.0 - o2 - he, 3)
        return {'depth': depth, 'time': time_val, 'gas': GasMix(o2, n2, he)}

    def _remove(self, *args):
        if self._on_remove:
            self._on_remove(self)


class DecoGasCard(MDCard):
    """Card para configurar um gás de descompressão individual."""

    def __init__(self, index: int, on_remove=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(4)
        self.adaptive_height = True
        self.elevation = 1
        self.radius = [dp(8)]
        self._on_remove = on_remove
        self._building = True

        # Cabeçalho
        header = MDBoxLayout(adaptive_height=True, spacing=dp(4))
        header.add_widget(MDLabel(
            text=f"Gás Deco {index}",
            font_style="Caption",
            bold=True,
            theme_text_color="Primary",
            adaptive_height=True,
        ))
        btn_rm = MDIconButton(
            icon="close-circle",
            size_hint_x=None,
            width=dp(36),
            on_release=self._remove,
            theme_text_color="Error",
        )
        header.add_widget(btn_rm)
        self.add_widget(header)

        # Slider O₂
        o2_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.lbl_o2 = MDLabel(text="O₂: 50%", size_hint_x=0.3, adaptive_height=True)
        self.sl_o2 = MDSlider(min=1, max=100, value=50, size_hint_x=0.7)
        self.sl_o2.bind(value=self._update)
        o2_row.add_widget(self.lbl_o2)
        o2_row.add_widget(self.sl_o2)
        self.add_widget(o2_row)

        # Slider He
        he_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.lbl_he = MDLabel(text="He:  0%", size_hint_x=0.3, adaptive_height=True)
        self.sl_he = MDSlider(min=0, max=99, value=0, size_hint_x=0.7)
        self.sl_he.bind(value=self._update)
        he_row.add_widget(self.lbl_he)
        he_row.add_widget(self.sl_he)
        self.add_widget(he_row)

        # Resumo N₂ + MOD
        self.lbl_info = MDLabel(
            text="N₂: 50%  |  EAN50  |  MOD: 22m (PO₂ 1.6)",
            font_style="Caption",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        self.add_widget(self.lbl_info)

        self._building = False
        self._update()

    def _update(self, *args):
        if self._building:
            return
        o2 = int(self.sl_o2.value)
        he = int(self.sl_he.value)
        if o2 + he > 100:
            he = 100 - o2
            self._building = True
            self.sl_he.value = he
            self._building = False
        n2 = 100 - o2 - he
        gas_name = _gas_display(o2, he)
        mod_val = (1.6 / (o2 / 100.0) - 1) * 10 if o2 > 0 else 999.0
        self.lbl_o2.text = f"O₂: {o2}%"
        self.lbl_he.text = f"He:  {he}%"
        self.lbl_info.text = f"N₂: {n2}%  |  {gas_name}  |  MOD: {mod_val:.0f}m (PO₂ 1.6)"

    def get_gas(self):
        from buhlmann import GasMix
        o2 = int(self.sl_o2.value) / 100.0
        he = int(self.sl_he.value) / 100.0
        n2 = round(1.0 - o2 - he, 3)
        return GasMix(o2, n2, he)

    def get_switch_depth(self) -> float:
        o2 = int(self.sl_o2.value) / 100.0
        return (1.6 / o2 - 1.0) * 10.0 if o2 > 0 else 0.0

    def _remove(self, *args):
        if self._on_remove:
            self._on_remove(self)


class MainScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._level_cards = []
        self._level_counter = 0
        self._deco_gas_cards = []
        self._deco_gas_counter = 0
        self._build_ui()

    def _build_ui(self):
        scroll = MDScrollView()
        layout = MDBoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(12),
            adaptive_height=True,
        )

        # Título
        layout.add_widget(MDLabel(
            text="Calculador de Mergulho",
            font_style="H5",
            halign="center",
            adaptive_height=True,
            padding=(0, dp(8)),
        ))
        layout.add_widget(MDLabel(
            text="Bühlmann ZH-L16C",
            font_style="Caption",
            halign="center",
            theme_text_color="Secondary",
            adaptive_height=True,
        ))

        # --- Parâmetros gerais ---
        layout.add_widget(self._section_label("PARÂMETROS DO MERGULHO"))

        self.field_surface = MDTextField(
            hint_text="Intervalo de superfície (min) — 0 para 1º mergulho",
            text="0",
            input_filter="float",
            mode="rectangle",
        )
        self.field_sac = MDTextField(
            hint_text="SAC (consumo superficial em L/min)",
            text="20",
            input_filter="float",
            mode="rectangle",
        )
        layout.add_widget(self.field_surface)
        layout.add_widget(self.field_sac)

        # --- Níveis do mergulho ---
        layout.add_widget(self._section_label("NÍVEIS DO MERGULHO"))

        self.level_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
        )
        layout.add_widget(self.level_layout)

        btn_add_level = MDFlatButton(
            text="+ ADICIONAR NÍVEL",
            on_release=self._add_level,
        )
        layout.add_widget(btn_add_level)

        # Adiciona nível 1 (não removível)
        self._add_level(is_first=True)

        # --- Gases de Descompressão ---
        layout.add_widget(self._section_label("GASES DE DESCOMPRESSÃO"))

        self.deco_gas_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
        )
        layout.add_widget(self.deco_gas_layout)

        btn_add_deco = MDFlatButton(
            text="+ ADICIONAR GÁS DE DECO",
            on_release=self._add_deco_gas,
        )
        layout.add_widget(btn_add_deco)

        # --- Gradient Factors ---
        layout.add_widget(self._section_label("GRADIENT FACTORS (conservadorismo)"))

        preset_row = MDBoxLayout(adaptive_height=True, spacing=dp(4))
        for label, lo, hi in [("Conservador\n30/85", 30, 85),
                               ("Moderado\n50/85",   50, 85),
                               ("Liberal\n85/85",    85, 85)]:
            preset_row.add_widget(MDFlatButton(
                text=label,
                on_release=lambda x, l=lo, h=hi: self._set_gf(l, h),
            ))
        layout.add_widget(preset_row)

        gf_row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.field_gf_lo = MDTextField(hint_text="GF Lo (%)", text="85",
                                       input_filter="int", mode="rectangle", size_hint_x=0.5)
        self.field_gf_hi = MDTextField(hint_text="GF Hi (%)", text="85",
                                       input_filter="int", mode="rectangle", size_hint_x=0.5)
        gf_row.add_widget(self.field_gf_lo)
        gf_row.add_widget(self.field_gf_hi)
        layout.add_widget(gf_row)

        # --- Botão Calcular ---
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))
        layout.add_widget(MDRaisedButton(
            text="CALCULAR",
            size_hint_x=1,
            on_release=self._on_calculate,
            md_bg_color=(0.0, 0.47, 0.84, 1),
        ))
        layout.add_widget(Widget(size_hint_y=None, height=dp(16)))

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def _section_label(self, text):
        return MDLabel(text=text, font_style="Overline", theme_text_color="Primary",
                       adaptive_height=True, padding=(0, dp(4)))

    def _add_level(self, *args, is_first=False):
        self._level_counter += 1
        # Sugestão de profundidade decrescente para novos níveis
        default_depth = 30 if is_first else max(5, 30 - (self._level_counter - 1) * 10)
        card = DiveLevelCard(
            index=self._level_counter,
            is_first=is_first,
            on_remove=self._remove_level,
            default_depth=default_depth,
            default_time=20,
        )
        self._level_cards.append(card)
        self.level_layout.add_widget(card)

    def _remove_level(self, card):
        if card in self._level_cards:
            self._level_cards.remove(card)
            self.level_layout.remove_widget(card)

    def _add_deco_gas(self, *args):
        self._deco_gas_counter += 1
        card = DecoGasCard(
            index=self._deco_gas_counter,
            on_remove=self._remove_deco_gas,
        )
        self._deco_gas_cards.append(card)
        self.deco_gas_layout.add_widget(card)

    def _remove_deco_gas(self, card):
        if card in self._deco_gas_cards:
            self._deco_gas_cards.remove(card)
            self.deco_gas_layout.remove_widget(card)

    def _set_gf(self, lo, hi):
        self.field_gf_lo.text = str(lo)
        self.field_gf_hi.text = str(hi)

    def _on_calculate(self, *args):
        try:
            surface_interval = float(self.field_surface.text or "0")
            sac_rate = float(self.field_sac.text or "20")
            gf_lo = float(self.field_gf_lo.text or "85") / 100.0
            gf_hi = float(self.field_gf_hi.text or "85") / 100.0
        except ValueError as e:
            self._show_error(f"Valores inválidos: {e}")
            return

        if not (0 < gf_lo <= 1.0 and 0 < gf_hi <= 1.0):
            self._show_error("Gradient Factors devem estar entre 1 e 100%.")
            return
        if sac_rate <= 0:
            self._show_error("SAC deve ser maior que zero.")
            return

        # Coleta níveis
        levels = []
        for card in self._level_cards:
            d = card.get_data()
            if d['depth'] <= 0:
                self._show_error("Profundidade deve ser maior que zero.")
                return
            levels.append(d)

        if not levels:
            self._show_error("Adicione pelo menos um nível de mergulho.")
            return

        # Coleta gases de deco
        deco_gases = []
        for card in self._deco_gas_cards:
            try:
                g = card.get_gas()
                sw = card.get_switch_depth()
                deco_gases.append((sw, g))
            except ValueError as e:
                self._show_error(f"Gás de deco inválido: {e}")
                return

        from buhlmann import BuhlmannDive

        dive = BuhlmannDive(gf_lo=gf_lo, gf_hi=gf_hi)
        if surface_interval > 0:
            dive.surface_interval(surface_interval)

        # NDL no primeiro nível, antes de qualquer segmento
        ndl = dive.ndl(levels[0]['depth'], levels[0]['gas'])

        # Aplica todos os níveis em sequência
        ascent_rate = 10.0
        level_consumption = {}

        def _p(d):
            return 1.0 + d / 10.0

        # Nível 0: descida + fundo
        desc_t = levels[0]['depth'] / ascent_rate
        p_avg_desc = (_p(0) + _p(levels[0]['depth'])) / 2.0
        g0 = levels[0]['gas']
        dive.add_segment(levels[0]['depth'] / 2.0, desc_t, g0)
        k = str(g0)
        level_consumption[k] = level_consumption.get(k, 0.0) + sac_rate * p_avg_desc * desc_t
        dive.add_segment(levels[0]['depth'], levels[0]['time'], g0)
        level_consumption[k] += sac_rate * _p(levels[0]['depth']) * levels[0]['time']

        # Níveis seguintes
        for i in range(1, len(levels)):
            prev = levels[i - 1]
            curr = levels[i]
            trans_t = abs(prev['depth'] - curr['depth']) / ascent_rate
            avg_p = (_p(prev['depth']) + _p(curr['depth'])) / 2.0
            # Transição usando gás do nível anterior
            mid_d = (prev['depth'] + curr['depth']) / 2.0
            dive.add_segment(mid_d, trans_t, prev['gas'])
            pk = str(prev['gas'])
            level_consumption[pk] = level_consumption.get(pk, 0.0) + sac_rate * avg_p * trans_t
            # Fundo do nível atual
            dive.add_segment(curr['depth'], curr['time'], curr['gas'])
            ck = str(curr['gas'])
            level_consumption[ck] = level_consumption.get(ck, 0.0) + sac_rate * _p(curr['depth']) * curr['time']

        # Paradas descompressivas a partir do último nível
        last_depth = levels[-1]['depth']
        last_gas = levels[-1]['gas']
        stops, deco_consumption = dive.deco_stops_multi_gas(
            last_depth, last_gas, deco_gases, sac_rate=sac_rate
        )

        # Junta consumos
        full_consumption = dict(level_consumption)
        for k, v in deco_consumption.items():
            full_consumption[k] = full_consumption.get(k, 0.0) + v

        saturation = dive.tissue_saturation()
        group = dive.repetitive_group()
        total_asc = last_depth / 10.0 + sum(s['time'] for s in stops)

        result_screen = self.manager.get_screen('result')
        result_screen.populate(
            levels=levels,
            deco_gases=deco_gases,
            gf_lo=gf_lo,
            gf_hi=gf_hi,
            sac_rate=sac_rate,
            surface_interval=surface_interval,
            ndl_before=ndl,
            stops=stops,
            consumption=full_consumption,
            saturation=saturation,
            group=group,
            total_ascent=total_asc,
        )
        self.manager.current = 'result'

    def _show_error(self, msg):
        d = MDDialog(
            title="Erro de entrada",
            text=msg,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())],
        )
        d.open()
