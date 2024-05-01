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
            cutoff = 0.5

            if self.player1.skill is not None:
                try:
                    percent_diff = self.player1.percentile - self.player2.percentile
                    skill_percent_diff = percent_diff / 2.0
                except:
                    print('what')
        
            if self.player1.deck is not None:
                deck1_name = self.player1.deck.name
                deck2_name = self.player2.deck.name
                player1_wr = self.player1.deck.winrates[deck2_name]
                player2_wr = self.player2.deck.winrates[deck1_name]

                if self.player1.skill is not None:
                    if percent_diff > 0.5:
                        matchup_cutoff = player1_wr
                    elif percent_diff < 0.5:
                        matchup_cutoff = player2_wr
                    else:
                        matchup_cutoff = (player1_wr + (1 - player2_wr)) / 2.0

                else:
                    matchup_cutoff = (player1_wr + (1 - player2_wr)) / 2.0


            if self.player1.deck is None:
                if self.player1.skill is not None:
                    # Case 1: No decks, but skill is used
                    cutoff = cutoff + skill_percent_diff # Use luck (0.5 original cutoff) + skill differential

            else:
                if self.player1.skill is None:
                    # Case 2: Deck present, no skill used
                    cutoff = matchup_cutoff # Entirely use matchups to determine this, since that already includes luck
        
                else:
                    # Case 3: Decks and skill both present
                    weight_factor = np.abs(percent_diff)
                    cutoff = matchup_cutoff * (1 -  weight_factor) + skill_percent_diff * weight_factor



            if bo3:
                num_games = 3
            else:
                num_games = 2

            for game in range(num_games):
                # if self.player1.deck == None and self.player2.deck == None:
                roll = np.random.random()
                if roll < cutoff:
                    self.score[0] = self.score[0] + 1
                else:
                    self.score[1] = self.score[1] + 1
        return self.score


class Deck:

    def __init__(self, row):
        self.name = row.name
        self.winrates = {}
        for deck_idx, val in row.items():
            self.winrates[deck_idx] = val

    def update_winrates(self, deck, winrate):
        self.winrates[deck] = winrate
        return self


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
            
        
def bad_method_for_deck_matrix():
    decks = [
        'GP Tempo',
        'RB Dime',
        'AS Steelsong',
        'BS Ramp',
        'GS Aggro Discard',
        'AR Mufasa',
        'Am Am Hyperaggro',
        'PS Jafar',
        'RP Control',
        'BP Blurple',
        'Default'
        ]
    deck_matrix = pd.DataFrame(columns= decks, index=decks)

    default_winrates = [0.5] * len(decks)

    deck_matrix['GP Tempo'] = [0.5, 0.75, 0.5, 0.55, 0.45, 0.66, 0.5, 0.55, 0.7, 0.5, 0.5] # 1  Artabax data
    deck_matrix['RB Dime'] = [0.4, 0.5, 0.75, 0.8, 0.65, 0.5, 0.3, 0.85, 0.5, 0.3, 0.5] # 2     Jbaum data
    deck_matrix['AS Steelsong'] = [0.5, 0.2, 0.5, 0.6, 0.75, 0.75, 0.6, 0.7, 0.6, 0.3, 0.5] # 3 Chuck data
    deck_matrix['BS Ramp'] = [0.7, 0.3, 0.4, 0.5, 0.7, 0.4, 0.6, 0.7, 0.6, 0.5, 0.5] # 4        Jak data
    deck_matrix['GS Aggro Discard'] = [0.55, 0.7, 0.4, 0.5, 0.5, 0.66, 0.75, 0.3, 0.75, 0.55, 0.5] # 5
    deck_matrix['AR Mufasa'] = [0.6, 0.65, 0.6, 0.85, 0.65, 0.5, 0.5, 0.6, 0.66, 0.5, 0.5] # 6
    deck_matrix['Am Am Hyperaggro'] = [0.4, 0.8, 0.3, 0.7, 0.3, 0.7, 0.5, 0.35, 0.7, 0.7, 0.5] # 7
    deck_matrix['PS Jafar'] = [0.6, 0.4, 0.3, 0.4, 0.5, 0.4, 0.7, 0.5, 0.65, 0.3, 0.5] # 8
    deck_matrix['RP Control'] = [0.5, 0.6, 0.55, 0.45, 0.35, 0.45, 0.3, 0.55, 0.5, 0.5, 0.5] # 9
    deck_matrix['BP Blurple'] = [0.65, 0.6, 0.65, 0.6, 0.55, 0.5, 0.35, 0.65, 0.6, 0.5, 0.5] # 10
    deck_matrix['Default'] = default_winrates

    return deck_matrix.T


def construct_deck_distribution(deck_matrix_dist):

    deck_intervals = {}

    start = 0.0
    closed='both'
    for deck in deck_matrix_dist.keys():
        prop = deck_matrix_dist[deck]
        end = start + prop
        deck_intervals[deck] = pd.Interval(start, end, closed=closed)
        start = end
        closed='right'

    assert np.abs(end - 1.0) < 1e-8
    return deck_intervals


def choose_deck(deck_intervals):

    random_roll = np.random.random()
    for deck, interval in deck_intervals.items():
        if random_roll in interval:
            return deck

    return 'Default'





if __name__ == '__main__':

    points_for_32 = []
    points_for_64 = []
    points_for_me = []
    points_for_16 = []
    num_players_tied_with_32 = []
    in_top_cut = 0

    deck_matrix = bad_method_for_deck_matrix()

    deck_distribution = {
        'GP Tempo' : 0.05,
        'RB Dime' : 0.2,
        'AS Steelsong': 0.2,
        'BS Ramp' : 0.05,
        'GS Aggro Discard' : 0.1,
        'AR Mufasa' : 0.05,
        'Am Am Hyperaggro' : 0.05,
        'PS Jafar' : 0.05,
        'RP Control' : 0.2,
        'BP Blurple' : 0.05,
        'Default' : 0.0
    }
    deck_intervals = construct_deck_distribution(deck_distribution)
    
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

    for mc in range(50):
        num_players = 2047  #128, 256, 512
        players = []

        my_deck = Deck(deck_matrix.loc['RP Control'])
        me = Player(num_players, deck=my_deck, skill=my_skill, dist=dist, loc=my_loc, scale=my_scale)

        for play in range(num_players):

            if dist == 'Normal':
                skill_level = np.random.normal(loc=my_loc, scale=my_scale)
            elif dist == 'Beta':
                skill_level = 1 - np.random.beta(2, 5)
            else:
                skill_level = None
                dist = None

            curr_deck = choose_deck(deck_intervals)
            player_deck = Deck(deck_matrix.loc[curr_deck])


            players.append(
                Player(play, deck=player_deck, skill=skill_level, dist=dist, loc=my_loc, scale=my_scale)
            )
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
        if me.points > points_64:
            in_top_cut += 1


        tied_with_32 = my_tournament.rankings[my_tournament.rankings['Points'] > points_32 - 1]
        thirty_x = tied_with_32.loc[32:,]
        bubbled_out = len(thirty_x)
        num_players_tied_with_32.append(bubbled_out)

        player_16 = my_tournament.players[15]
        points_16 = player_16.points
        points_for_16.append(points_16)

    # plt.hist(points_for_16)
    # plt.title(f'{dist} Distribution -- Top 16')
    # plt.show()
    # my_tournament.rankings.to_csv(r'C:\\Users\jrobc\Documents\Tournament_Simulator\example_rankings.csv')

    # plt.hist(points_for_32)
    # plt.title(f'{dist} Distribution -- Top 32')
    # plt.show()

    # plt.hist(points_for_64)
    # plt.title(f'{dist} Distribution -- Top 64')
    # plt.show()

    top_cut_percent = (in_top_cut / 500) * 100
    print(f'I made top cut {in_top_cut} times out of 500, so {top_cut_percent} % with {me.deck.name}')

    # plt.hist(points_for_me)
    # plt.title(f'{dist} Distribution for Me')
    # plt.show()

    # plt.hist(num_players_tied_with_32)
    # plt.title(f'{dist} Distribution # of Players Bubbled')
    # plt.show()
