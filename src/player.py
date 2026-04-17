from team import Team


class PlayerStats:
    def __init__(self, data: dict[str, str]):
        self.age = int(data.get("Age", 0))
        self.games_played = int(data.get("GP", 0))
        self.goals = int(data.get("G", 0))
        self.assists = int(data.get("A", 0))
        self.points = int(data.get("P", 0))
        self.overtime_goals = int(data.get("OTG", 0))
        self.pim = int(data.get("PIM", 0))
        self.plus_minus = int(data.get("+/-", 0))
        self.toi = data.get("TOI", "")
        self.toi_es = data.get("ES", "")
        self.even_strength_goals = int(data.get("ESG", 0))
        self.even_strength_points = int(data.get("ESP", 0))
        self.toi_pp = data.get("PP", "")
        self.toi_sh = data.get("SH", "")
        self.shots = int(data.get("SHOTS", 0))
        self.hits = int(data.get("HITS", 0))
        self.blocks = int(data.get("BS", 0))
        self.fow = int(data.get("FOW", 0))
        self.fol = int(data.get("FOL", 0))

        self.sh_pct = self._parse_percent(data.get("SH%", "0%"))
        self.fo_pct = self._parse_percent(data.get("FO%", "0%"))
        self.ppp_pct = self._parse_percent(data.get("PPP%", "0%"))

    def _parse_percent(self, val: str) -> float:
        return float(val.strip('%')) / 100 if val else 0.0


class Player:
    estimatedValue: float = 0.0

    def __init__(self, team: Team, seasonStats: dict[str, str], stretchStats: dict[str, str], prevSeasonStats: [dict[str, str]] = {}):
        self.name = seasonStats["Name"]
        self.team = team
        self.position = seasonStats["Pos"]
        self.seasonStats = PlayerStats(seasonStats)
        self.stretchStats = PlayerStats(stretchStats)
        self.prevSeasonStats = PlayerStats(prevSeasonStats)

    def __repr__(self):
        return f"{self.name} ({self.team.name}) - {self.estimatedValue:.3f} EV"
