import requests
import pandas as pd
import numpy as np
from openpyxl import load_workbook
import matplotlib.pyplot as plt
import os

BASE_URL = "https://fantasy.premierleague.com/api/"
Save_Location = "G:\My Drive"

def login_fpl(email, password):
    """Log in to FPL and return a session."""
    session = requests.session()
    login_url = "https://users.premierleague.com/accounts/login/"

    payload = {
        "login": email,
        "password": password,
        "redirect_uri": "https://fantasy.premierleague.com/",
        "app": "plfpl-web"
    }

    response = session.post(login_url, data=payload)
    response.raise_for_status()
    return session

def get_my_team(session, team_id, gw):
    """Fetch your team (squad) for a given gameweek."""
    url = BASE_URL + f"entry/{team_id}/event/{gw}/picks/"
    response = session.get(url)
    response.raise_for_status()
    return response.json()

def get_my_history(session, team_id):
    """Fetch your season history (GW scores, ranks, etc.)."""
    url = BASE_URL + f"entry/{team_id}/history/"
    response = session.get(url)
    response.raise_for_status()
    return response.json()


def get_my_leagues(session, team_id):
    """Fetch classic and H2H leagues info."""
    url = BASE_URL + f"entry/{team_id}/"
    response = session.get(url)
    response.raise_for_status()
    return response.json()["leagues"]

def get_live_points(gw):
    """Fetch live points for a given Gameweek."""
    url = BASE_URL + f"event/{gw}/live/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def export_to_excel_with_lookup(dataframes, player_lookup, filename="fpl_data.xlsx"):
    """
    Export multiple DataFrames to Excel and include a Lookup sheet.
    Automatically adds VLOOKUP formulas in 'My Team' sheet.
    
    player_lookup: DataFrame containing id, short_name, team_name, position, now_cost
    """
    # Export initial sheets
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        # Export lookup sheet
        player_lookup.to_excel(writer, sheet_name="Lookup", index=False)

    # Open workbook to add formulas
    wb = load_workbook(filename)

    if "My Team" in wb.sheetnames and "Lookup" in wb.sheetnames:
        ws_team = wb["My Team"]

        # Determine last column and add new headers
        col_max = ws_team.max_column
        new_columns = ["Player Name", "Team Name", "Position", "Cost (M)", "Total Team Value (M)"]
        for i, header in enumerate(new_columns, start=col_max + 1):
            ws_team.cell(row=1, column=i, value=header)

        # Add VLOOKUP formulas for each player row
        for row in range(2, ws_team.max_row + 1):
            player_id_cell = f"A{row}"  # adjust if player ID is in another column
            ws_team.cell(row=row, column=col_max + 1,
                         value=f"=VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 2, FALSE)")
            ws_team.cell(row=row, column=col_max + 2,
                         value=f"=VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 9, FALSE)")
            ws_team.cell(row=row, column=col_max + 3,
                         value=f"=VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 11, FALSE)")
            ws_team.cell(row=row, column=col_max + 4,
                         value=f"=VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 7, FALSE)/10")
            ws_team.cell(row=2, column=col_max + 5,
                         value=f"=SUM($J$2:$J$16)")

    Save_Path = os.path.join(Save_Location, filename)
    wb.save(Save_Path)
    print(f"✅ Data exported to {filename} with Lookup sheet and VLOOKUP formulas")

def get_bootstrap_data():
    """Fetch general FPL metadata: players, teams, positions."""
    url = BASE_URL + "bootstrap-static/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_league_standings(league_id, page=1):
    """Fetch all members of a classic mini-league."""
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_team_history(team_id):
    """Fetch season history for a given team ID."""
    url = f"https://fantasy.premierleague.com/api/entry/{team_id}/history/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def Mini_league_standings(league_id):
    """find mini league standings"""
    league_data = get_league_standings(league_id)

    managers = league_data["standings"]["results"]

    all_histories = []

    for manager in managers:
        team_id = manager["entry"]
        team_name = manager["entry_name"]
        player_name = manager["player_name"]

        history = get_team_history(team_id)
        history_df = pd.DataFrame(history["current"])
        history_df["manager"] = player_name
        history_df["team_name"] = team_name
        history_df["team_id"] = team_id

        all_histories.append(history_df)

    combined_histories = pd.concat(all_histories, ignore_index=True)

    return combined_histories

def plot_league_histories(histories_df):
    """
    Plot total points over gameweeks for all managers in a league.
    histories_df: DataFrame from combined_histories (includes manager, event, total_points)
    """

    #print(histories_df.head())
    #print(histories_df.columns)
    #print(histories_df.dtypes)
    plt.figure(figsize=(16, 8))  # wider
    #print(histories_df["manager"].unique())

    # Group by manager and plot each line
    for manager, df in histories_df.groupby("manager"):
        df = df.sort_values("event")  # sort by gameweek
        plt.plot(df["event"], df["total_points"], label=manager, linewidth=2)

        # Optionally annotate last point
        last_event = df["event"].iloc[-1]
        last_points = df["total_points"].iloc[-1]
        plt.text(last_event + 0.2, last_points, manager, fontsize=8)

    plt.title("League Total Points Over Time", fontsize=16, weight="bold")
    plt.xlabel("Gameweek")
    plt.ylabel("Total Points")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=8)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    EMAIL = input("your_email_here")
    PASSWORD = input("your_password_here")
    TEAM_ID = 1533428  # Replace with your FPL team ID (find in URL of your team page)
    GAMEWEEK = 1       # Change to current gameweek

    # Login
    session = login_fpl(EMAIL, PASSWORD)

    # Fetch player/teams metadata
    bootstrap = get_bootstrap_data()

    players_df = pd.DataFrame(bootstrap["elements"])
    teams_df = pd.DataFrame(bootstrap["teams"])
    positions_df = pd.DataFrame(bootstrap["element_types"])

    # Player lookup: id → full name, team, position
    player_lookup = players_df[["id", "web_name", "first_name", "second_name", "team", "element_type", "now_cost"]]

    # Add team/position names
    player_lookup = player_lookup.merge(teams_df[["id", "name"]], left_on="team", right_on="id", suffixes=("", "_team"))
    player_lookup = player_lookup.merge(positions_df[["id", "singular_name_short"]], left_on="element_type", right_on="id", suffixes=("", "_pos"))

    player_lookup = player_lookup.rename(columns={
        "web_name": "short_name",
        "name": "team_name",
        "singular_name_short": "position"
    })

    print(player_lookup.head())

    live_points = get_live_points(GAMEWEEK)

    # elements is a list of dicts → make DataFrame
    elements_df = pd.DataFrame(live_points["elements"])

    # Flatten stats dict into separate columns
    stats_df = pd.json_normalize(elements_df["stats"])
    stats_df["id"] = elements_df["id"]

    # Merge with player lookup
    live_with_names = stats_df.merge(player_lookup, on="id", how="left")

    print(live_with_names[[
        "id", "short_name", "team_name", "position",
        "minutes", "goals_scored", "assists", "clean_sheets", "total_points"
    ]].head())

    # 1. Fetch team for this GW
    my_team = get_my_team(session, TEAM_ID, GAMEWEEK)
    picks = pd.DataFrame(my_team["picks"])
    print("\nMy Team Picks:")
    print(picks.head())

    # 2. Fetch season history
    history = get_my_history(session, TEAM_ID)
    history_df = pd.DataFrame(history["current"])
    print("\nSeason History:")
    print(history_df.head())

    # 3. Fetch league info
    leagues = get_my_leagues(session, TEAM_ID)
    classic_leagues = pd.DataFrame(leagues["classic"])
    print("\nClassic Leagues:")
    print(classic_leagues.head())

    # 4. Fetch live points for this GW
    live_points = get_live_points(GAMEWEEK)

    # elements is already a list of dicts
    elements_list = live_points["elements"]

    # Flatten stats into columns
    stats_df = pd.json_normalize(elements_list, sep="_")

    # Merge with lookup for player details
    live_with_names = stats_df.merge(player_lookup, on="id", how="left")

    print("\nLive GW Points (flattened):")
    print(live_with_names.head())



    # 5. Mini League standings

    ale_league_id = 828398  # your mini-league ID
    OBC_league_id = 235840
    
    combined_histories_ale = Mini_league_standings(ale_league_id)
    combined_histories_OBC = Mini_league_standings(OBC_league_id)

    # Parameters
    managers = ["Dan Colling", "Alex Porfyrakis", "Zane Henry", "Freddie Beckett-Smith" ,"Clem Gibbs", "Jack Meads" , "Toby Williams" ]
    n_weeks = 38

    # Generate synthetic data
    data = []

    for manager in managers:
        total_points = 0
        for week in range(1, n_weeks + 1):
            # Random weekly points between 40 and 80
            weekly_points = np.random.randint(40, 80)
            total_points += weekly_points
            data.append({
                "manager": manager,
                "event": week,
                "total_points": total_points
            })
    # Create DataFrame
    histories_df = pd.DataFrame(data)
    print(histories_df.head())
    
    # 6. Export everything to Excel
    export_to_excel_with_lookup({
        "My Team": picks,
        "History": history_df,
        "Classic Leagues": classic_leagues,
        "Ale League Histories": combined_histories_ale,
        "OBC League Histories": combined_histories_OBC,
        "Live Points": live_with_names
    }, player_lookup)

    # 7. Plot league points
    plot_league_histories(histories_df)

    
