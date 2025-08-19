import requests
import pandas as pd
from openpyxl import load_workbook
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
        new_columns = ["Player Name", "Team Name", "Position", "Cost"]
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

    Save_Path = os.path.join(Save_Location, filename)
    wb.save(Save_Path)
    print(f"✅ Data exported to {filename} with Lookup sheet and VLOOKUP formulas")

def get_bootstrap_data():
    """Fetch general FPL metadata: players, teams, positions."""
    url = BASE_URL + "bootstrap-static/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()



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
    # Flatten stats dict into separate columns
    elements_df = pd.DataFrame(live_points["elements"])  # list of dicts
    stats_df = pd.json_normalize(elements_df["stats"])  # flatten stats
    stats_df["id"] = elements_df["id"]  # add player id

    # Merge with player_lookup to add names, teams, positions
    live_with_names = stats_df.merge(player_lookup, on="id", how="left")

    # Now export live_with_names instead of elements_df
    export_to_excel_with_lookup(
        dataframes={
            "My Team": picks,
            "History": history_df,
            "Classic Leagues": classic_leagues,
            "Live Points": live_with_names  # flattened
        },
        player_lookup=player_lookup
    )

    
