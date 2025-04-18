class TeamPlayoffOdds:
    def __init__(self, data: dict[str, str]):
        self.round1 = float(data["Round1"])
        self.round2 = float(data["Round2"])
        self.conference = float(data["Conference"])
        self.final = float(data["Final"])


class Team:
    def __init__(self, data: dict[str, str]):
        self.name = data["Team"]
        self.odds = TeamPlayoffOdds(data)

    def __repr__(self):
        return f"{self.name}: Final={self.odds.final:.3f}"