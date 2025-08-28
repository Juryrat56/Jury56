import requests
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill
import matplotlib.pyplot as plt
import os

BASE_URL = "https://fantasy.premierleague.com/api/"
Save_Location = "G:\My Drive"

# Define a fill style 
FDR1 = PatternFill(start_color="375523", end_color="375523", fill_type="solid")
FDR2 = PatternFill(start_color="01FC7A", end_color="01FC7A", fill_type="solid")
FDR3 = PatternFill(start_color="F5E000", end_color="F5E000", fill_type="solid")
FDR4 = PatternFill(start_color="FF1751", end_color="FF1751", fill_type="solid")
FDR5 = PatternFill(start_color="80072D", end_color="80072D", fill_type="solid")

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

def get_watchlist(filename):
    """get watchlist players from My Team sheet"""
    required_cols = "A:A"
    watch_df = pd.read_excel(f'{filename}', sheet_name = "My Team", skiprows = 0, usecols = required_cols)
    print("watchlist")
    print(watch_df.to_string(index=False))  # cleaner printout
    print("debug")
    return watch_df

def export_to_excel_with_lookup(dataframes, player_lookup, teams, fixtures, filename):
    """
    Export multiple DataFrames to Excel and include a Lookup sheet.
    Automatically adds VLOOKUP formulas in 'My Team' sheet.
    
    player_lookup: DataFrame containing id, short_name, team_name, position, now_cost
    """
    teams = teams.to_dict("records")
    team_lookup = {t["short_name"]: t["id"] for t in teams}
    
    print(type(teams))
    print(teams[0])
    
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
        ws_lookup = wb["Lookup"]

        # Determine last column and add new headers
        col_max = ws_team.max_column
        new_columns = ["Player Name", "Team Name","Team" , "Position", "Cost (M)", "Total Team Value (M)", "fixture 1", "FDR 1", "fixture 2", "FDR 2", "fixture 3", "FDR 3", "fixture 4", "FDR 4", "fixture 5", "FDR 5", "Team FDR", "AVG FDR"]
        for i, header in enumerate(new_columns, start=col_max + 1):
            ws_team.cell(row=1, column=i, value=header)

        # Add VLOOKUP formulas for each player row
        for row in range(2, ws_team.max_row + 8):
            player_id_cell = f"A{row}"  # adjust if player ID is in another column
            team_id_cell = f"I{row}"
            ws_team.cell(row=row, column=col_max + 1,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 2, FALSE))')
            ws_team.cell(row=row, column=col_max + 2,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 9, FALSE))')
            ws_team.cell(row=row, column=col_max + 3,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 5, FALSE))')
            ws_team.cell(row=row, column=col_max + 4,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 11, FALSE))')
            ws_team.cell(row=row, column=col_max + 5,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({player_id_cell}, Lookup!$A$2:$K$1000, 7, FALSE)/10)')
            ws_team.cell(row=2, column=col_max + 6,
                         value=f"=SUM($K$2:$K$16)")
            ws_team.cell(row=row, column=col_max + 7,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 19, FALSE))')
            ws_team.cell(row=row, column=col_max + 8,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 20, FALSE))')
            ws_team.cell(row=row, column=col_max + 9,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 21, FALSE))')
            ws_team.cell(row=row, column=col_max + 10,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 22, FALSE))')
            ws_team.cell(row=row, column=col_max + 11,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 23, FALSE))')
            ws_team.cell(row=row, column=col_max + 12,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 24, FALSE))')
            ws_team.cell(row=row, column=col_max + 13,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 25, FALSE))')
            ws_team.cell(row=row, column=col_max + 14,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 26, FALSE))')
            ws_team.cell(row=row, column=col_max + 15,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 27, FALSE))')
            ws_team.cell(row=row, column=col_max + 16,
                         value=f'=IF({player_id_cell} = "","",VLOOKUP({team_id_cell}, Teams!$D$2:$AE$1000, 28, FALSE))')
            ws_team.cell(row=row, column=col_max + 17,
                         value=f'=H{row}')
            ws_team.cell(row=row, column=col_max + 18,
                         value=f'=IF({player_id_cell} = "","",(N{row} + P{row} + R{row} + T{row} + V{row})/5)')

        ws_team.conditional_formatting.add(
            "M2:X1000",
            FormulaRule(formula=["IF( N2 > 0 ,OR(N2<2, M2 <2), IF(M2>0,M2<2))"], fill=FDR1)    
        )
        
        ws_team.conditional_formatting.add(
            "M2:X1000",
            FormulaRule(formula=["IF( N2 > 0 ,OR(N2<3, M2 <3), IF(M2>0,M2<3))"], fill=FDR2)   
        )

        ws_team.conditional_formatting.add(
            "M2:X1000",
            FormulaRule(formula=["IF( N2 > 0 ,OR(N2<4, M2 <4), IF(M2>0,M2<4))"], fill=FDR3)   
        )

        ws_team.conditional_formatting.add(
            "M2:X1000",
            FormulaRule(formula=["IF( N2 > 0 ,OR(N2<5, M2 <5), IF(M2>0,M2<5))"], fill=FDR4)
        )
        ws_team.conditional_formatting.add(
            "M2:X1000",
            FormulaRule(formula=["OR(N2=5, M2 =5)"], fill=FDR5)
            
        )

        
        #team_lookup = {t["short_name"]: t["id"] for t in teams}
        
        team_fixtures = {t["id"]: [] for t in teams}

        for f in fixtures:
            if f["event"] is None:
                continue
            if f["event"] < GAMEWEEK + 1 or f["event"] >= GAMEWEEK + 6:
                continue

            home = teams[f["team_h"] - 1]["short_name"]
            away = teams[f["team_a"] - 1]["short_name"]

            team_fixtures[f["team_h"]].append((f"{away} (H)", f["team_h_difficulty"]))
            team_fixtures[f["team_a"]].append((f"{home} (A)", f["team_a_difficulty"]))

        ws_teams = wb["Teams"]

        # Find where to start writing new columns
        start_col = ws_teams.max_column + 1

        # Find which columns to write fixtures into (append after last col)
        headers = []
        for i in range(5):
            headers.append(f"GW {i+1+GAMEWEEK}")
            headers.append(f"FDR GW{i+1+GAMEWEEK}")

        
        for j, h in enumerate(headers, start=start_col):
            ws_teams.cell(row=1, column=j, value=h)

        # --- Add fixtures row by row ---
        for row in range(2, ws_teams.max_row + 1):
            team_name = ws_teams.cell(row=row, column=10).value  # assumes Team is in col 10
            if team_name not in team_lookup:
                continue
    
            team_id = team_lookup[team_name]
            next5 = team_fixtures.get(team_id, [])[:5]  # take only 5
    
            # Write fixture + difficulty
            col = start_col
            for fixture, difficulty in next5:
                ws_teams.cell(row=row, column=col, value=fixture)
                ws_teams.cell(row=row, column=col+1, value=difficulty)
                col += 2
            ws_teams.cell(row=row, column=col,
                         value=f'=J{row}')
            ws_teams.cell(row=row, column=col+1,
                         value=f'=((W{row} + Y{row} + AA{row} + AC{row} + AE{row})/5)')
            
        ws_teams.conditional_formatting.add(
            "V2:AG1000",
            FormulaRule(formula=["IF( W2 > 0 ,OR(W2<2, V2 <2), IF(V2>0,V2<2))"], fill=FDR1)    
        )
        
        ws_teams.conditional_formatting.add(
            "V2:AG1000",
            FormulaRule(formula=["IF( W2 > 0 ,OR(W2<3, V2 <3), IF(V2>0,V2<3))"], fill=FDR2)    
        )

        ws_teams.conditional_formatting.add(
            "V2:AG1000",
            FormulaRule(formula=["IF( W2 > 0 ,OR(W2<4, V2 <4), IF(V2>0,V2<4))"], fill=FDR3)    
        )

        ws_teams.conditional_formatting.add(
            "V2:AG1000",
            FormulaRule(formula=["IF( W2 > 0 ,OR(W2<5, V2 <5), IF(V2>0,V2<5))"], fill=FDR4)    
        )
        ws_teams.conditional_formatting.add(
            "V2:AG1000",
            FormulaRule(formula=["OR(W2=5, V2 =5)"], fill=FDR5)
            
        )
        

    Save_Path = os.path.join(Save_Location, filename)
    wb.save(Save_Path)
    print(f"✅ Data exported to {filename} with Lookup sheet and VLOOKUP formulas")

def get_bootstrap_data():
    """Fetch general FPL metadata: players, teams, positions."""
    url = BASE_URL + "bootstrap-static/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_fixtures(gw):
    """get gameweek fixtures"""
    url = BASE_URL + f"fixtures/"
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



def Mini_league_standings(league_id, k_factor=10, start_elo=1500):
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

    combined_histories = combined_histories.merge(avg_df, on="event", how="left")

    # --- Add Elo ratings ---
    combined_histories = combined_histories.sort_values(["event", "manager"])
    combined_histories["mini league rank"] = np.nan
    combined_histories["week rank"] = np.nan
    combined_histories["movement"] = np.nan
    combined_histories["wins"] = np.nan
    combined_histories["draws"] = np.nan
    combined_histories["losses"] = np.nan
    combined_histories["elo"] = np.nan
    

    # Initialize each manager's Elo
    elo_ratings = {m["player_name"]: start_elo for m in managers}
    

    # Loop week by week
    for gw, week_df in combined_histories.groupby("event"):
        avg_score = week_df["avg_points"].iloc[0]  # same for all rows in that GW
        scores = dict(zip(week_df["manager"], week_df["points"]))
        total_scores = dict(zip(week_df["manager"], week_df["total_points"]))

        # Sort the list and assign ranks
        sorted_ws = sorted(scores)
        ranked_ws = [sorted_ws.index(x) + 1 for x in scores]
        for idx, row in week_df.iterrows():
            manager = row["manager"]
            score = row["points"]
            total_score = row["total_points"]
            

            # --- Count wins/draws/losses vs all other managers in this GW ---
            wins = sum(score > s for m, s in scores.items() if m != manager)
            draws = sum(score == s for m, s in scores.items() if m != manager)
            losses = sum(score < s for m, s in scores.items() if m != manager)

            players = wins + draws + losses

            # Sort the list and assign ranks
            #combined_histories.at[idx, "mini league rank"] = ranked_ts[idx]

            # Sort the list and assign ranks
            #sorted_ws = sorted(score)
            #combined_histories.at[idx, "week rank"] = [sorted_ts.index(x) + 1 for x in score]


            combined_histories.at[idx, "wins"] = wins
            combined_histories.at[idx, "draws"] = draws
            combined_histories.at[idx, "losses"] = losses

            # Simple Elo: compare manager score vs league average
            #expected = 1 / (1 + 10 ** ((avg_score - elo_ratings[manager]) / 400))
            #actual = 1 if score >= avg_score else 0  # win if above avg
            
            #elo_change = k_factor * (actual - expected)
            expected_wins = (wins + draws + losses) * elo_ratings[manager]/3000
            elo_ratings[manager] += k_factor * ((wins + draws/2)- expected_wins)
            combined_histories.at[idx, "elo"] = elo_ratings[manager]
    
                    
    return combined_histories


def add_week0_points(df, start_points=0):
    """
    Add week 0 (initial points) for all managers.
    df: DataFrame with columns ['event','total_points','manager']
    """
    managers = df["manager"].unique()
    week0 = pd.DataFrame({
        "event": 0,
        "total_points": start_points,
        "manager": managers
    })
    return pd.concat([week0, df], ignore_index=True).sort_values(["manager", "event"])

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
        df = df.sort_values("event") #sort by gameweek
        # Plot step line and capture the color
        line, = plt.step(df["event"], df["total_points"], where="pre", label=None, alpha=0.9)
        color = line.get_color()

    # Add marker at last point
        x_last = df["event"].iloc[-1]
        y_last = df["total_points"].iloc[-1]
        plt.scatter(x_last, y_last, s=30, color=color)
        plt.text(x_last + 0.2, y_last, f"{manager} ({int(y_last)})", fontsize=8, va="center", color=color)
    # Add manager label + final Elo score in matching color

    plt.title("League Total Points Over Time", fontsize=16, weight="bold")
    plt.xlabel("Gameweek")
    plt.ylabel("Total Points")
    plt.axhline(y=0, xmin=0, xmax=1, c = 'r')
    plt.grid(True, alpha=0.3)
    plt.xticks(np.arange(0, 5, step=1))
    plt.tight_layout()
    plt.show()

def add_week0_elo(df, start_elo=1500):
    """
    Add week 0 (initial Elo) for all managers.
    df: DataFrame with columns ['event','elo','manager']
    """
    managers = df["manager"].unique()
    week0 = pd.DataFrame({
        "event": 0,
        "elo": start_elo,
        "manager": managers
    })
    return pd.concat([week0, df], ignore_index=True).sort_values(["manager", "event"])

def plot_league_elo(histories_df):
    """Plot league elo"""

    plt.figure(figsize=(16,8))

    # Group by manager and plot each line
    for manager, df in histories_df.groupby("manager"):
        df = df.sort_values("event") #sort by gameweek
        # Plot step line and capture the color
        line, = plt.step(df["event"], df["elo"], where="pre", label=None, alpha=0.9)
        color = line.get_color()

    # Add marker at last point
        x_last = df["event"].iloc[-1]
        y_last = df["elo"].iloc[-1]
        plt.scatter(x_last, y_last, s=30, color=color)
        plt.text(x_last + 0.1, y_last, f"{manager} ({int(y_last)})", fontsize=8, va="center", color=color)
    # Add manager label + final Elo score in matching color

       
        
    plt.title("League ELO rating Over Time", fontsize=16, weight="bold")
    plt.xlabel("Gameweek")
    plt.ylabel("ELO rating")
    plt.axhline(y=1500, xmin=0, xmax=1, c = 'r')
    plt.grid(True, alpha=0.3)
    plt.xticks(np.arange(0, 5, step=1))
    #plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=8)
    plt.tight_layout()
    plt.show()
        
if __name__ == "__main__":
    EMAIL = input("your_email_here: ")
    PASSWORD = input("your_password_here: ")
    TEAM_ID = 1533428  # Replace with your FPL team ID (find in URL of your team page)
    GAMEWEEK = 2       # Change to current gameweek
    FUTURE_FIX = 3         # number of future fixtures shown
    filename="fpl_data.xlsx"
    # Login
    session = login_fpl(EMAIL, PASSWORD)

    # Fetch player/teams metadata
    bootstrap = get_bootstrap_data()

    players_df = pd.DataFrame(bootstrap["elements"])
    teams_df = pd.DataFrame(bootstrap["teams"])
    positions_df = pd.DataFrame(bootstrap["element_types"])
    events = bootstrap["events"]
    avg_df = pd.DataFrame([
        {"event": event["id"], "avg_points": event["average_entry_score"]}
        for event in events
    ])

    fixtures = get_fixtures(GAMEWEEK)
    for f in fixtures:
        if f['event'] >= GAMEWEEK +1| f['event'] < GAMEWEEK + 6:
            print(
                f"GW{f['event']}: Team {f['team_h']} vs Team {f['team_a']} | "
            f"H difficulty: {f['team_h_difficulty']}, A difficulty: {f['team_a_difficulty']}"
        )
        

    #fixtures
    
    
    
        

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

    
    watchlist = get_watchlist(filename)
    
    
    # 6. Export everything to Excel
    export_to_excel_with_lookup({
        "My Team": picks,
        "Team History": history_df,
        "Classic Leagues": classic_leagues,
        "Ale League Histories": combined_histories_ale,
        "OBC League Histories": combined_histories_OBC,
        "Live Points": live_with_names,
        "Teams": teams_df
    }, player_lookup, teams_df, fixtures, filename)

    # 7. Plot league points
    #plot_league_histories(combined_histories_ale)
    #combined_histories_ale = add_week0_elo(combined_histories_ale, start_elo=1500)
    #plot_league_elo(combined_histories_ale)

    combined_histories_OBC = add_week0_points(combined_histories_OBC, start_points=0)
    plot_league_histories(combined_histories_OBC)

    
