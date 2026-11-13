import io as _io
from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image as KivyImage
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivy.uix.widget import Widget


class ResultScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def populate(self, levels, deco_gases, gf_lo, gf_hi, sac_rate,
                 surface_interval, ndl_before, stops, consumption,
                 saturation, group, total_ascent):
        self.clear_widgets()

        from buhlmann import mod as _mod

        # Referências rápidas
        bottom_gas = levels[0]['gas']        # gás do 1º nível (geralmente o mais profundo)
        last_gas   = levels[-1]['gas']       # gás do último nível (ponto de saída para deco)
        max_depth  = max(L['depth'] for L in levels)
        total_bottom = sum(L['time'] for L in levels)
        gf_lo_pct, gf_hi_pct = int(gf_lo * 100), int(gf_hi * 100)
        mod14 = _mod(bottom_gas, 1.4)
        mod16 = _mod(bottom_gas, 1.6)

        scroll = MDScrollView()
        layout = MDBoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(12),
            adaptive_height=True,
        )

        # Cabeçalho
        layout.add_widget(MDLabel(
            text="Resultado do Mergulho",
            font_style="H5",
            halign="center",
            adaptive_height=True,
        ))
        if len(levels) == 1:
            hdr_text = (f"{str(bottom_gas)}  |  {levels[0]['depth']:.0f}m  |  "
                        f"{levels[0]['time']:.0f}min  |  GF {gf_lo_pct}/{gf_hi_pct}")
        else:
            depths_str = " → ".join(f"{L['depth']:.0f}m/{L['time']:.0f}min" for L in levels)
            hdr_text = f"{len(levels)} níveis: {depths_str}  |  GF {gf_lo_pct}/{gf_hi_pct}"
        layout.add_widget(MDLabel(
            text=hdr_text,
            font_style="Caption",
            halign="center",
            theme_text_color="Secondary",
            adaptive_height=True,
        ))

        # ── GRÁFICO DE PERFIL (com PO₂/PN₂) ────────────────────────────────
        chart_widget = self._build_profile_chart(
            levels=levels,
            deco_gases=deco_gases,
            stops=stops,
            gf_lo=gf_lo,
            gf_hi=gf_hi,
            surface_interval=surface_interval,
            mod14=mod14,
        )
        if chart_widget:
            chart_card = self._card()
            chart_card.add_widget(chart_widget)
            layout.add_widget(chart_card)

        # ── MOD dos Níveis ───────────────────────────────────────────────────
        mod_card = self._card()
        mod_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(2))
        mod_box.add_widget(self._over("PROFUNDIDADE MÁXIMA POR NÍVEL"))
        for i, L in enumerate(levels):
            m14 = _mod(L['gas'], 1.4)
            m16 = _mod(L['gas'], 1.6)
            warn = " ⚠" if L['depth'] > m14 else ""
            mod_box.add_widget(MDLabel(
                text=(f"Nível {i+1} — {str(L['gas'])}  "
                      f"→  MOD {m14:.0f}m (PO₂ 1.4)  |  {m16:.0f}m (PO₂ 1.6){warn}"),
                font_style="Body2", adaptive_height=True,
                theme_text_color="Error" if warn else "Primary",
            ))
        mod_card.add_widget(mod_box)
        layout.add_widget(mod_card)

        # ── MOD dos Gases de Deco ────────────────────────────────────────────
        if deco_gases:
            dmod = self._card()
            db = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(2))
            db.add_widget(self._over("MOD DOS GASES DE DESCOMPRESSÃO"))
            for sw_depth, g in sorted(deco_gases, key=lambda x: x[0], reverse=True):
                db.add_widget(MDLabel(
                    text=f"{str(g)}  →  Troca em {sw_depth:.0f}m (PO₂ 1.6)",
                    font_style="Body2", adaptive_height=True,
                ))
            dmod.add_widget(db)
            layout.add_widget(dmod)

        # ── NDL ──────────────────────────────────────────────────────────────
        ndl_card = self._card()
        ndl_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12))
        is_deco = len(stops) > 0
        if ndl_before is None or is_deco:
            ndl_box.add_widget(MDLabel(
                text="MERGULHO DESCOMPRESSIVO",
                font_style="H6", halign="center",
                theme_text_color="Error", adaptive_height=True,
            ))
            if ndl_before is not None:
                ndl_box.add_widget(MDLabel(
                    text=(f"NDL em {levels[0]['depth']:.0f}m era {ndl_before:.0f} min — "
                          f"tempo total {total_bottom:.0f} min excedeu o limite"),
                    font_style="Caption", theme_text_color="Secondary",
                    halign="center", adaptive_height=True,
                ))
        else:
            ndl_box.add_widget(MDLabel(
                text=f"NDL: {ndl_before:.0f} min disponíveis",
                font_style="H6", halign="center", adaptive_height=True,
            ))
            remaining = ndl_before - total_bottom
            ndl_box.add_widget(MDLabel(
                text=f"Utilizado: {total_bottom:.0f} min  |  Margem: {remaining:.0f} min",
                font_style="Caption", halign="center",
                theme_text_color="Error" if remaining < 5 else "Secondary",
                adaptive_height=True,
            ))
        ndl_card.add_widget(ndl_box)
        layout.add_widget(ndl_card)

        # ── Paradas + Troca de Gás ───────────────────────────────────────────
        deco_card = self._card()
        deco_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(2))
        deco_box.add_widget(self._over("PARADAS DESCOMPRESSIVAS"))

        if not stops:
            deco_box.add_widget(MDLabel(
                text="Nenhuma parada necessária",
                font_style="Body1", halign="center",
                theme_text_color="Secondary", adaptive_height=True,
            ))
        else:
            hdr = MDBoxLayout(size_hint_y=None, height=dp(24))
            hdr.add_widget(MDLabel(text="Prof.", bold=True, size_hint_x=0.2, font_style="Caption"))
            hdr.add_widget(MDLabel(text="Tempo", bold=True, size_hint_x=0.2, font_style="Caption"))
            hdr.add_widget(MDLabel(text="Gás",  bold=True, size_hint_x=0.6, font_style="Caption"))
            deco_box.add_widget(hdr)

            prev_gas = last_gas   # gás com que se inicia a ascensão
            for stop in stops:
                cur_gas = stop['gas']
                if str(cur_gas) != str(prev_gas):
                    sw_row = MDBoxLayout(size_hint_y=None, height=dp(22))
                    sw_row.add_widget(MDLabel(
                        text=f"  → TROCAR PARA: {str(cur_gas)}",
                        font_style="Caption", theme_text_color="Error", bold=True,
                    ))
                    deco_box.add_widget(sw_row)

                row = MDBoxLayout(size_hint_y=None, height=dp(24))
                row.add_widget(MDLabel(text=f"{stop['depth']:.0f}m",   size_hint_x=0.2, font_style="Body2"))
                row.add_widget(MDLabel(text=f"{stop['time']} min",     size_hint_x=0.2, font_style="Body2"))
                row.add_widget(MDLabel(text=str(cur_gas),              size_hint_x=0.6,
                                       font_style="Body2", theme_text_color="Secondary"))
                deco_box.add_widget(row)
                prev_gas = cur_gas

            deco_box.add_widget(MDLabel(
                text=f"Tempo total de ascensão estimado: ~{total_ascent:.0f} min",
                font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
            ))
        deco_card.add_widget(deco_box)
        layout.add_widget(deco_card)

        # ── Consumo de Gás ───────────────────────────────────────────────────
        cons_card = self._card()
        cons_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(2))
        cons_box.add_widget(self._over(f"CONSUMO DE GÁS  (SAC = {sac_rate:.0f} L/min)"))
        total_liters = sum(consumption.values())
        ch = MDBoxLayout(size_hint_y=None, height=dp(22))
        ch.add_widget(MDLabel(text="Gás",         bold=True, font_style="Caption", size_hint_x=0.5))
        ch.add_widget(MDLabel(text="Consumo (L)", bold=True, font_style="Caption", size_hint_x=0.3))
        ch.add_widget(MDLabel(text="%",           bold=True, font_style="Caption", size_hint_x=0.2))
        cons_box.add_widget(ch)
        for gas_key, liters in sorted(consumption.items(), key=lambda x: -x[1]):
            pct = (liters / total_liters * 100) if total_liters > 0 else 0
            row = MDBoxLayout(size_hint_y=None, height=dp(22))
            row.add_widget(MDLabel(text=gas_key,        font_style="Caption", size_hint_x=0.5))
            row.add_widget(MDLabel(text=f"{liters:.0f}", font_style="Caption", size_hint_x=0.3))
            row.add_widget(MDLabel(text=f"{pct:.0f}%",  font_style="Caption", size_hint_x=0.2))
            cons_box.add_widget(row)
        cons_box.add_widget(MDLabel(
            text=f"TOTAL: {total_liters:.0f} L",
            font_style="Subtitle2", bold=True, adaptive_height=True,
        ))
        cons_card.add_widget(cons_box)
        layout.add_widget(cons_card)

        # ── Grupo de Repetição ───────────────────────────────────────────────
        grp_card = self._card()
        grp_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(4))
        grp_box.add_widget(self._over("GRUPO DE REPETIÇÃO"))
        grp_box.add_widget(MDLabel(text=group, font_style="H3", halign="center", adaptive_height=True))
        max_sat = max(saturation)
        grp_box.add_widget(MDLabel(
            text=f"Saturação máxima: {max_sat:.1f}%",
            font_style="Caption", halign="center",
            theme_text_color="Secondary", adaptive_height=True,
        ))
        prog = MDProgressBar(value=min(max_sat, 100), max=100)
        prog.color = (0.9, 0.2, 0.2, 1) if max_sat > 100 else (0.9, 0.6, 0.0, 1) if max_sat > 80 else (0.0, 0.7, 0.3, 1)
        grp_box.add_widget(prog)
        grp_card.add_widget(grp_box)
        layout.add_widget(grp_card)

        # ── Saturação Tecidual ───────────────────────────────────────────────
        sat_card = self._card()
        sat_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=dp(12), spacing=dp(2))
        sat_box.add_widget(self._over("SATURAÇÃO TECIDUAL (% M-VALUE)"))
        for i, sat in enumerate(saturation):
            row = MDBoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
            row.add_widget(MDLabel(text=f"C{i+1:02d}", font_style="Caption",
                                   size_hint_x=None, width=dp(30)))
            bar = MDProgressBar(value=min(sat, 100), max=100, size_hint_x=0.75)
            bar.color = (0.9, 0.2, 0.2, 1) if sat > 100 else (0.9, 0.6, 0.0, 1) if sat > 80 else (0.0, 0.47, 0.84, 1)
            row.add_widget(bar)
            row.add_widget(MDLabel(text=f"{sat:.0f}%", font_style="Caption",
                                   size_hint_x=None, width=dp(40), halign="right"))
            sat_box.add_widget(row)
        sat_card.add_widget(sat_box)
        layout.add_widget(sat_card)

        # Botão voltar
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))
        layout.add_widget(MDRaisedButton(
            text="NOVO MERGULHO",
            size_hint_x=1,
            on_release=lambda *a: setattr(self.manager, 'current', 'main'),
        ))
        layout.add_widget(Widget(size_hint_y=None, height=dp(16)))

        scroll.add_widget(layout)
        self.add_widget(scroll)

    # ── Geração do gráfico ───────────────────────────────────────────────────

    def _build_profile_chart(self, levels, deco_gases, stops, gf_lo, gf_hi,
                              surface_interval, mod14, ascent_rate=10.0):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from buhlmann import BuhlmannDive
            from kivy.core.image import Image as CoreImage
        except Exception:
            return None

        P_H2O = 0.0627

        # ── 1. Constrói waypoints (time, depth, gas) multi-nível ─────────
        waypoints = [(0.0, 0.0, levels[0]['gas'])]
        t = 0.0

        # Descida para o nível 0
        desc_t = levels[0]['depth'] / ascent_rate
        t += desc_t
        waypoints.append((t, levels[0]['depth'], levels[0]['gas']))
        t += levels[0]['time']
        waypoints.append((t, levels[0]['depth'], levels[0]['gas']))

        # Níveis subsequentes (transição + fundo)
        for i in range(1, len(levels)):
            prev = levels[i - 1]
            curr = levels[i]
            trans_t = abs(prev['depth'] - curr['depth']) / ascent_rate
            t += trans_t
            waypoints.append((t, curr['depth'], curr['gas']))
            t += curr['time']
            waypoints.append((t, curr['depth'], curr['gas']))

        # Paradas descompressivas
        curr_d = levels[-1]['depth']
        for stop in stops:
            asc_t = (curr_d - stop['depth']) / ascent_rate
            waypoints.append((t + asc_t,               stop['depth'], stop['gas']))
            waypoints.append((t + asc_t + stop['time'], stop['depth'], stop['gas']))
            t = t + asc_t + stop['time']
            curr_d = stop['depth']

        if curr_d > 0.1:
            last_gas = stops[-1]['gas'] if stops else levels[-1]['gas']
            waypoints.append((t + curr_d / ascent_rate, 0.0, last_gas))

        total_time = waypoints[-1][0]

        # ── 2. Função de interpolação dos waypoints ──────────────────────
        def interp_wp(t_q):
            for i in range(len(waypoints) - 1):
                t0, d0, g0 = waypoints[i]
                t1, d1, _  = waypoints[i + 1]
                if t0 <= t_q <= t1 + 1e-9:
                    f = (t_q - t0) / (t1 - t0) if t1 > t0 else 0.0
                    return d0 + (d1 - d0) * f, g0
            return 0.0, levels[-1]['gas']

        # ── 3. Simula ceiling + PP em alta resolução (Δt = 30 s) ─────────
        sim = BuhlmannDive(gf_lo=gf_lo, gf_hi=gf_hi)
        if surface_interval > 0:
            sim.surface_interval(surface_interval)

        dt = 0.5
        sim_t, sim_d, sim_c, sim_ppo2, sim_ppn2 = [], [], [], [], []
        t_sim = 0.0
        while t_sim < total_time:
            d_mid, g = interp_wp(t_sim + dt / 2)
            p_amb = 1.0 + d_mid / 10.0
            sim.add_segment(d_mid, dt, g)
            sim_t.append(t_sim + dt / 2)
            sim_d.append(d_mid)
            sim_c.append(sim.ceiling_depth())
            sim_ppo2.append(p_amb * g.o2)
            sim_ppn2.append(max(0.0, (p_amb - P_H2O) * g.n2))
            t_sim += dt

        # ── 4. Detecta trocas de gás ──────────────────────────────────────
        gas_switches = []
        prev_g = None
        for w_t, w_d, w_g in waypoints:
            if prev_g is not None and str(w_g) != str(prev_g):
                gas_switches.append((w_t, w_g))
            prev_g = w_g

        max_depth = max(L['depth'] for L in levels)

        # ── 5. Plot com dois subplots (perfil + PO₂/PN₂) ─────────────────
        fig, (ax, ax_pp) = plt.subplots(
            2, 1,
            figsize=(6.5, 4.6),
            dpi=95,
            gridspec_kw={'height_ratios': [2.5, 1], 'hspace': 0.05},
            sharex=True,
        )
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        ax_pp.set_facecolor('#1a1a2e')

        prof_t = [w[0] for w in waypoints]
        prof_d = [w[1] for w in waypoints]
        max_depth_plot = max(max_depth, max(prof_d, default=max_depth)) * 1.08

        # Perfil (azul)
        ax.fill_between(prof_t, prof_d, 0, alpha=0.22, color='#42a5f5', interpolate=True)
        ax.plot(prof_t, prof_d, color='#42a5f5', linewidth=2.0, label='Perfil', zorder=4)

        # Teto virtual (vermelho tracejado)
        ceil_nonzero = [c if c > 0.3 else 0 for c in sim_c]
        ax.plot(sim_t, ceil_nonzero, '--', color='#ef5350', linewidth=1.6,
                label='Teto virtual', zorder=5, alpha=0.9)

        # Zona deco
        ax.fill_between(sim_t, 0, ceil_nonzero,
                        where=[c > 0.3 for c in sim_c],
                        alpha=0.17, color='#ef5350', interpolate=True, label='Zona deco')

        # Linha do MOD (laranja pontilhado)
        if 0 < mod14 < max_depth_plot * 1.3 and mod14 < 300:
            ax.axhline(y=mod14, color='#ff9800', linestyle=':', linewidth=1.2,
                       alpha=0.75, label=f'MOD {mod14:.0f}m (1.4)', zorder=3)

        # Marcador de fim de descida e início de ascensão
        t_end_desc = levels[0]['depth'] / ascent_rate
        t_start_asc = t_end_desc + levels[0]['time']
        for phase_t in [t_end_desc, t_start_asc]:
            ax.axvline(x=phase_t, color='#546e7a', linestyle=':', linewidth=0.8, alpha=0.5, zorder=2)

        # Profundidades das paradas
        for stop in stops:
            ax.axhline(y=stop['depth'], color='#37474f', linestyle=':',
                       linewidth=0.6, alpha=0.5, zorder=2)

        # Trocas de gás (linhas verticais coloridas)
        sw_colors = ['#66bb6a', '#ffca28', '#ab47bc', '#26c6da']
        for idx, (t_sw, g_sw) in enumerate(gas_switches):
            c = sw_colors[idx % len(sw_colors)]
            ax.axvline(x=t_sw, color=c, linestyle='--', linewidth=1.4, alpha=0.9, zorder=6)
            d_sw, _ = interp_wp(t_sw)
            label_y = d_sw * 0.5 + max_depth_plot * 0.1
            ax.text(t_sw - 0.4, label_y,
                    f'→ {str(g_sw)}',
                    color=c, fontsize=6.5, fontweight='bold',
                    rotation=90, ha='right', va='center',
                    bbox=dict(boxstyle='round,pad=0.1', facecolor='#1a1a2e',
                              edgecolor='none', alpha=0.6))

        # Anotação do primeiro nível
        t_mid = t_end_desc + levels[0]['time'] / 2
        ax.annotate(
            f"{levels[0]['time']:.0f}min\n{levels[0]['depth']:.0f}m",
            xy=(t_mid, levels[0]['depth']),
            xytext=(t_mid, levels[0]['depth'] + max_depth_plot * 0.1),
            color='#90a4ae', fontsize=7, ha='center',
            arrowprops=dict(arrowstyle='-', color='#546e7a', lw=0.8),
        )

        # Título
        if len(levels) == 1:
            title = f"Perfil — {levels[0]['depth']:.0f}m / {levels[0]['time']:.0f}min — {str(levels[0]['gas'])}"
        else:
            depths_str = "→".join(f"{L['depth']:.0f}m" for L in levels)
            title = f"Perfil Multinível — {depths_str}"
        ax.set_title(title, color='#eceff1', fontsize=9.5, pad=5, fontweight='bold')

        ax.invert_yaxis()
        ax.set_ylim(max_depth_plot, -2.0)
        ax.set_xlim(-0.3, total_time * 1.03)
        ax.set_ylabel('Profundidade (m)', color='#b0bec5', fontsize=8.5)
        ax.tick_params(colors='#90a4ae', labelsize=7.5, labelbottom=False)
        for s in ax.spines.values():
            s.set_edgecolor('#2e3f4f')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(loc='lower right', fontsize=7, ncol=2,
                  facecolor='#263238', edgecolor='#37474f',
                  labelcolor='#b0bec5', framealpha=0.85)

        # ── Subplot PO₂/PN₂ ──────────────────────────────────────────────
        ax_pp.plot(sim_t, sim_ppo2, color='#66bb6a', linewidth=1.5, label='PO₂', zorder=4)
        ax_pp.plot(sim_t, sim_ppn2, color='#42a5f5', linewidth=1.4, label='PN₂ alv.', zorder=4, alpha=0.85)

        ax_pp.axhline(y=1.4, color='#ff9800', linestyle='--', linewidth=1.0, alpha=0.85,
                      label='PO₂ 1.4', zorder=3)
        ax_pp.axhline(y=1.6, color='#ef5350', linestyle='--', linewidth=1.0, alpha=0.85,
                      label='PO₂ 1.6', zorder=3)

        # Mesmas linhas de troca de gás no subplot
        for idx, (t_sw, _) in enumerate(gas_switches):
            c = sw_colors[idx % len(sw_colors)]
            ax_pp.axvline(x=t_sw, color=c, linestyle='--', linewidth=1.0, alpha=0.7, zorder=6)

        y_max_pp = max(2.0, max(sim_ppo2, default=2.0) * 1.15, max(sim_ppn2, default=2.0) * 1.1)
        ax_pp.set_ylim(0, y_max_pp)
        ax_pp.set_xlim(-0.3, total_time * 1.03)
        ax_pp.set_ylabel('P.P. (bar)', color='#b0bec5', fontsize=8)
        ax_pp.set_xlabel('Tempo (min)', color='#b0bec5', fontsize=8.5)
        ax_pp.tick_params(colors='#90a4ae', labelsize=7.5)
        for s in ax_pp.spines.values():
            s.set_edgecolor('#2e3f4f')
        ax_pp.spines['top'].set_visible(False)
        ax_pp.spines['right'].set_visible(False)
        ax_pp.legend(loc='upper right', fontsize=6.5, ncol=4,
                     facecolor='#263238', edgecolor='#37474f',
                     labelcolor='#b0bec5', framealpha=0.85)

        plt.tight_layout(pad=0.3)

        # ── 6. Renderiza para Kivy ────────────────────────────────────────
        buf = _io.BytesIO()
        fig.savefig(buf, format='png', dpi=95, bbox_inches='tight',
                    facecolor='#1a1a2e', edgecolor='none')
        plt.close(fig)
        buf.seek(0)

        from kivy.core.image import Image as CoreImage
        texture = CoreImage(buf, ext='png').texture
        img = KivyImage(
            texture=texture,
            size_hint_y=None,
            height=dp(390),
            allow_stretch=True,
            keep_ratio=True,
        )
        return img

    # ── helpers ──────────────────────────────────────────────────────────────

    def _card(self):
        return MDCard(orientation='vertical', padding=0,
                      size_hint_y=None, adaptive_height=True,
                      elevation=2, radius=[dp(8)])

    def _over(self, text):
        return MDLabel(text=text, font_style="Overline", theme_text_color="Secondary",
                       adaptive_height=True, padding=(dp(12), dp(8), dp(12), 0))
