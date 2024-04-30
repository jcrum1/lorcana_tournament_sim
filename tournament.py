import numpy as np
import pandas as pd
from math import ceil
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.stats import beta

# 1/(1+10^((opp elo - your elo)/400))

class Match:

    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.score = [0, 0]
     
    def play_match(self, bo3=False):

        if self.player2 == None:
            self.score[0] += 3
        else:
            if self.player1.skill is not None:
                percent_diff = self.player1.percentile - self.player2.percentile
                percent_diff = percent_diff / 2.0
                cutoff = 0.5 + percent_diff
            else:
                cutoff = 0.5

            if bo3:
                num_games = 3
            else:
                num_games = 2

            for game in range(num_games):
                if self.player1.deck == None and self.player2.deck == None:
                        roll = np.random.random()
                        if roll < cutoff:
                            self.score[0] = self.score[0] + 1
                        else:
                            self.score[1] = self.score[1] + 1
        return self.score


class Player:

    def __init__(self, id_number, deck=None, skill=None, dist=None, scale=1.0, loc=0.0):
        self.deck = deck
        self.skill = skill
        self.played_list = []
        self.points = 0.0
        self.paired = False
        self.id = id_number
        if skill is not None:
            if dist == 'Normal':
                self.percentile = norm.cdf(skill, loc=loc, scale=scale)
            elif dist == 'Beta':
                self.percentile = beta.cdf(skill, loc, scale)
        else:
            self.percentile = 1.0
        ### TODO:  Need to track opp win %, opp opp win %, and win % in game 2.

    def __str__(self):
        return str(self.id)

    def update_player(self, player2, score, bo3=False):
        self.played_list.append(player2)
        if score == 2:
            self.points += 7#3
        elif score == 1 and bo3==False:
            self.points += 3#1
        else:
            self.points += 0
        self.paired = False
        return self


class Tournament:

    def __init__(self, player_list, top_cut=32):
         self.num_rounds = ceil(np.log2(len(player_list)))
         self.players = player_list
         self.rankings = self.initialize_rankings()
         self.pairings = []

    def find_pairings(self):
        self.pairings = []
        for j in range(len(self.players)):
            player = self.players[j]
            for next_player_idx in range(j+1, len(self.players)):
                if player.paired == False:
                    next_player = self.players[next_player_idx]
                    if next_player.paired == False:
                        if next_player not in player.played_list:  ####  TODO:  Look into hashings for this.
                            player.paired = True
                            next_player.paired = True
                            self.pairings.append((player, next_player))
                            continue
                    else:
                        pass
                else:
                    break  # This is the case of pairing having happened.
                if player.paired == False:
                    self.pairings.append((player, None))
                    player.paired = True
        return self

    def run_round(self, bo3=False):
        current_players = []
        for pairing in self.pairings:
            player1 = pairing[0]
            player2 = pairing[1]
            curr_match = Match(player1, player2)
            score = curr_match.play_match(bo3)
            if player1 is not None:
                player1 = player1.update_player(player2, score[0], bo3)
                current_players.append(player1)
            if player2 is not None:
                player2 = player2.update_player(player1, score[1], bo3)
                current_players.append(player2)
        self.players = current_players
        return self

    def initialize_rankings(self):
        rankings = pd.DataFrame()
        player_ids = [p.id for p in self.players]
        player_skills = [p.percentile for p in self.players]
        player_points = [0]*len(self.players)
        opp_win_percent = [100]*len(self.players)
        opp_opp_win_percent = [100]*len(self.players)
        rankings['Player'] = self.players
        rankings['Player ID'] = player_ids
        rankings['Points'] = player_points
        rankings['Opp Win %'] = opp_win_percent
        rankings['Opp Opp Win %'] = opp_opp_win_percent
        rankings['Skill %'] = player_skills
        return rankings

    def update_rankings(self):
        for player in self.players:
            player_index = self.rankings[self.rankings['Player ID'] == player.id].index[0]
            self.rankings.at[player_index, 'Points'] = player.points
            self.rankings.at[player_index, 'Opp Win %'] = 100
            self.rankings.at[player_index, 'Opp Opp Win %'] = 100

        self.rankings = self.rankings.sort_values(['Points', 'Opp Win %', 'Opp Opp Win %'], ascending=False, ignore_index=True)
        self.players = list(self.rankings['Player'].values)
        return self
            
        

        


if __name__ == '__main__':

    points_for_32 = []
    points_for_64 = []
    points_for_me = []
    points_for_16 = []

    num_players_tied_with_32 = []
    
    dist = 'Normal'
    if dist == 'Normal':
        my_loc = 0
        my_scale = 1
        my_skill = 2.5
    elif dist == 'Beta':
        my_loc = 2
        my_scale = 5
        my_skill = 0.98
    else:
        my_loc = None
        my_scale = None
        my_skill = None

    for mc in range(500):
        num_players = 2047  #128, 256, 512
        players = []
        me = Player(num_players, skill=my_skill, dist=dist, loc=my_loc, scale=my_scale)

        for play in range(num_players):
            if dist == 'Normal':
                skill_level = np.random.normal(loc=my_loc, scale=my_scale)
            elif dist == 'Beta':
                skill_level = 1 - np.random.beta(2, 5)
            else:
                skill_level = None
                dist = None
            players.append(Player(play, skill=skill_level, dist=dist, loc=my_loc, scale=my_scale))
        players.append(me)

        my_tournament = Tournament(players)
        my_tournament.num_rounds = 9
        for round in range(my_tournament.num_rounds):
            my_tournament = my_tournament.find_pairings()
            my_tournament.run_round(bo3=False)
            my_tournament.update_rankings()

        player_32 = my_tournament.players[31]
        points_32 = player_32.points
        points_for_32.append(points_32)

        player_64 = my_tournament.players[63]
        points_64 = player_64.points
        points_for_64.append(points_64)

        points_for_me.append(me.points)

        tied_with_32 = my_tournament.rankings[my_tournament.rankings['Points'] > points_32 - 1]
        thirty_x = tied_with_32.loc[32:,]
        bubbled_out = len(thirty_x)
        num_players_tied_with_32.append(bubbled_out)

        player_16 = my_tournament.players[15]
        points_16 = player_16.points
        points_for_16.append(points_16)

    plt.hist(points_for_16)
    plt.title(f'{dist} Distribution -- Top 16')
    plt.show()
    my_tournament.rankings.to_csv(r'C:\\Users\jrobc\Documents\Tournament_Simulator\example_rankings.csv')

    plt.hist(points_for_32)
    plt.title(f'{dist} Distribution -- Top 32')
    plt.show()

    plt.hist(points_for_64)
    plt.title(f'{dist} Distribution -- Top 64')
    plt.show()

    # plt.hist(points_for_me)
    # plt.title(f'{dist} Distribution for Me')
    # plt.show()

    # plt.hist(num_players_tied_with_32)
    # plt.title(f'{dist} Distribution # of Players Bubbled')
    # plt.show()
