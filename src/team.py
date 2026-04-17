class TeamPlayoffOdds:
    def __init__(self, data: dict[str, str]):
        self.round1 = float(data.get("Round1", 0))
        self.round2 = float(data.get("Round2", 0))
        self.conference = float(data.get("Conference", 0))
        self.final = float(data.get("Final", 0))


class Team:
    estimatedValue: float = 0.0

    def __init__(self, data: dict[str, str]):
        self.name = data["Name"]
        self.odds = TeamPlayoffOdds(data)

    @classmethod
    def from_name(cls, name: str) -> "Team":
        return cls({"Name": name})

    def __repr__(self):
        return f"{self.name}: Final={self.odds.final:.3f}"