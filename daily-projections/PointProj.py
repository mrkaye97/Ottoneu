import requests
import pandas as pd
import numpy as np
import io
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import sys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


roster_url = "https://ottoneu.fangraphs.com/1139/rosterexport"
f = requests.get(roster_url)

mlb_team_map = pd.DataFrame({
    'abbr': [
        'NYY', 'TBR', 'BOS', 'BAL', 'TOR',   ## AL East
        'MIN', 'DET', 'KCR', 'CLE', 'CHW',   ## AL Central
        'HOU', 'OAK', 'LAA', 'SEA', 'TEX',   ## AL West
        'NYM', 'PHI', 'WSN', 'ATL', 'MIA',   ## NL East
        'CIN', 'MIL', 'STL', 'CHC', 'PIT',   ## NL Central
        'COL', 'ARI', 'LAD', 'SDP', 'SFG'    ## NL West
    ],
    'Team': [
        'Yankees', 'Rays', 'Red Sox', 'Orioles', 'Blue Jays',
        'Twins', 'Tigers', 'Royals', 'Indians', 'White Sox',
        'Astros', 'Athletics', 'Angels', 'Mariners', 'Rangers',
        'Mets', 'Phillies', 'Nationals', 'Braves', 'Marlins',
        'Reds', 'Brewers', 'Cardinals', 'Cubs', 'Pirates',
        'Rockies', 'Diamondbacks', 'Dodgers', 'Padres', 'Giants'
    ]
}
)
# get list of players on my team
team = (pd
        .read_csv(io.BytesIO(f.content))
        .rename(index=str, columns={'Team Name': 'TeamName',
                                    'FG MajorLeagueID': 'FGID',
                                    'Position(s)': 'Position',
                                    'MLB Team': 'abbr'})
        .query("TeamName == 'C.C. Sabathtub'")
        .dropna(axis=0)
        .merge(mlb_team_map, on='abbr')
        .filter(items=['Name', 'Team'])
        .replace({'Name': {'Nick Castellanos': 'Nicholas Castellanos',
                           }})
        )

# loop over players
# load each fangraphs page

hpoints = pd.DataFrame(
    {
        'stat': ['AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'CS', 'SB'],
        'pts': [-1, 5.6, 2.9, 5.7, 9.4, 3, 3, -2.8, 1.9]
    }
)

ppoints = pd.DataFrame(
    {
        'stat': ['IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HOLDS'],
        'pts': [7.4, 2.0, -2.6, -3, -3, -12.3, 5, 4]
    }
)


def get_hitter_proj():
    driver = webdriver.Chrome()

    driver.get('https://www.fangraphs.com/dailyprojections.aspx?pos=all&stats=bat&type=sabersim&team=0&lg=all&players=0')

    numrows = int(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[5]/strong[1]'))).text)
  #  numrows = int(driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[5]/strong[1]').text)

    driver.refresh()
    driver.implicitly_wait(10)
    players_per_page_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[4]/div/span/button')))
   # players_per_page_dropdown = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[4]/div/span/button')
    players_per_page_dropdown.click()
    driver.implicitly_wait(10)
    ppp1000 = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[1]/div/div/ul/li[7]')))
   # ppp1000 = driver.find_element_by_xpath('/html/body/form/div[1]/div/div/ul/li[7]')
    ppp1000.click()
    driver.implicitly_wait(10)
    colnames = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/thead'))).text.split(" ")
  #  colnames = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/thead').text.split(" ")
    numcols = len(colnames)

    mat = np.array(['']*(numrows*numcols), dtype=object)

    for row in range(1, numrows+1):
        for col in range(1, (numcols+1)):
            cell = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tbody/tr[' + str(row) + ']/td[' + str(col) + ']').text
            mat[(row - 1) * (numcols) + (col-1)] = cell

        print(str(round(100 * row / numrows)) + "% Done")

    hitters = (
        pd.DataFrame(mat.reshape((numrows, numcols)), columns=colnames)
        .assign(AB=lambda x: x.PA.astype(float) - x.BB.astype(float))
        .melt(id_vars=['Name', 'Team', 'Game', 'Pos'], var_name = 'stat')
        .merge(hpoints, on = 'stat', how = 'inner')
        .astype({'value': float,
                 'pts': float}, errors='ignore')
        .assign(Points=lambda x: x.pts * x.value)
        .groupby(['Name', 'Team'])
        .sum()
        .filter(items=['Points'])
        .reset_index()
        .sort_values('Points', ascending=False)
        .merge(team, on=['Name', 'Team'], how = 'inner')
    )

    print(hitters.head())

    driver.quit()
    return hitters


def get_pitcher_proj():
    driver = webdriver.Chrome()

    driver.get('https://www.fangraphs.com/dailyprojections.aspx?pos=all&stats=pit&type=sabersim&team=0&lg=all&players=0')

    numrows = int(WebDriverWait(driver, 3).until(EC.presence_of_element_located(
        (By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[5]/strong[1]'))).text)
    #  numrows = int(driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[5]/strong[1]').text)

    driver.refresh()
    driver.implicitly_wait(10)
    players_per_page_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located(
        (By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[4]/div/span/button')))
    # players_per_page_dropdown = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tfoot/tr/td/div/div[4]/div/span/button')
    players_per_page_dropdown.click()
    driver.implicitly_wait(10)
    ppp1000 = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/form/div[1]/div/div/ul/li[7]')))
    # ppp1000 = driver.find_element_by_xpath('/html/body/form/div[1]/div/div/ul/li[7]')
    ppp1000.click()
    driver.implicitly_wait(10)
    colnames = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/div[2]/span/div/table/thead'))).text.split(
        " ")
    #  colnames = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/thead').text.split(" ")
    numcols = len(colnames)

    mat = np.array([''] * (numrows * numcols), dtype=object)

    for row in range(1, numrows+1):
        for col in range(1, (numcols+1)):
            cell = driver.find_element_by_xpath('/html/body/form/div[3]/div[2]/span/div/table/tbody/tr[' + str(row) + ']/td[' + str(col) + ']').text
            mat[(row - 1) * (numcols) + (col-1)] = cell

        print(str(round(100 * row / numrows)) + "% Done")

    ip = (
        pd.DataFrame(mat.reshape((numrows, numcols)), columns=colnames)
        .filter(items=['Name', 'Team', 'IP'])
    )
    pitchers = (
        pd.DataFrame(mat.reshape((numrows, numcols)), columns=colnames)
        .melt(id_vars=['Name', 'Team', 'Game'], var_name = 'stat')
        .merge(ppoints, on = 'stat', how = 'inner')
        .astype({'value': float,
                 'pts': float}, errors='ignore')
        .assign(Points=lambda x: x.pts * x.value)
        .groupby(['Name', 'Team'])
        .sum()
        .filter(items=['Points'])
        .reset_index()
        .sort_values('Points', ascending=False)
        .merge(team, on=['Name', 'Team'], how = 'inner')
        .merge(ip, how='inner', on=['Name', 'Team'])
        .assign(PIP=lambda x: x.Points / x.IP.astype(float))
        .rename(columns={'PIP': 'P/IP'})
    )

    print(pitchers.head())
    return pitchers


hitters = get_hitter_proj()
pitchers = get_pitcher_proj()

withproj = (
    (pitchers.filter(items =['Name']))
    .append([(hitters.filter(items=['Name']))])
)

noproj = team[~team.Name.isin(withproj.Name)]


email = "Hitter Projections: {h} <br> " \
        "Pitcher Projections: {p} <br> <br>" \
        "Players Missing Data: {na}"

email = email.format(h=hitters.to_html(index=False),
                     p=pitchers.to_html(index=False),
                     na=noproj.to_html(index=False))

date = datetime.datetime.now().date()

sender_email = "mrkaye97@gmail.com"
receiver_email = ["mrkaye97@gmail.com", "masonpropper@gmail.com"]
password = str(sys.argv[1])

message = MIMEMultipart("alternative")
message["Subject"] = 'Projections for ' + str(date)
message["From"] = sender_email
message["To"] = ", ".join(receiver_email)

# Create the plain-text and HTML version of your message
text = 'See table:'

# Turn these into plain/html MIMEText objects
part1 = MIMEText(text, "plain")
part2 = MIMEText(email, "html")

# Add HTML/plain-text parts to MIMEMultipart message
# The email client will try to render the last part first
message.attach(part1)
message.attach(part2)

# Create secure connection with server and send email
context = ssl.create_default_context()

with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(
        sender_email, receiver_email, message.as_string()
    )

