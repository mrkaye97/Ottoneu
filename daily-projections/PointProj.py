import requests
import lxml.html as lh
import numpy as np
import pandas as pd
import io
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import sys
from selenium import webdriver


driver = webdriver.Chrome()

hitters = range(4, 15)
pitchers = range(3, 13)
p_res = pd.DataFrame(columns=['ID', 'Name', 'Points', 'Innings', 'P/IP'])
h_res = pd.DataFrame(columns=['ID', 'Name', 'Points'])
p_na = pd.DataFrame(columns=['ID', 'Name'])
h_na = pd.DataFrame(columns=['ID', 'Name'])

roster_url = "https://ottoneu.fangraphs.com/1139/rosterexport"
f = requests.get(roster_url)

# get list of players on my team
team = (pd
        .read_csv(io.BytesIO(f.content))
        .rename(index=str, columns={'Team Name': 'TeamName',
                                    'FG MajorLeagueID': 'FGID',
                                    'Position(s)': 'Position'})
        .query("TeamName == 'C.C. Sabathtub'")
        .dropna(axis=0)
        .assign(FGID=lambda x: x.FGID.apply(int))
        .filter(['FGID', 'Name', 'Position'])
        )

# loop over players
# load each fangraphs page

hpoints = pd.DataFrame(
    {
        'stat': ['AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'CS', 'SB'],
        'pts': [-1, 5.6, 2.9, 5.7, 9.4, 3, 3, 1.9, -2.8]
    }
)

ppoints = pd.DataFrame(
    {
        'stat': ['IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HOLDS'],
        'pts': [7.4, 2.0, -2.6, -3, -3, -12.3, 5, 4]
    }
)

# team = team.query("FGID==12970")

for temp in team.itertuples():

    tries = 0
    while tries < 5:

        try:
            tries += 1
            driver.implicitly_wait(5)
            driver.get("https://www.fangraphs.com/statss.aspx?playerid={pid}".format(pid=temp.FGID))
            driver.implicitly_wait(5)

            tab = driver.find_element_by_xpath('//*[@id="daily-projections"]/div[3]/div/div/div/div[1]').text.split("\n")[:2]

            proj = (
                pd.DataFrame.from_records({'stat': pd.Series(tab[0].split(" ")[2:]),
                                           'val': pd.Series(tab[1].split(" ")[4:])})
                    .assign(val=lambda x: pd.to_numeric(x.val, errors='coerce'))
            )

            if temp.Position in ["SP", "RP", "SP/RP"]:

                daypts = (
                    pd.merge(proj, ppoints, how='inner', on='stat')
                        .assign(prod=lambda x: x.val * x.pts)
                        .sum()
                )['prod']

                ip = proj.query("stat=='IP'").iloc[:, 1].values[0]

                curr = {'ID': temp.FGID,
                        'Name': temp.Name,
                        'Innings': ip,
                        'Points': daypts,
                        'P/IP': daypts / ip
                        }

                p_res = p_res.append(curr, ignore_index=True)

            else:

                daypts = (
                    pd.merge(proj, hpoints, how='inner', on='stat')
                        .assign(prod=lambda x: x.val * x.pts)
                        .sum()
                )['prod']

                curr = {'ID': temp.FGID,
                        'Name': temp.Name,
                        'Points': daypts - 4.5}

                h_res = h_res.append(curr, ignore_index=True)

            tries = 5

        except:
            if tries < 5:
                pass
            else:
                if temp.Position in ["SP", "RP", "SP/RP"]:
                    curr = {'ID': temp.FGID,
                            'Name': temp.Name,
                            }

                    p_na = p_na.append(curr, ignore_index=True)

                else:
                    curr = {'ID': temp.FGID,
                            'Name': temp.Name,
                            }

                    h_na = h_na.append(curr, ignore_index=True)

h_res = (h_res
         .sort_values(by='Points', ascending=False)
         .reset_index()
         .filter(['Name', 'Points'])
         )
p_res = (p_res
         .sort_values(by='P/IP', ascending=False)
         .reset_index()
         .filter(['Name', 'Points', 'Innings', 'P/IP'])
         )

email = "Hitter Projections: {h} <br> " \
        "Pitcher Projections: {p} <br> <br>" \
        "Hitters Missing Data: {hna} <br>" \
        "Pitchers Missing Data: {pna}"

email = email.format(h=h_res.to_html(index=False),
                     p=p_res.to_html(index=False),
                     hna=h_na.to_html(index=False),
                     pna=p_na.to_html(index=False))

date = datetime.datetime.now().date()

print(h_res)
print(p_res)

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


driver.quit()
