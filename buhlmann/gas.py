from .constants import P_H2O


class GasMix:
    """Representa uma mistura de gases de mergulho (O2/N2/He)."""

    def __init__(self, o2: float, n2: float, he: float):
        """
        Args:
            o2: fração de oxigênio (0.0–1.0)
            n2: fração de nitrogênio (0.0–1.0)
            he: fração de hélio (0.0–1.0)
        """
        if abs(o2 + n2 + he - 1.0) > 0.001:
            raise ValueError(f"Frações de gás devem somar 1.0 (recebido {o2+n2+he:.4f})")
        if any(f < 0 for f in (o2, n2, he)):
            raise ValueError("Frações de gás não podem ser negativas")
        self.o2 = o2
        self.n2 = n2
        self.he = he

    def alveolar_n2(self, p_amb: float) -> float:
        """Pressão alveolar parcial de N2 em bar."""
        return max(0.0, (p_amb - P_H2O) * self.n2)

    def alveolar_he(self, p_amb: float) -> float:
        """Pressão alveolar parcial de He em bar."""
        return max(0.0, (p_amb - P_H2O) * self.he)

    def pp_o2(self, p_amb: float) -> float:
        """Pressão parcial de O2 em bar (para verificação de toxicidade)."""
        return p_amb * self.o2

    @classmethod
    def air(cls) -> "GasMix":
        return cls(0.21, 0.79, 0.0)

    def __repr__(self) -> str:
        o2 = round(self.o2 * 100)
        he = round(self.he * 100)
        if o2 == 21 and he == 0:
            return "Ar"
        if o2 == 100 and he == 0:
            return "O₂ Puro"
        if he == 0:
            return f"EAN{o2}"
        return f"Trimix {o2}/{he}"
