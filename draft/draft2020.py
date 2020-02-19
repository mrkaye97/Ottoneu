import pandas as pd
import os
import numpy as np

ROOT_DIR = '/users/matt/Documents/GitHub/Ottoneu'


def point_proj(cols_to_use, points, projlist, multiplier):

    pts = pd.DataFrame({'stat': cols_to_use[2:],
                        'points': points})

    df = pd.DataFrame(columns=cols_to_use)
    for d in projlist:
        temp = pd.read_csv(d, dtype={'playerid': 'str'})
        df = pd.concat([df, temp], axis=0, sort=False)

    df = (df
          .filter(cols_to_use)
          .set_index(['playerid', 'Name'])
          .apply(pd.to_numeric, errors = 'coerce')
          .reset_index(drop=False)
          .groupby(['playerid', 'Name'])
          .mean()
          .reset_index(drop=False)
          .filter(cols_to_use)
          .melt(id_vars=['Name', 'playerid'], value_name='counts', var_name='stat')
          .astype({'counts': 'float'})
          )

    df = (pd
     .merge(df, pts, on='stat')
     .assign(tot=lambda x: x.counts * x.points * multiplier)
     .filter(['Name', 'playerid', 'tot'])
     .groupby(['Name', 'playerid'])
     .sum()
     .sort_values('tot', ascending=False)
     .round({'tot': 2})
     .reset_index(drop=False)
     )

    return df


def join_pos(df):
    pos = (pd
           .read_csv(os.path.join(ROOT_DIR, 'data', 'fielding.csv'))
           .filter(items=['playerid', 'Pos', 'Inn'])
           )

    elig = pd.read_csv(os.path.join(ROOT_DIR, 'data', 'eligibility.csv'))

    pos = (
        pd
            .merge(pos, elig, on=['playerid', 'Inn'])
            .sort_values(by='playerid')
            .query('G > 10 or GS > 5')
            .filter(items=['playerid', 'Pos'])
    )

    pos['playerid'] = pos['playerid'].astype(str)

    steamer = (
        pd
            .read_csv(os.path.join(ROOT_DIR, 'data', 'SteamerPitchers.csv'))
            .assign(Pos=lambda x: np.where(x.GS >= 5, 'SP', 'RP'))
            .filter(['playerid', 'Pos'])
    )

    rec = {}
    for ix, y in steamer.iterrows():
        rec[y.playerid] = y.Pos

    for i, d in pos.iterrows():
        if d.playerid in list(rec.keys()):
            d.Pos = rec[d.playerid]

    temp = (
        pd
            .merge(df, pos, on='playerid')
            .replace({'Pos': {'RF': 'OF', 'LF': 'OF', 'CF': 'OF'}})
            .drop_duplicates()
    )

    return temp

def get_rep_lvl(df):
    # multiplied pitcher rep lvl by 5/6 to account for decrease in the innings cap from 1500 to 1250
    rep_lvl = pd.DataFrame.from_records(
        {'Pos': ['C', '1B', '2B', 'SS', '3B', 'OF', 'SP', 'RP'], 'Lvl': [35, 27, 30, 32, 18, 84, 90, 61]})


    res = pd.DataFrame(columns=['Name', 'playerid', 'tot', 'Pos'])
    for i, d in rep_lvl.iterrows():
        res = res.append(df.query('Pos == @d.Pos').iloc[d.Lvl,])

    temp = (
        df
            .merge(res, on='Pos')
            .rename(columns={'Name_x': 'Name',
                             'playerid_x': 'playerid',
                             'tot_x': 'tot',
                             'Pos_x': 'Pos',
                             'tot_y': 'rep'})
            .filter(items=['Name', 'playerid', 'tot', 'Pos', 'rep'])
            .assign(PAR=lambda x: x.tot - x.rep)
            .assign(p=lambda x: x.PAR * 4500 / 39680)
            .sort_values('p', ascending=False)
            .round(3)
    )

    return temp


def discount():

    hlist = [
        'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/Zips21Hitters.csv'
        ]

    plist = [
        'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/Zips21Pitchers.csv'
    ]

    temp21 = pd.concat([
        point_proj(cols_to_use=['Name', 'playerid', 'AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'SB', 'CS'],
                   points=[-1.0, 5.6, 2.9, 5.7, 9.4, 3.0, 3.0, 1.9, -2.8],
                   projlist=hlist,
                   multiplier=.5),
        point_proj(cols_to_use=['Name', 'playerid', 'IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HD'],
                   points=[7.4, 2.0, -2.6, -3.0, -3.0, -12.3, 5.0, 4.0],
                   projlist=plist,
                   multiplier=.5)
    ], axis=0, sort=False)

    temp21 = join_pos(temp21)
    temp21 = get_rep_lvl(temp21)

    hlist = [
        'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/Zips22Hitters.csv'
    ]

    plist = [
        'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/Zips22Pitchers.csv'
    ]

    temp22 = pd.concat([
        point_proj(cols_to_use=['Name', 'playerid', 'AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'SB', 'CS'],
                   points=[-1.0, 5.6, 2.9, 5.7, 9.4, 3.0, 3.0, 1.9, -2.8],
                   projlist=hlist,
                   multiplier=.25),
        point_proj(cols_to_use=['Name', 'playerid', 'IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HD'],
                   points=[7.4, 2.0, -2.6, -3.0, -3.0, -12.3, 5.0, 4.0],
                   projlist=plist,
                   multiplier=.25)
    ], axis=0, sort=False)

    temp22 = join_pos(temp22)
    temp22 = get_rep_lvl(temp22)

    temp21 = temp21.filter(['playerid', 'p']).rename(columns={'p': 'p21'})
    temp22 = temp22.filter(['playerid', 'p']).rename(columns={'p': 'p22'})

    return (temp21, temp22)

hlist = [
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/DepthChartsHitters.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/SteamerHitters.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/TBHitters.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ZipsHitters.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ATCHitters.csv'
]

plist = [
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/DepthChartsPitchers.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/SteamerPitchers.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/TBPitchers.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ZipsPitchers.csv',
    'https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ATCPitchers.csv'
]


base_proj = pd.concat([
    point_proj(cols_to_use=['Name', 'playerid', 'AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'SB', 'CS'],
           points=[-1.0, 5.6, 2.9, 5.7, 9.4, 3.0, 3.0, 1.9, -2.8],
           projlist=hlist,
           multiplier=1),
    point_proj(cols_to_use=['Name', 'playerid', 'IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HD'],
           points=[7.4, 2.0, -2.6, -3.0, -3.0, -12.3, 5.0, 4.0],
           projlist=plist,
           multiplier=1)
    ], axis = 0, sort = False)

proj_w_pos = join_pos(base_proj)
proj_w_rep_lvl = get_rep_lvl(proj_w_pos)

twentyone, twentytwo = discount()

(
    proj_w_rep_lvl
        .merge(twentyone, on='playerid')
        .merge(twentytwo, on='playerid')
        .assign(pdisc = lambda x: (x.p + x.p21 + x.p22) / 1.75)
        .sort_values('pdisc', ascending=False)
        .groupby('playerid')
        .head(1)
        .filter(['Name', 'tot', 'Pos', 'pdisc'])
        .rename(columns={'pdisc': 'Discounted Auction Value',
                         'tot': 'Total Projected 2020 Points',
                         'Pos': 'Position'})
        .to_csv(os.path.join(ROOT_DIR, 'draft', 'projections.csv'), index=False)
      )



