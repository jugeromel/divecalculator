import math
import copy
from typing import Optional
from .constants import COMPARTMENTS, P_H2O
from .gas import GasMix


def mod(gas: GasMix, ppo2_max: float = 1.4) -> float:
    """Profundidade operacional máxima em metros para uma mistura de gás."""
    if gas.o2 <= 0:
        return float('inf')
    return (ppo2_max / gas.o2 - 1.0) * 10.0


def bottom_phase_consumption(depth_m: float, time_bottom: float,
                              sac_rate: float, ascent_rate: float = 10.0) -> float:
    """Consumo de gás (litros) durante descida + tempo de fundo."""
    descent_time = depth_m / ascent_rate
    p_bottom = _depth_to_pressure(depth_m)
    p_avg_descent = (1.0 + p_bottom) / 2.0
    return sac_rate * (p_avg_descent * descent_time + p_bottom * time_bottom)


def _depth_to_pressure(depth_m: float) -> float:
    return 1.0 + depth_m / 10.0


def _pressure_to_depth(p_bar: float) -> float:
    return max(0.0, (p_bar - 1.0) * 10.0)


def _schreiner(p_initial: float, p_alveolar: float, time_min: float, half_time: float) -> float:
    """Equação de Schreiner: carga tecidual exata para segmento de pressão constante."""
    if time_min <= 0:
        return p_initial
    k = math.log(2) / half_time
    return p_initial + (p_alveolar - p_initial) * (1.0 - math.exp(-k * time_min))


def _compartment_ceiling(pn2: float, phe: float,
                          an2: float, bn2: float,
                          ahe: float, bhe: float,
                          gf: float) -> float:
    """
    Pressão ambiente mínima (bar) para o compartimento não ultrapassar o M-value.
    Usa a fórmula Bühlmann com Gradient Factors.
    Retorna 0.0 se o compartimento está dentro dos limites na superfície.
    """
    total = pn2 + phe
    if total <= 0:
        return 0.0
    a_mix = (an2 * pn2 + ahe * phe) / total
    b_mix = (bn2 * pn2 + bhe * phe) / total
    # P_ceiling = (P_total - a*GF) / (GF/b - GF + 1)
    denom = gf / b_mix - gf + 1.0
    if denom <= 0:
        return 0.0
    ceiling = (total - a_mix * gf) / denom
    return max(0.0, ceiling)


def _surface_mvalue(pn2: float, phe: float,
                     an2: float, bn2: float,
                     ahe: float, bhe: float) -> float:
    """M-value máximo tolerado na superfície (P_amb = 1 bar, GF = 1.0)."""
    total = pn2 + phe
    if total <= 0:
        return 0.0
    a_mix = (an2 * pn2 + ahe * phe) / total
    b_mix = (bn2 * pn2 + bhe * phe) / total
    return a_mix + 1.0 / b_mix


class BuhlmannDive:
    """
    Calculador de descompressão Bühlmann ZH-L16C com Gradient Factors.

    Uso típico:
        dive = BuhlmannDive(gf_lo=0.3, gf_hi=0.85)
        air = GasMix(0.21, 0.79, 0.0)
        ndl = dive.ndl(30, air)          # minutos disponíveis
        dive.add_segment(30, 40, air)    # carrega tecidos
        stops = dive.deco_stops(30, air) # paradas necessárias
    """

    def __init__(self, gf_lo: float = 0.85, gf_hi: float = 0.85):
        if not (0 < gf_lo <= 1.0 and 0 < gf_hi <= 1.0):
            raise ValueError("GF deve estar entre 0 e 1")
        self.gf_lo = gf_lo
        self.gf_hi = gf_hi
        # Pressões teciduais: lista de [pn2, phe] por compartimento
        # Inicializa com ar na superfície: N2 = 0.79 × (1.0 - P_H2O)
        p_n2_surface = (1.0 - P_H2O) * 0.79
        self._tissues = [[p_n2_surface, 0.0] for _ in COMPARTMENTS]

    def _clone_tissues(self):
        return copy.deepcopy(self._tissues)

    def _load_tissues(self, tissues, depth_m: float, time_min: float, gas: GasMix):
        """Aplica carga tecidual para um segmento de profundidade/tempo constante."""
        p_amb = _depth_to_pressure(depth_m)
        p_alv_n2 = gas.alveolar_n2(p_amb)
        p_alv_he = gas.alveolar_he(p_amb)
        for i, (ht_n2, ht_he, an2, bn2, ahe, bhe) in enumerate(COMPARTMENTS):
            tissues[i][0] = _schreiner(tissues[i][0], p_alv_n2, time_min, ht_n2)
            tissues[i][1] = _schreiner(tissues[i][1], p_alv_he, time_min, ht_he)

    def add_segment(self, depth_m: float, time_min: float, gas: GasMix):
        """Carrega os tecidos com um segmento de mergulho (profundidade constante)."""
        self._load_tissues(self._tissues, depth_m, time_min, gas)

    def surface_interval(self, time_min: float):
        """Off-gassing na superfície durante o intervalo entre mergulhos."""
        self._load_tissues(self._tissues, 0.0, time_min, GasMix.air())

    def ceiling_depth(self, gf: Optional[float] = None) -> float:
        """
        Profundidade mínima segura de ascensão (metros).
        Usa gf_hi se não especificado (ceiling conservador para ascensão final).
        """
        if gf is None:
            gf = self.gf_hi
        max_ceiling_bar = 0.0
        for i, (_, _, an2, bn2, ahe, bhe) in enumerate(COMPARTMENTS):
            pn2, phe = self._tissues[i]
            c = _compartment_ceiling(pn2, phe, an2, bn2, ahe, bhe, gf)
            if c > max_ceiling_bar:
                max_ceiling_bar = c
        return _pressure_to_depth(max_ceiling_bar)

    def _ceiling_with_tissues(self, tissues, gf: float) -> float:
        max_ceiling_bar = 0.0
        for i, (_, _, an2, bn2, ahe, bhe) in enumerate(COMPARTMENTS):
            pn2, phe = tissues[i]
            c = _compartment_ceiling(pn2, phe, an2, bn2, ahe, bhe, gf)
            if c > max_ceiling_bar:
                max_ceiling_bar = c
        return _pressure_to_depth(max_ceiling_bar)

    def ndl(self, depth_m: float, gas: GasMix) -> Optional[float]:
        """
        Tempo restante sem descompressão (minutos) na profundidade dada.
        Retorna None se o mergulho já é descompressivo (ceiling > 0).
        """
        if self.ceiling_depth(gf=self.gf_hi) > 0.1:
            return None

        sim_tissues = self._clone_tissues()
        p_amb = _depth_to_pressure(depth_m)
        p_alv_n2 = gas.alveolar_n2(p_amb)
        p_alv_he = gas.alveolar_he(p_amb)

        # Busca binária: NDL entre 0 e 999 min
        lo, hi = 0.0, 999.0
        for _ in range(40):
            mid = (lo + hi) / 2
            test = self._clone_tissues()
            self._load_tissues(test, depth_m, mid, gas)
            # NDL: pode subir diretamente para a superfície (ceiling ≤ 0 com GF_hi)
            ceiling = self._ceiling_with_tissues(test, self.gf_hi)
            if ceiling <= 0.1:
                lo = mid
            else:
                hi = mid

        return round(lo, 1)

    def tissue_saturation(self) -> list:
        """
        Saturação de cada compartimento como % do M-value na superfície (GF=1).
        100% = exatamente no limite; >100% = em deco.
        """
        saturations = []
        for i, (_, _, an2, bn2, ahe, bhe) in enumerate(COMPARTMENTS):
            pn2, phe = self._tissues[i]
            total = pn2 + phe
            if total <= 0:
                saturations.append(0.0)
                continue
            m_val = _surface_mvalue(pn2, phe, an2, bn2, ahe, bhe)
            # Pressão inerte na superfície: tecido respirou ar em superfície → baseline não é zero
            # Saturação relativa ao M-value na superfície
            sat = (total / m_val) * 100.0 if m_val > 0 else 0.0
            saturations.append(round(sat, 1))
        return saturations

    def repetitive_group(self) -> str:
        """
        Letra do grupo de repetição (A–Z) baseada na saturação do compartimento líder.
        A = menor carga residual, Z = próximo do limite.
        """
        sats = self.tissue_saturation()
        max_sat = max(sats)
        # Mapeia 0-100% → A-Z (26 grupos)
        idx = min(int(max_sat / 100.0 * 26), 25)
        return chr(ord('A') + idx)

    def deco_stops(self, current_depth: float, gas: GasMix,
                   ascent_rate: float = 10.0,
                   stop_increment: float = 3.0) -> list:
        """
        Calcula paradas descompressivas necessárias.

        Args:
            current_depth: profundidade atual em metros
            gas: mistura de gás em uso
            ascent_rate: taxa de ascensão em m/min (padrão 10 m/min)
            stop_increment: incremento de profundidade das paradas (padrão 3m)

        Returns:
            Lista de tuplas (profundidade_m, tempo_min), ordenada de mais profunda
            para mais rasa. Lista vazia se não há paradas necessárias.
        """
        sim_tissues = self._clone_tissues()

        # Determina profundidade da primeira parada
        ceil_depth = self._ceiling_with_tissues(sim_tissues, self.gf_lo)
        if ceil_depth <= 0.1:
            return []  # Sem deco necessária

        # Arredonda ceiling para o múltiplo de stop_increment mais próximo acima
        first_stop = math.ceil(ceil_depth / stop_increment) * stop_increment
        first_stop = max(first_stop, stop_increment)

        stops = []
        depth = current_depth

        # Ascende até a primeira parada
        if depth > first_stop:
            ascent_time = (depth - first_stop) / ascent_rate
            self._load_tissues(sim_tissues, (depth + first_stop) / 2, ascent_time, gas)
            depth = first_stop

        # Processa cada parada de cima para baixo (mais profunda primeiro na lista)
        stop_depths = []
        d = first_stop
        while d >= stop_increment - 0.01:
            stop_depths.append(d)
            d -= stop_increment

        # Reordena de mais profunda para mais rasa e processa
        stop_depths = sorted(stop_depths, reverse=True)

        for stop_depth in stop_depths:
            # GF nesta parada: interpola entre gf_lo (primeira parada) e gf_hi (superfície)
            gf_at_stop = self._gf_at_depth(stop_depth, first_stop)

            stop_time = 0
            max_iterations = 300  # segurança contra loop infinito
            while self._ceiling_with_tissues(sim_tissues, gf_at_stop) > stop_depth - 0.1:
                self._load_tissues(sim_tissues, stop_depth, 1.0, gas)
                stop_time += 1
                if stop_time >= max_iterations:
                    break

            if stop_time > 0:
                stops.append((stop_depth, stop_time))

            # Ascende para próxima parada (ou superfície)
            next_depth = stop_depth - stop_increment
            if next_depth < 0:
                next_depth = 0.0
            if next_depth >= 0:
                asc_time = stop_increment / ascent_rate
                self._load_tissues(sim_tissues, (stop_depth + next_depth) / 2, asc_time, gas)

        return stops

    def _gf_at_depth(self, depth: float, first_stop_depth: float) -> float:
        """GF interpolado linearmente: gf_lo na parada mais profunda → gf_hi na superfície."""
        if first_stop_depth <= 0:
            return self.gf_hi
        ratio = 1.0 - depth / first_stop_depth
        return self.gf_lo + (self.gf_hi - self.gf_lo) * ratio

    def total_deco_time(self, current_depth: float, gas: GasMix,
                        ascent_rate: float = 10.0) -> float:
        """Tempo total de ascensão estimado (incluindo ascensão + paradas) em minutos."""
        stops = self.deco_stops(current_depth, gas, ascent_rate)
        ascent_time = current_depth / ascent_rate
        stop_time = sum(t for _, t in stops)
        return round(ascent_time + stop_time, 1)

    def deco_stops_multi_gas(self, current_depth: float, bottom_gas: GasMix,
                              deco_gases: list,
                              sac_rate: float = 20.0,
                              ascent_rate: float = 10.0,
                              stop_increment: float = 3.0) -> tuple:
        """
        Cálculo de paradas deco com múltiplos gases e rastreamento de consumo.

        Args:
            current_depth: profundidade atual em metros
            bottom_gas: gás principal do mergulho
            deco_gases: lista de (switch_depth_m, GasMix) — switch_depth = MOD do gás (PO₂ 1.6)
            sac_rate: consumo superficial em L/min
            ascent_rate: taxa de ascensão em m/min
            stop_increment: incremento entre paradas em metros

        Returns:
            (stops, consumption)
            stops: lista de dicts {'depth': float, 'time': int, 'gas': GasMix}
            consumption: dict {repr_str: litros}
        """
        sim_tissues = self._clone_tissues()
        consumption = {}  # str(gas) -> litros

        def track(gas, depth_m, time_min):
            key = str(gas)
            consumption[key] = consumption.get(key, 0.0) + sac_rate * _depth_to_pressure(depth_m) * time_min

        def select_gas(depth):
            # Seleciona o gás mais rico disponível nessa profundidade
            available = [(sd, g) for sd, g in deco_gases if depth <= sd]
            if not available:
                return bottom_gas
            return max(available, key=lambda x: x[1].o2)[1]

        ceil_depth = self._ceiling_with_tissues(sim_tissues, self.gf_lo)
        if ceil_depth <= 0.1:
            return [], {}

        first_stop = math.ceil(ceil_depth / stop_increment) * stop_increment
        first_stop = max(first_stop, stop_increment)

        stops = []

        # Ascensão do fundo até a primeira parada
        if current_depth > first_stop:
            asc_time = (current_depth - first_stop) / ascent_rate
            mid_depth = (current_depth + first_stop) / 2.0
            gas_asc = select_gas(mid_depth)
            self._load_tissues(sim_tissues, mid_depth, asc_time, gas_asc)
            track(gas_asc, mid_depth, asc_time)

        # Gera lista de profundidades de parada
        stop_depths = []
        d = first_stop
        while d >= stop_increment - 0.01:
            stop_depths.append(d)
            d -= stop_increment
        stop_depths = sorted(stop_depths, reverse=True)

        for stop_depth in stop_depths:
            gf_at_stop = self._gf_at_depth(stop_depth, first_stop)
            gas = select_gas(stop_depth)

            stop_time = 0
            while self._ceiling_with_tissues(sim_tissues, gf_at_stop) > stop_depth - 0.1:
                self._load_tissues(sim_tissues, stop_depth, 1.0, gas)
                track(gas, stop_depth, 1.0)
                stop_time += 1
                if stop_time >= 300:
                    break

            if stop_time > 0:
                stops.append({'depth': stop_depth, 'time': stop_time, 'gas': gas})

            # Ascende para a próxima parada
            next_depth = max(0.0, stop_depth - stop_increment)
            asc_time = stop_increment / ascent_rate
            mid = (stop_depth + next_depth) / 2.0
            self._load_tissues(sim_tissues, mid, asc_time, gas)
            track(gas, mid, asc_time)

        return stops, consumption
