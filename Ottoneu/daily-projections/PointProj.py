import requests
import lxml.html as lh
import numpy as np
import pandas as pd
import io
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

hitters = range(4, 15)
pitchers = range(3, 13)
p_res = pd.DataFrame(columns=['ID', 'Name', 'Points', 'Innings', 'P/IP'])
h_res = pd.DataFrame(columns=['ID', 'Name', 'Points'])
p_na = pd.DataFrame(columns=['ID', 'Name'])
h_na = pd.DataFrame(columns=['ID', 'Name'])

roster_url = "https://ottoneu.fangraphs.com/1087/rosterexport"
f = requests.get(roster_url)

# get list of players on my team
team = (pd
        .read_csv(io.BytesIO(f.content))
        .rename(index=str, columns={'Team Name': 'TeamName',
                                    'FG MajorLeagueID': 'FGID',
                                    'Position(s)': 'Position'})
        .query("TeamName.str.contains('Sabathtub')")
        .dropna(axis=0)
        .assign(FGID=lambda x: x.FGID.apply(int))
        .filter(['FGID', 'Name', 'Position'])
        )

# loop over players
# load each fangraphs page
for temp in team.itertuples():
    url = "https://www.fangraphs.com/statss.aspx?playerid={pid}".format(pid=temp.FGID)

    page = requests.get(url)
    doc = lh.fromstring(page.content)

    try:
        if temp.Position in ["SP", "RP", "SP/RP"]:
            tr_elements = [doc.xpath('//*[@id="SeasonStats1_dgSeason24_ctl00__0"]/td[{i}]'.format(i=i))
                           for i in pitchers]

            pts = np.array([0, 7.4, 0, -2.6, 0, 0, 0, -12.3, -3.0, 2.0])

            proj = np.array([float(t[0].text_content())
                             for t in tr_elements])

            curr = {'ID': temp.FGID,
                    'Name': temp.Name,
                    'Innings': proj[1],
                    'Points': np.dot(pts, proj),
                    'P/IP': np.dot(pts, proj) / proj[1]
                    }

            p_res = p_res.append(curr, ignore_index=True)

        else:
            tr_elements = [doc.xpath('//*[@id="SeasonStats1_dgSeason24_ctl00__0"]/td[{i}]'.format(i=i))
                           for i in hitters]

            pts = np.array([5.6, 0, 2.9, 5.7, 9.4, 0, 0, 1.9, -2.8, 3.0, 0])
            proj = np.array([float(t[0].text_content())
                             for t in tr_elements])

            curr = {'ID': temp.FGID,
                    'Name': temp.Name,
                    'Points': np.dot(pts, proj) - 4.5}

            h_res = h_res.append(curr, ignore_index=True)

    except:
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

sender_email = "mrkaye97@gmail.com"
receiver_email = ["mrkaye97@gmail.com", "masonpropper@gmail.com"]
password = '1997GOOGLEmrk!'

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
