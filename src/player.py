from team import Team

class PlayerStats:
    def __init__(self, data: dict[str, str]):
        self.age = int(data["Age"])
        self.position = data["Pos"]
        self.games_played = int(data["GP"])
        self.goals = int(data["G"])
        self.assists = int(data["A"])
        self.points = int(data["P"])
        self.pim = int(data["PIM"])
        self.plus_minus = int(data["+/-"])
        self.toi = data["TOI"]
        self.toi_es = data["ES"]
        self.toi_pp = data["PP"]
        self.toi_sh = data["SH"]
        self.shots = int(data["SHOTS"])
        self.hits = int(data["HITS"])
        self.blocks = int(data["BS"])
        self.fow = int(data["FOW"])
        self.fol = int(data["FOL"])

        self.sh_pct = self._parse_percent(data["SH%"])
        self.fo_pct = self._parse_percent(data["FO%"])
        self.ppp_pct = self._parse_percent(data["PPP%"])

    def _parse_percent(self, val: str) -> float:
        return float(val.strip('%')) / 100 if val else 0.0


class Player:
    def __init__(self, team: Team, seasonStats: dict[str, str], stretchStats: dict[str, str]):
        self.name = data["Name"]
        self.team = team
        self.seasonStats = PlayerStats(seasonStats)
        self.stretchStats = PlayerStats(stretchStats)

    def __repr__(self):
        return f"{self.name} ({self.team}) - {self.seasonStats.points} points"
