import requests
import pandas as pd
import json

# Replace with your actual league ID and week number
league_id = "1119602622941523968"  # Add your actual league ID
current_week = 4  # Change this to the current week of the season
start_week = 1  # Start from Week 1

# Placeholder dictionaries for the 5 stats
bench_efficiency = {}
trade_impact = {}
waiver_pickups = {}
underperforming_players = {}
top_scorers = {}

# Placeholder for total player points across all weeks
roster_player_points = {}
roster_bench_points = {}
player_points_total = {}
# Placeholder for total player points by position across all weeks
team_position_points = {}
# Identify Underperforming Players
url_players = "https://api.sleeper.app/v1/players/nfl"
response_players = requests.get(url_players)
players_data = response_players.json()
# Fetch rosters to map roster_id to user_id and team_name
url_rosters = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
response_rosters = requests.get(url_rosters)
rosters = response_rosters.json()
# Loop through each week and fetch matchups
for week in range(start_week, current_week + 1):
    print(f"Fetching matchups for Week {week}...")
    
    # Fetch matchups for each week
    url_matchups = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
    response_matchups = requests.get(url_matchups)
    
    if response_matchups.status_code != 200:
        print(f"Error fetching matchups for Week {week}")
        continue

    matchups = response_matchups.json()

    url_transactions = f"https://api.sleeper.app/v1/league/{league_id}/transactions/{week}"
    response_transactions = requests.get(url_transactions)
    transactions = response_transactions.json()

    # Accumulate player points and calculate Bench Efficiency and Top Scorers
    for matchup in matchups:
        roster_id = matchup['roster_id']
        players_points = matchup.get('players_points', {})
        starters = matchup.get('starters', [])
        players = matchup.get('players', [])
        bench = list(set(players) - set(starters))
        
        # Initialize roster's player points and bench points if not already done
        if roster_id not in roster_player_points:
            roster_player_points[roster_id] = {}
        if roster_id not in roster_bench_points:
            roster_bench_points[roster_id] = {}

        # Track top scorers by accumulating points for each player in starters
        if roster_id not in top_scorers:
            top_scorers[roster_id] = {}

        for player_id in starters:
            player_points = players_points.get(player_id, 0)
            if player_id in top_scorers[roster_id]:
                top_scorers[roster_id][player_id] += player_points
            else:
                top_scorers[roster_id][player_id] = player_points

        # For each starter, accumulate points for that player within that roster
        for player_id in starters:
            points = players_points.get(player_id, 0)
            if player_id in roster_player_points[roster_id]:
                roster_player_points[roster_id][player_id] += points
            else:
                roster_player_points[roster_id][player_id] = points

        # For each bench player, accumulate points for that player within that roster
        for player_id in bench:
            points = players_points.get(player_id, 0)
            if player_id in roster_bench_points[roster_id]:
                roster_bench_points[roster_id][player_id] += points
            else:
                roster_bench_points[roster_id][player_id] = points

        # Populate player_points_total (add all player points across rosters)
        for player_id, points in players_points.items():
            if player_id in player_points_total:
                player_points_total[player_id] += points
            else:
                player_points_total[player_id] = points
        
        #### PLAYER POINTS PER POSITION ####
        roster_id = matchup['roster_id']
        players_points = matchup.get('players_points', {})
        starters = matchup.get('starters', [])

        # Initialize team position points if not already done
        if roster_id not in team_position_points:
            team_position_points[roster_id] = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'FLEX': 0, 'K': 0, 'DEF': 0}

        # For each starter, accumulate points based on their position
        for player_id in starters:
            player_points = players_points.get(player_id, 0)
            player_position = players_data.get(player_id, {}).get('position', 'Unknown')

            # Accumulate points by position
            if player_position in team_position_points[roster_id]:
                team_position_points[roster_id][player_position] += player_points
            else:
                # Handle FLEX or other positions if needed
                if player_position in ['RB', 'WR', 'TE']:
                    team_position_points[roster_id]['FLEX'] += player_points
                else:
                    print(f"Unknown position: {player_position} for player {player_id}")
    # Process Waiver Pickups and Trade Impact
    for transaction in transactions:
        if transaction['type'] == 'waiver':
            user_id = transaction['roster_ids'][0]
            added_player_ids = list(transaction['adds'].keys())

            # Calculate total points for the players added via waivers
            total_waiver_points = sum([player_points_total.get(player_id, 0) for player_id in added_player_ids])

            if user_id not in waiver_pickups:
                waiver_pickups[user_id] = 0  # Initialize if not already in the dictionary

            waiver_pickups[user_id] += total_waiver_points  # Accumulate waiver points

        elif transaction['type'] == 'trade':
            # Calculate trade impact
            user_ids = transaction['roster_ids']
            added_player_ids = list(transaction['adds'].keys())

            for user_id in user_ids:
                team_trade_points = sum([player_points_total.get(player_id, 0) for player_id in added_player_ids])
                if user_id not in trade_impact:
                    trade_impact[user_id] = 0  # Initialize if not already in the dictionary

                trade_impact[user_id] += team_trade_points  # Accumulate trade points

# Identify Underperforming Players
url_players = "https://api.sleeper.app/v1/players/nfl"
response_players = requests.get(url_players)
players_data = response_players.json()

for player_id, total_points in player_points_total.items():
    projected_points = players_data.get(player_id, {}).get('pts_proj', 0)
    if projected_points > 0 and total_points < projected_points * 0.8:  # 80% threshold for underperformance
        underperforming_players[player_id] = total_points

# Fetch rosters to map roster_id to user_id
url_rosters = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
response_rosters = requests.get(url_rosters)
rosters = response_rosters.json()

# Map roster_id to user_id
roster_id_to_user_id = {roster['roster_id']: roster['owner_id'] for roster in rosters}

# Fetch user data from Sleeper API to map user_id to display_name
url_users = f"https://api.sleeper.app/v1/league/{league_id}/users"
response_users = requests.get(url_users)
users = response_users.json()

# Map user display names to their user IDs
user_id_to_name = {user['user_id']: user['display_name'] for user in users}

# Calculate Bench Efficiency
bench_efficiency = {}

for roster_id in roster_player_points:
    # Calculate total points for starters and bench players
    total_starter_points = sum(roster_player_points[roster_id].values())
    total_bench_points = sum(roster_bench_points[roster_id].values())

    # Calculate total points
    total_points = total_starter_points + total_bench_points

    # Calculate bench efficiency if there are any points
    if total_points > 0:
        bench_efficiency[roster_id] = (total_starter_points / total_points) * 100
    else:
        bench_efficiency[roster_id] = 0

# Convert bench efficiency to a DataFrame
bench_efficiency_df = pd.DataFrame(list(bench_efficiency.items()), columns=['roster_id', 'bench_efficiency'])

# Convert other stats to DataFrames
top_scorers_df = pd.DataFrame([(user_id, player_id, points) for user_id, players in top_scorers.items() for player_id, points in players.items()], columns=['roster_id', 'player_id', 'total_points'])
waiver_pickups_df = pd.DataFrame(list(waiver_pickups.items()), columns=['roster_id', 'waiver_points'])
trade_impact_df = pd.DataFrame(list(trade_impact.items()), columns=['roster_id', 'trade_impact'])
underperforming_players_df = pd.DataFrame(list(underperforming_players.items()), columns=['player_id', 'total_points'])

# Replace roster_id with user_id in DataFrames and map user_id to team_name
top_scorers_df['user_id'] = top_scorers_df['roster_id'].map(roster_id_to_user_id)
top_scorers_df['team_name'] = top_scorers_df['user_id'].map(user_id_to_name)

bench_efficiency_df['user_id'] = bench_efficiency_df['roster_id'].map(roster_id_to_user_id)
bench_efficiency_df['team_name'] = bench_efficiency_df['user_id'].map(user_id_to_name)

waiver_pickups_df['user_id'] = waiver_pickups_df['roster_id'].map(roster_id_to_user_id)
waiver_pickups_df['team_name'] = waiver_pickups_df['user_id'].map(user_id_to_name)

trade_impact_df['user_id'] = trade_impact_df['roster_id'].map(roster_id_to_user_id)
trade_impact_df['team_name'] = trade_impact_df['user_id'].map(user_id_to_name)

# Map player_id to player_name in top_scorers_df
top_scorers_df['player_name'] = top_scorers_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('full_name', 'Unknown'))


# Convert team position points to DataFrame
team_position_df = pd.DataFrame.from_dict(team_position_points, orient='index')
# Drop unnecessary columns
top_scorers_df = top_scorers_df[['team_name', 'player_name', 'total_points']]
bench_efficiency_df = bench_efficiency_df[['team_name', 'bench_efficiency']]
waiver_pickups_df = waiver_pickups_df[['team_name', 'waiver_points']]
trade_impact_df = trade_impact_df[['team_name', 'trade_impact']]
underperforming_players_df['player_name'] = underperforming_players_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('full_name', 'Unknown'))
underperforming_players_df = underperforming_players_df[['player_name', 'total_points']]
# Map roster_id to user_id
roster_id_to_user_id = {roster['roster_id']: roster['owner_id'] for roster in rosters}

# Fetch user data to map user_id to display_name (team name)
url_users = f"https://api.sleeper.app/v1/league/{league_id}/users"
response_users = requests.get(url_users)
users = response_users.json()

# Map user display names to their user IDs
user_id_to_name = {user['user_id']: user['display_name'] for user in users}

# Add team name to the DataFrame
team_position_df['team_name'] = team_position_df.index.map(roster_id_to_user_id).map(user_id_to_name)

# Reorder the columns to have team_name first
team_position_df = team_position_df[['team_name', 'QB', 'RB', 'WR', 'TE', 'FLEX', 'K', 'DEF']]

# Display DataFrames with Pandas methods
print("Bench Efficiency")
print(bench_efficiency_df.head())
# Display the DataFrame
print("\nTeam Total Strength by Position:")
print(team_position_df.head())
print("\nTop Scorers")
print(top_scorers_df.head())

print("\nWaiver Pickups")
print(waiver_pickups_df.head())

print("\nTrade Impact")
print(trade_impact_df.head())

print("\nUnderperforming Players")
print(underperforming_players_df.head())

# Optionally, save DataFrames to CSV files
bench_efficiency_df.to_csv('bench_efficiency.csv', index=False)
top_scorers_df.to_csv('top_scorers.csv', index=False)
waiver_pickups_df.to_csv('waiver_pickups.csv', index=False)
trade_impact_df.to_csv('trade_impact.csv', index=False)
underperforming_players_df.to_csv('underperforming_players.csv', index=False)

# Optionally, save DataFrame to CSV
team_position_df.to_csv('team_position_strength.csv', index=False)
