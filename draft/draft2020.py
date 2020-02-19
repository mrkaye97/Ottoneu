import pandas as pd
import os
import numpy as np
from pulp import *

ROOT_DIR = '/users/matt/Documents/GitHub/Ottoneu'


def point_proj(cols_to_use, points, depth, steamer, tb, zips, atc, out):
    depth = pd.read_csv(depth, dtype={'playerid': 'str'})
    steamer = pd.read_csv(steamer, dtype={'playerid': 'str'})
    tb = pd.read_csv(tb, dtype={'playerid': 'str'})
    zips = pd.read_csv(zips, dtype={'playerid': 'str'})
    atc = pd.read_csv(atc, dtype={'playerid': 'str'})


    df = (pd
          .concat([depth, steamer, tb, zips, atc], axis=0, sort=False)
          .groupby(['playerid', 'Name'])
          .mean()
          .reset_index(drop=False)
          .filter(cols_to_use)
          .melt(id_vars=['Name', 'playerid'], value_name='counts', var_name='stat')
          .astype({'counts': 'float'})
          )

    pts = pd.DataFrame({'stat': cols_to_use[2:],
                            'points': points})

    (pd
     .merge(df, pts, on='stat')
     .assign(tot=lambda x: x.counts * x.points)
     .filter(['Name', 'playerid', 'tot'])
     .groupby(['Name', 'playerid'])
     .sum()
     .sort_values('tot', ascending=False)
     .round({'tot': 2})
     .to_csv(os.path.join(ROOT_DIR, 'draft', out))
     )

def join_pos():

    pos =  (pd
            .read_csv(os.path.join(ROOT_DIR, 'data', 'fielding.csv'))
            .filter(items=['playerid', 'Pos', 'Inn'])
            )

    elig = pd.read_csv(os.path.join(ROOT_DIR, 'data', 'eligibility.csv'))

    pos = (
        pd
            .merge(pos, elig, on = ['playerid', 'Inn'])
            .sort_values(by='playerid')
            .query('G > 10 or GS > 5')
            .filter(items=['playerid', 'Pos'])
    )

    pos['playerid'] = pos['playerid'].astype(str)

    h = pd.read_csv(os.path.join(ROOT_DIR, 'draft', 'hitters.csv'))
    p = pd.read_csv(os.path.join(ROOT_DIR, 'draft', 'pitchers.csv'))

    steamer = (
        pd
        .read_csv(os.path.join(ROOT_DIR, 'data', 'SteamerPitchers.csv'))
        .assign(Pos=lambda x: np.where(x.GS >= 5, 'SP', 'RP'))
        .filter(['playerid', 'Pos'])
               )

    rec = {}
    for ix,y in steamer.iterrows():
        rec[y.playerid] = y.Pos

    for i, d in pos.iterrows():
        if d.playerid in list(rec.keys()):
            d.Pos = rec[d.playerid]

    proj = pd.concat([h, p], axis=0)

    (
        pd
        .merge(proj, pos, on='playerid')
        .replace({'Pos' : {'RF' : 'OF', 'LF' : 'OF', 'CF' : 'OF' }})
        .drop_duplicates()
        .to_csv(os.path.join(ROOT_DIR, 'draft', 'projections.csv'), index=False)
      )

def get_rep_lvl():

    rep_lvl = pd.DataFrame.from_records({'Pos': ['C', '1B', '2B', 'SS', '3B', 'OF', 'SP', 'RP'], 'Lvl': [35, 27, 30, 32, 18, 84, 90, 61]})

    df = pd.read_csv(os.path.join(ROOT_DIR, 'draft', 'projections.csv'))

    res = pd.DataFrame(columns=['Name', 'playerid', 'tot', 'Pos'])
    for i, d in rep_lvl.iterrows():
        res = res.append(df.query('Pos == @d.Pos').iloc[d.Lvl,])

    (
        pd
        .read_csv(os.path.join(ROOT_DIR, 'draft', 'projections.csv'))
        .merge(res, on='Pos')
        .rename(columns={'Name_x': 'Name',
                 'playerid_x': 'playerid',
                 'tot_x': 'tot',
                 'Pos_x': 'Pos',
                 'tot_y': 'rep'})
        .filter(items=['Name', 'playerid', 'tot', 'Pos', 'rep'])
        .assign(PAR=lambda x: x.tot - x.rep)
        .assign(p = lambda x: x.PAR * 4500 / 39680)
        .sort_values('p', ascending=False)
        .round(3)
        .to_csv(os.path.join(ROOT_DIR, 'draft', 'projections.csv'), index=False)
    )


point_proj(cols_to_use = ['Name', 'playerid', 'AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'SB', 'CS'],
      points = [-1.0, 5.6, 2.9, 5.7, 9.4, 3.0, 3.0, 1.9, -2.8],
      depth='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/DepthChartsHitters.csv',
      steamer='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/SteamerHitters.csv',
      tb='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/TBHitters.csv',
      zips='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ZipsHitters.csv',
      atc='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ATCHitters.csv',
      out='hitters.csv')
point_proj(cols_to_use = ['Name', 'playerid', 'IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HD'],
      points=[7.4, 2.0, -2.6, -3.0, -3.0, -12.3, 5.0, 4.0],
      depth='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/DepthChartsPitchers.csv',
      steamer='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/SteamerPitchers.csv',
      tb='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/TBPitchers.csv',
      zips='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ZipsPitchers.csv',
      atc='https://raw.githubusercontent.com/mrkaye97/Ottoneu/master/data/ATCPitchers.csv',
      out='pitchers.csv')

join_pos()

get_rep_lvl()


