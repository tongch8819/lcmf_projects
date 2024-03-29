#coding=utf8

from sqlalchemy import MetaData, Table, select, func, literal_column
# import string
# from datetime import datetime, timedelta
import pandas as pd
# import os
# import sys
import logging
from . import database
from ipdb import set_trace

from dateutil.parser import parse

logger = logging.getLogger(__name__)

def load(gid, included_highlow_id=False):
    db = database.connection('asset')
    metadata = MetaData(bind=db)
    t1 = Table('mz_highlow_pos', metadata, autoload=True)

    columns = [
        t1.c.mz_date,
        t1.c.mz_asset_id,
        t1.c.mz_ratio,
    ]
    index_col = ['mz_date', 'mz_asset_id']

    if included_highlow_id:
        columns.insert(0, t1.c.mz_highlow_id)
        index_col.insert(0, 'mz_highlow_id')

    s = select(columns)

    if gid is not None:
        s = s.where(t1.c.mz_highlow_id == gid)
    else:
        return None
    # if xtypes is not None:
    #     s = s.where(t1.c.mz_type.in_(xtypes))

    df = pd.read_sql(s, db, index_col=index_col, parse_dates=['mz_date'])

    df = df.unstack().fillna(0.0)
    df.columns = df.columns.droplevel(0)
    df = df.rename(lambda x: x.decode() if isinstance(x, bytes) else x, axis = 'columns')

    return df

def save(gid, df):
    fmt_columns = ['mz_ratio']
    fmt_precision = 4
    if not df.empty:
        df = database.number_format(df, fmt_columns, fmt_precision)
    #
    # 保存择时结果到数据库
    #
    db = database.connection('asset')
    t2 = Table('mz_highlow_pos', MetaData(bind=db), autoload=True)
    columns = [literal_column(c) for c in (df.index.names + list(df.columns))]
    s = select(columns, (t2.c.mz_highlow_id == gid))
    df_old = pd.read_sql(s, db, index_col=['mz_highlow_id', 'mz_date', 'mz_asset_id'], parse_dates=['mz_date'])
    df_old = df_old.rename(index = lambda x: x.decode() if isinstance(x, bytes) else x)
    if not df_old.empty:
        df_old = database.number_format(df_old, fmt_columns, fmt_precision)

    # 更新数据库
    # print df_new.head()
    # print df_old.head()
    database.batch(db, t2, df, df_old, timestamp=True)

