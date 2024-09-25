import requests
import pandas as pd
import json

# Replace with your actual league ID and week number
league_id = "1119602622941523968"  # Add your actual league ID
current_week = 4 # Change this to the current week of the season
start_week = 1  # Start from Week 1

player_points_total = {}
### For projections
def get_player_projections(player_id, week, season="2024", season_type="regular", grouping="week"):
    url = f"https://api.sleeper.com/projections/nfl/player/{player_id}?season_type={season_type}&season={season}&grouping={grouping}"
    response = requests.get(url)
    if response.status_code == 200:
        projection_data = response.json()
        # Assuming week projections are available, return PPR projection for the given week
        
        week_str = str(week)
        # Check if the week exists in the projection_data dictionary
        if week_str in projection_data:
            # Extract the stats for the given week
            try:
                week_data = projection_data[week_str]
                stats = week_data.get('stats', {})
            except:
                return 0
            # Get the pts_ppr value from the stats, defaulting to 0 if not found
            return stats.get('pts_ppr', 0)
            # Return 0 if no projection is found for the given week
        return 0  # Default to 0 if no projection found
    
# Fetch player data early in the script
url_players = "https://api.sleeper.app/v1/players/nfl"
response_players = requests.get(url_players)

# Check if the API request was successful
if response_players.status_code == 200:
    players_data = response_players.json()
else:
    print(f"Failed to fetch players data: {response_players.status_code}")
    players_data = {}
# Fetch user data to map user_id to display_name (team name)
url_users = f"https://api.sleeper.app/v1/league/{league_id}/users"
response_users = requests.get(url_users)
users = response_users.json()

# Map user display names to their user IDs
user_id_to_name = {user['user_id']: user['display_name'] for user in users}

# Fetch rosters to map roster_id to user_id and team_name
url_rosters = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
response_rosters = requests.get(url_rosters)
rosters = response_rosters.json()

# Map roster_id to user_id
roster_id_to_user_id = {roster['roster_id']: roster['owner_id'] for roster in rosters}
import pandas as pd

# Placeholder lists to collect weekly data
weekly_bench_efficiency = []
weekly_top_scorers = []
weekly_waiver_pickups = []
weekly_trade_impact = []
weekly_discrepancies = []

#injuriesa
weekly_injury_losses = []
# Define injury-related statuses
injury_statuses = ['IR', 'out', 'questionable', 'Out']
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

    # Process matchups and transactions
    for matchup in matchups:
        roster_id = matchup['roster_id']
        players_points = matchup.get('players_points', {})
        starters = matchup.get('starters', [])
        players = matchup.get('players', [])
        bench = list(set(players) - set(starters))
        players_points = matchup.get('players_points', {})
        for player_id, points in players_points.items():
            if player_id in player_points_total:
                player_points_total[player_id] += points
            else:
                player_points_total[player_id] = points
        # Bench Efficiency
        total_starter_points = sum(players_points.get(player_id, 0) for player_id in starters)
        total_bench_points = sum(players_points.get(player_id, 0) for player_id in bench)
        total_points = total_starter_points + total_bench_points
        bench_efficiency = (total_starter_points / total_points) * 100 if total_points > 0 else 0

        # Collect bench efficiency data
        weekly_bench_efficiency.append({
            'week': week,
            'roster_id': roster_id,
            'bench_efficiency': bench_efficiency
        })

        # Top Scorers
        for player_id in starters:
            player_points = players_points.get(player_id, 0)
            weekly_top_scorers.append({
                'week': week,
                'roster_id': roster_id,
                'player_id': player_id,
                'total_points': player_points
            })

        # Discrepancy Data
        for player_id in players:
            actual_points = players_points.get(player_id, 0)
            projected_points = get_player_projections(player_id, week)
            discrepancy = projected_points - actual_points
    
            weekly_discrepancies.append({
                'week': week,
                'player_id': player_id,

                'roster_id': roster_id,
                'actual_points': actual_points,
                'projected_points': projected_points,
                'discrepancy': discrepancy
            })

          # Injsry df
            player_status = players_data.get(player_id, {}).get('injury_status')
            if player_status in injury_statuses:
                injury_point_loss = projected_points - actual_points
                weekly_injury_losses.append({
                    'week': week,
                    'player_id': player_id,
                    'team_name': roster_id,  # Replace with team_name if available
                    'projected_points': projected_points,
                    'actual_points': actual_points,
                    'injury_point_loss': injury_point_loss,
                    'status': player_status  # Record the player's injury status
                })

    # Process transactions for waiver pickups and trade impact
    for transaction in transactions:
        if transaction['type'] in ['waiver', 'free_agent']:  # Check if the transaction is either waiver or free_agent
            user_id = transaction['roster_ids'][0]
            
            # Check if 'adds' exists and is not None, otherwise skip the transaction
            if not transaction.get('adds'):
            
                continue
            added_player_ids = list(transaction['adds'].keys())
            total_waiver_points = sum([player_points_total.get(player_id, 0) for player_id in added_player_ids])
    
            weekly_waiver_pickups.append({
                'week': week,
                'roster_id': user_id,
                'waiver_points': total_waiver_points,
                'transaction_type': transaction['type']  # Add type of transaction (waiver or free_agent)
            })

        elif transaction['type'] == 'trade':
            user_ids = transaction['roster_ids']
            added_player_ids = list(transaction['adds'].keys())
            for user_id in user_ids:
                team_trade_points = sum([player_points_total.get(player_id, 0) for player_id in added_player_ids])
                weekly_trade_impact.append({
                    'week': week,
                    'roster_id': user_id,
                    'trade_impact': team_trade_points
                })

# Convert collected weekly data to DataFrames
bench_efficiency_df = pd.DataFrame(weekly_bench_efficiency)
top_scorers_df = pd.DataFrame(weekly_top_scorers)
waiver_pickups_df = pd.DataFrame(weekly_waiver_pickups)
trade_impact_df = pd.DataFrame(weekly_trade_impact)
discrepancy_df = pd.DataFrame(weekly_discrepancies)

# Replace roster_id with user_id and map to team_name
bench_efficiency_df['user_id'] = bench_efficiency_df['roster_id'].map(roster_id_to_user_id)
bench_efficiency_df['team_name'] = bench_efficiency_df['user_id'].map(user_id_to_name)

top_scorers_df['user_id'] = top_scorers_df['roster_id'].map(roster_id_to_user_id)
top_scorers_df['team_name'] = top_scorers_df['user_id'].map(user_id_to_name)

waiver_pickups_df['user_id'] = waiver_pickups_df['roster_id'].map(roster_id_to_user_id)
waiver_pickups_df['team_name'] = waiver_pickups_df['user_id'].map(user_id_to_name)

trade_impact_df['user_id'] = trade_impact_df['roster_id'].map(roster_id_to_user_id)
trade_impact_df['team_name'] = trade_impact_df['user_id'].map(user_id_to_name)

#Map out names
discrepancy_df['player_name'] = discrepancy_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('full_name', 'Unknown'))
discrepancy_df['position'] = discrepancy_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('position', 'Unknown'))
discrepancy_df['user_id'] = discrepancy_df['roster_id'].map(roster_id_to_user_id)
discrepancy_df['team_name'] =  discrepancy_df['user_id'].map(user_id_to_name)

top_scorers_df['player_name'] = top_scorers_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('full_name', 'Unknown'))
top_scorers_df['position'] = discrepancy_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('position', 'Unknown'))

#sort to add cumsum 
discrepancy_df['discrepancy'] = discrepancy_df['discrepancy'] * -1
# Sort by player and week to ensure cumulative sum is calculated in the correct order
discrepancy_df = discrepancy_df.sort_values(by=['player_id', 'week'])

# Add a cumulative sum column for discrepancies
discrepancy_df['cumulative_discrepancy'] = discrepancy_df.groupby('player_id')['discrepancy'].cumsum()

# Convert injury losses to DataFrame
injury_loss_df = pd.DataFrame(weekly_injury_losses)
# Convert injury losses to DataFrame
injury_loss_df['team_name'] =  injury_loss_df['team_name'].map(roster_id_to_user_id)
injury_loss_df['team_name'] =  injury_loss_df['team_name'].map(user_id_to_name)
injury_loss_df['player_name'] = injury_loss_df['player_id'].map(lambda pid: players_data.get(pid, {}).get('full_name', 'Unknown'))
# Display final DataFrames
print("Bench Efficiency (Weekly)")
print(bench_efficiency_df.head())

print("\nTop Scorers (Weekly)")
print(top_scorers_df.head())
# Print the injury point loss data
print("\nInjury Point Losses (Weekly)")
print(injury_loss_df.head())
print("\nWaiver Pickups (Weekly)")
print(waiver_pickups_df.head())

print("\nTrade Impact (Weekly)")
print(trade_impact_df.head())

print("\nDiscrepancies (Weekly)")
print(discrepancy_df.head())

# Save the weekly data to CSV files if needed
bench_efficiency_df.to_csv('weekly_bench_efficiency.csv', index=False)
top_scorers_df.to_csv('weekly_top_scorers.csv', index=False)
waiver_pickups_df.to_csv('weekly_waiver_pickups.csv', index=False)
trade_impact_df.to_csv('weekly_trade_impact.csv', index=False)
discrepancy_df.to_csv('weekly_discrepancies.csv', index=False)
injury_loss_df.to_csv('injury_loss.csv', index=False)
