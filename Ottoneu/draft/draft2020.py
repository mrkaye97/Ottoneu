import pandas as pd
import os

ROOT_DIR = '/users/matt/Google Drive/Ottoneu'


def point_proj(cols_to_use, points, depth, steamer, out):
    depth = pd.read_csv(os.path.join(ROOT_DIR, 'data', depth), dtype={'playerid': 'str'})
    steamer = pd.read_csv(os.path.join(ROOT_DIR, 'data', steamer), dtype={'playerid': 'str'})

    df = (pd
          .concat([depth, steamer], axis=0, sort=False)
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
     .to_csv(os.path.join(ROOT_DIR, 'draft', out))
     )


point_proj(cols_to_use = ['Name', 'playerid', 'AB', 'H', '2B', '3B', 'HR', 'BB', 'HBP', 'SB', 'CS'],
      points = [-1.0, 5.6, 8.5, 11.3, 15, 3.0, 3.0, 1.9, -2.8],
      depth='dc.csv',
      steamer='steamer.csv',
      out='hitters.csv')
point_proj(cols_to_use = ['Name', 'playerid', 'IP', 'SO', 'H', 'BB', 'HBP', 'HR', 'SV', 'HD'],
      points=[7.4, 2.0, -2.6, -3.0, -3.0, -14.9, 5.0, 4.0],
      depth='p_dc.csv',
      steamer='p_steamer.csv',
      out='pitchers.csv')


